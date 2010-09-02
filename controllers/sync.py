# -*- coding: utf-8 -*-

""" Synchronisation - Controllers

    @author: Amer Tahir

"""

module = "admin" # sync?
module_name = T("Synchronization")

# Options Menu (available in all Functions' Views)
response.menu_options = admin_menu_options

# -----------------------------------------------------------------------------
# S3 framework functions
#
def index():

    """ Module's Home Page """

    return dict(module_name=module_name)

# -----------------------------------------------------------------------------
@auth.requires_login()
def now():

    """ Manual synchronization """

    import simplejson as json

    # Settings
    settings = db().select(db.sync_setting.uuid,
                           db.sync_setting.proxy,
                           limitby=(0, 1)).first()
    if not settings:
        session.error = T("Synchronization not configured")
        return dict(module_name=module_name,
                    sync_status="Configuration Error - no settings found.",
                    sync_start=False,
                    sync_state=None)

    # Last state (=first record in sync_now)
    state = db().select(db.sync_now.ALL, limitby=(0, 1)).first()

    action = request.get_vars.get("sync", None)

    if action == "start":

        if session.s3.sync_msg is None:
            session.s3.sync_msg = []

        #tablesnames = s3_sync_primary_resources()

        if not state: # =no prior sync to be resumed.

            # Get all scheduled jobs
            table_job = db.sync_schedule
            jobs = db((table_job.period == "m") &
                      (table_job.enabled == True)).select(table_job.ALL)
            if not jobs:
                final_status = "There are no scheduled jobs. Please schedule a sync operation (set to run manually).<br /><br /><a href=\"" + URL(r=request, c="sync", f="schedule") + "\">Click here</a> to go to Sync Schedules page.<br /><br />\n"
            else:
                # Load first resource list
                job = jobs.first()
                try:
                    job_cmd = json.loads(job.job_command)
                except:
                    res_list = ""
                else:
                    res_list = ",".join(map(str, job_cmd.get("resources", [])))

            job_list = ",".join(map(str, [j.id for j in jobs]))

            # begin new sync now session
            sync_now_id = db.sync_now.insert(sync_jobs = job_list,
                                             started_on = request.utcnow,
                                             job_resources_done = "",
                                             job_resources_pending = res_list,
                                             job_sync_errors = "")

            state = db(db.sync_now.id == sync_now_id).select(db.sync_now.ALL, limitby=(0, 1)).first()

            #session.s3.sync_msg.append()

        else:

            # Now already started
            sync_now_id = state.id
            session.s3.sync_msg.append("Sync resumed (originally started on %s)" % state.started_on.strftime("%x %H:%M:%S"))

        # unlock session - what for?
        #session._unlock(response)
        # become super-user - what for?
        session.s3.roles.append(1)

        # get job from queue
        sync_jobs_list = state.sync_jobs.split(", ")
        if "" in sync_jobs_list:
            sync_jobs_list.remove("")
        sync_job = db(db.sync_schedule.id == int(sync_jobs_list[0])).select(db.sync_schedule.ALL, limitby=(0, 1)).first()
        job_cmd = None
        if sync_job:
            job_cmd = json.loads(sync_job.job_command)
        sync_job_partner = job_cmd["partner_uuid"]
        peer = db(db.sync_partner.uuid == sync_job_partner).select(limitby=(0, 1)).first()

        # Whether a push was successful
        push_success = False

        if sync_job and peer:

            #final_status += "<br />Syncing with: " + \
                            #peer.name + ", " + \
                            #peer.instance_url + \
                            #" (" + peer.instance_type + "):<br />\n\n"

            peer_sync_success = True
            last_sync_on = sync_job.last_run
            complete_sync = False
            sync_mode = 1
            if "complete" in job_cmd and str(job_cmd["complete"]) == "True":
                complete_sync = True
            if "mode" in job_cmd:
                sync_mode = int(job_cmd["mode"])

            # Get policy and set resolver (defaults to peer policy)
            job_policy = job_cmd.get("policy", peer.policy)
            if job_policy:
                try:
                    policy = int(job_policy)
                except ValueError:
                    policy = None
            s3xrc.sync_resolve = lambda vector, peer=peer, policy=policy: \
                                        sync_res(vector, peer, policy)

            sync_resources = []
            sync_errors = ""

            # Find resources to sync
            tn = state.job_resources_pending.split(",")
            tablenames = [n.strip().lower() for n in tn]

            if sync_job.job_type == 1:

                # Synchronize Eden<->Eden
                result = s3_sync_eden_eden(peer, sync_mode, tablenames,
                                        settings=settings,
                                        last_sync=last_sync_on,
                                        complete_sync=complete_sync)

            else:

                # Synchronize Eden<->Other
                result = s3_sync_eden_other(peer, sync_mode, tablenames,
                                            settings=settings)

            # update sync now state
            if state.job_resources_done:
                state.job_resources_done += ","
            state.job_resources_done += ",".join(map(str, sync_resources))

            job_res_pending = state.job_resources_pending.split(",")
            if "" in job_res_pending:
                job_res_pending.remove("")

            if sync_job.job_type == 1:
                for tablename in tablenames:
                    job_res_pending.remove(tablename)

            state.job_resources_pending = ",".join(map(str, job_res_pending))
            state.job_sync_errors += sync_errors
            vals = {"job_resources_done": state.job_resources_done,
                    "job_resources_pending": state.job_resources_pending,
                    "job_sync_errors": state.job_sync_errors}
            db(db.sync_now.id == sync_now_id).update(**vals)
            state = db(db.sync_now.id == sync_now_id).select(db.sync_now.ALL, limitby=(0, 1)).first()

            # check if all resources are synced for the current job, i.e. is it done?
            if (not state.job_resources_pending) or sync_job.job_type == 2:
                # job completed, check if there are any more jobs, if not, then sync now completed

                # log sync job
                if sync_mode == 1:
                    sync_method = "Pull"
                elif sync_mode == 2:
                    sync_method = "Push"
                elif sync_mode == 3:
                    sync_method = "Pull-Push"
                log_table_id = db[log_table].insert(
                    partner_uuid = sync_job_partner,
                    timestmp = datetime.datetime.utcnow(),
                    sync_resources = state.job_resources_done,
                    sync_errors = state.job_sync_errors,
                    sync_mode = "online",
                    sync_method = sync_method,
                    complete_sync = complete_sync
                )

                # remove this job from queue and process next
                sync_jobs_list = state.sync_jobs.split(", ")
                if "" in sync_jobs_list:
                    sync_jobs_list.remove("")

                if len(sync_jobs_list) > 0:
                    sync_jobs_list.remove(sync_jobs_list[0])
                    state.sync_jobs = ", ".join(map(str, sync_jobs_list))
                    state.job_resources_done = ""
                    state.job_resources_pending = ""
                    if len(sync_jobs_list) > 0:
                        next_job_sel = db(db.sync_schedule.id == int(state.sync_jobs[0])).select(db.sync_schedule.ALL)
                        if next_job_sel:
                            next_job = next_job_sel[0]
                            if next_job.job_type == 1:
                                next_job_cmd = json.loads(next_job.job_command)
                                state.job_resources_pending = ", ".join(map(str, next_job_cmd["resources"]))
                    state.job_sync_errors = ""
                    vals = {"sync_jobs": state.sync_jobs,
                            "job_resources_done": state.job_resources_done,
                            "job_resources_pending": state.job_resources_pending}

                    db(db.sync_now.id == sync_now_id).update(**vals)
                    state = db(db.sync_now.id == sync_now_id).select(db.sync_now.ALL, limitby=(0, 1)).first()

                # update last_sync_on
                vals = {"last_sync_on": datetime.datetime.utcnow()}
                db(db.sync_partner.id == peer.id).update(**vals)
                vals = {"last_run": datetime.datetime.utcnow()}
                db(db.sync_schedule.id == sync_job.id).update(**vals)

            if not state.sync_jobs:
                # remove sync now session state
                db(db.sync_now.id == sync_now_id).delete()
                # we're done
                final_status += "Sync completed successfully. Logs generated: " + str(A(T("Click here to open log"),_href=URL(r=request, c="sync", f="history"))) + "<br /><br />\n"

    elif action == "stop":
        # Stop the running sync process (remove all pending jobs)
        pass

    elif action == "status":
        response.view = "xml.html"
        if session.s3.sync_msg is None:
            item = DIV(DIV("No synchronization process currently running.", _class="failure"))
            session.s3.sync_msg = "DONE"
        elif isinstance(session.s3.sync_msg, list):
            if session.s3.sync_msg:
                msg_list = []
                for i in xrange(len(session.s3.sync_msg)):
                    msg = str(session.s3.sync_msg.pop(0))
                    if msg.find("FAIL"):
                        msg_list.append(DIV(msg, _class="failure"))
                    else:
                        msg_list.append(DIV(msg, _class="success"))
                if msg_list:
                    item = DIV(msg_list).xml()
            else:
                item = DIV(DIV("Synchronization complete.", _class="success"))
                session.s3.sync_msg = "DONE"
        else:
            item = "DONE"
            session.s3.sync_msg = None

        return dict(item=item)
    else:
        pass

    return dict(module_name=module_name,
                action=action,
                sync_status=None,
                sync_start=None,
                sync_state=state)


# -----------------------------------------------------------------------------
def sync():

    """ Sync interface

        allows PUT/GET of any resource (universal RESTful controller)

    """

    import gluon.contrib.simplejson as json

    if len(request.args) < 2:
        # No resource specified
        raise HTTP(501, body=s3xrc.ERROR.BAD_RESOURCE)
    else:
        prefix = request.args.pop(0)
        name = request.args.pop(0)

        if name.find(".") != -1:
            name, extension = name.rsplit(".", 1)
            request.extension = extension

    # Get the sync partner
    peer_uuid = request.vars.get("sync_partner_uuid", None)
    if peer_uuid:
        peers = db.sync_partner
        peer = db(peers.uuid == peer_uuid).select(limitby=(0,1)).first()

    # remote push?
    method = request.env.request_method
    if method in ("PUT", "POST"):
        remote_push = True
        # Must be registered partner for push:
        if not sync_peer:
            raise HTTP(501, body=s3xrc.ERROR.NOT_PERMITTED)
    elif method == "GET":
        remote_push = False
    else:
        raise HTTP(501, body=s3xrc.ERROR.BAD_METHOD)

    # Set the sync resolver with no policy (defaults to peer policy)
    s3xrc.sync_resolve = lambda vector, peer=peer: sync_res(vector, peer, None)

    def prep(r):
        # Do not allow interactive formats
        if r.representation in ("html", "popup", "aadata"):
            return False
        # Do not allow URL methods
        if r.method:
            return False
        # Neutralize push limit of the resource
        r.resource.push_limit = None
        return True
    response.s3.prep = prep

    def postp(r, output, sync_peer=sync_peer):

        try:
            output_json = Storage(json.loads(output))
        except:
            # No JSON response?
            pass
        else:
            if r.http in ("PUT", "POST"):

                resource = r.resource
                sr = [c.component.tablename for c in resource.components.values()]
                sr.insert(0, resource.tablename)
                sync_resources = ",".join(sr)

                if str(output_json["statuscode"]) != "200":
                    sync_resources += " (error)"
                    sync_errors = str(output)
                else:
                    sync_errors = ""

                db[log_table].insert(
                    partner_uuid = sync_peer.uuid,
                    timestmp = datetime.datetime.utcnow(),
                    sync_resources = sync_resources,
                    sync_errors = sync_errors,
                    sync_mode = "online",
                    sync_method = "Remote Push",
                    complete_sync = False)

        return output
    response.s3.postp = postp

    # Execute the request
    output = shn_rest_controller(prefix, name)

    #return ret_data
    return output


# -----------------------------------------------------------------------------
def sync_res(vector, peer, policy):

    """ Sync resolver

        designed as callback for s3xrc.sync_resolve

    """

    import cPickle

    if policy is None:
        policy = peer.policy

    newer = True # assume that the peer record is newer

    if vector.method == vector.METHOD_UPDATE:
        table = vector.table
        if "modified_on" in table.fields and vector.mtime is not None:
            row = vector.db(table.id==vector.id).select(table.modified_on,
                                                        limitby=(0,1)).first()
            if row:
                local_mtime = row.modified_on
            if local_mtime > vector.mtime:
                newer = False

    # Sync policies:
    #
    #  Option    local records                 peer records     Title
    #
    #  0         do nothing                    do nothing       No Sync
    #  1         --                            --               Manual
    #  2         do nothing                    import           Import
    #  3         update to peer version        import           Replace
    #  4         update to peer version        do nothing       Update
    #  5         update to/keep newer version  import           Replace Newer
    #  6         update to/keep newer version  do nothing       Update Newer
    #  7         do nothing                    import master    Import Master
    #  8         update to master              import master    Replace Master
    #  9         update to master              do nothing       Update Master
    # 10         --                            --               Role-Based (not implemented)

    conflict = False

    # @todo: conflict detection

    if sync_policy == 0: # No Sync
        vector.resolution = vector.RESOLUTION.THIS
        vector.strategy = []
    elif sync_policy == 1: # Manual
        vector.resolution = vector.RESOLUTION.THIS
        vector.strategy = []
    elif sync_policy == 2: # Import
        vector.resolution = vector.RESOLUTION.OTHER
        vector.strategy = [vector.METHOD.CREATE]
    elif sync_policy == 3: # Replace
        vector.resolution = vector.RESOLUTION.OTHER
        vector.strategy = [vector.METHOD.CREATE, vector.METHOD.UPDATE]
    elif sync_policy == 4: # Update
        vector.resolution = vector.RESOLUTION.OTHER
        vector.strategy = [vector.METHOD.UPDATE]
    elif sync_policy == 5: # Replace Newer
        vector.resolution = vector.RESOLUTION.NEWER
        vector.strategy = [vector.METHOD.CREATE, vector.METHOD.UPDATE]
    elif sync_policy == 6: # Update Newer
        vector.resolution = vector.RESOLUTION.NEWER
        vector.strategy = [vector.METHOD.UPDATE]
    elif sync_policy == 7: # Import Master
        vector.resolution = vector.RESOLUTION.MASTER
        vector.strategy = [vector.METHOD.CREATE]
    elif sync_policy == 8: # Replace Master
        vector.resolution = vector.RESOLUTION.MASTER
        vector.strategy = [vector.METHOD.CREATE, vector.METHOD.UPDATE]
    elif sync_policy == 9: # Update Master
        vector.resolution = vector.RESOLUTION.THIS
        vector.strategy = [vector.METHOD.UPDATE]
    elif sync_policy == 10: # Role Based (not implemented)
        vector.resolution = vector.RESOLUTION.THIS
        vector.strategy = []
    else:
        pass # use defaults

    #elif sync_policy == 1:  # Keep Local
        #vector.resolution = vector.RESOLUTION.THIS

    #elif sync_policy == 2:  # Replace with Remote
        #vector.resolution = vector.RESOLUTION.OTHER
        #if (db_record_mtime and vector.mtime < db_record_mtime) or \
           #(db_record_mtime and sync_peer.last_sync_on and db_record_mtime > sync_peer.last_sync_on):
           ## log this as a conflict, remote record is older
            ## log this as a conflict, local record was modified too, but overwritten

    #elif sync_policy == 3:  # Keep with Newer Timestamp
        #vector.resolution = vector.RESOLUTION.NEWER
        #if db_record_mtime and vector.mtime < db_record_mtime:
            ## log this as a conflict, remote record is older

    #elif sync_policy == 4:  # Role-based
        ## not implemented, defaulting to "Newer Timestamp"
        #vector.resolution = vector.RESOLUTION.NEWER

    #elif sync_policy == 5:  # Choose Manually
        #if db_record_mtime and vector.mtime != db_record_mtime:
            ## just log and skip
            #vector.strategy = []

    if conflict: # log conflict

        record_dump = cPickle.dumps(dict(vector.record), 0)

        db[conflict_table].insert(
            uuid = vector.uuid,
            resource_table = vector.tablename,
            remote_record = record_dump,
            remote_modified_by = vector.element.get("modified_by", None),
            remote_modified_on = vector.mtime,
            logged_on = datetime.datetime.utcnow(),
            resolved = False)

    return


# -----------------------------------------------------------------------------
@auth.shn_requires_membership(1)
def partner():

    """ Synchronisation Partners """

    import gluon.contrib.simplejson as json

    table = db.sync_partner

    table.uuid.label = "UUID"
    table.uuid.comment = DIV(SPAN("*", _class="req"), DIV(_class="tooltip",
        _title="UUID|" + Tstr("The unique identifier of the sync partner. Leave blank if the instance type is not Sahana Eden, it will be auto-assigned in that case.")))
    table.name.label = T("Name")
    table.name.comment = DIV(_class="tooltip",
        _title=Tstr("Name") + "|" + Tstr("The descriptive name of the sync partner."))
    table.instance_url.label = T("Instance URL")
    table.instance_url.comment = DIV(SPAN("*", _class="req"), DIV(_class="tooltip",
        _title=Tstr("Instance URL") + "|" + Tstr("For Eden instances - this is the application URL, e.g. http://sync.sahanfoundation.org/eden. For non-Eden instances, this is the Full ")))
    table.instance_type.label = T("Instance Type")
    table.instance_type.comment = DIV(SPAN("*", _class="req"), DIV(_class="tooltip",
        _title=Tstr("Instance Type") + "|" + Tstr("Whether this is a Sahana Eden, Sahana Agasti, Ushahidi or Other instance.")))
    table.username.label = T("Sync Username")
    table.username.comment = DIV(_class="tooltip",
        _title=Tstr("Sync Username") + "|" + Tstr("Username used to login when synchronising with this partner. Note that only HTTP Basic authentication is supported."))
    table.password.label = T("Sync Password")
    table.password.comment = DIV(_class="tooltip",
        _title=Tstr("Sync Password") + "|" + Tstr("Password used to login when synchronising with this partner. Note that only HTTP Basic authentication is supported."))
    table.comments.label = T("Comments")
    table.comments.comment = DIV(_class="tooltip",
        _title=Tstr("Comments") + "|" + Tstr("Any comments about this sync partner."))
    table.policy.label = T("Sync Policy")
    table.policy.comment = DIV(SPAN("*", _class="req"), DIV(_class="tooltip",
        _title=Tstr("Sync Policy") + "|" + Tstr("The policy to use while synchronising with this partner. All policies other than 'No Sync' come into effect when conflicts arise.")))
    table.sync_pools.readable = False
    table.sync_pools.writable = False
    table.password.readable = False
    table.last_sync_on.writable = False

    # CRUD Strings - @todo: make new style
    title_create = T("Add Partner")
    title_display = T("Partner Details")
    title_list = T("List Partners")
    title_update = T("Edit Partner")
    title_search = T("Search Partners")
    subtitle_create = T("Add New Partner")
    subtitle_list = T("Partners")
    label_list_button = T("List Partners")
    label_create_button = T("Add Partner")
    label_search_button = T("Search Partners")
    msg_record_created = T("Partner added")
    msg_record_modified = T("Partner updated")
    msg_record_deleted = T("Partner deleted")
    msg_list_empty = T("No Partners currently registered")
    s3.crud_strings.sync_partner = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)

    if "delete" in request.args:
        peer_sel = db(db.sync_partner.id==int(request.args[0])).select(db.sync_partner.ALL)
        peer_uuid = None
        if peer_sel:
            peer_uuid = peer_sel[0].uuid
        if peer_uuid:
            sch_jobs_del = []
            sch_jobs = db().select(db.sync_schedule.ALL)
            for sch_job in sch_jobs:
                sch_job_cmd = json.loads(sch_job.job_command)
                if sch_job_cmd["partner_uuid"] == peer_uuid:
                    sch_jobs_del.append(sch_job.id)
            if sch_jobs_del:
                db(db.sync_schedule.id.belongs(sch_jobs_del)).delete()

    elif (not "update" in request.args) and len(request.vars) > 0:
        # add new partner
        random_uuid = str(uuid.uuid4())
        new_instance_type = ""
        if "instance_type" in request.vars:
            new_instance_type = request.vars["instance_type"]
        if new_instance_type != "Sahana Eden":
            if "uuid" in request.vars:
                request.vars["uuid"] = random_uuid
            if "uuid" in request.get_vars:
                request.get_vars["uuid"] = random_uuid
            if "uuid" in request.post_vars:
                request.post_vars["uuid"] = random_uuid
        elif "uuid" in request.vars and request.vars["uuid"] and "instance_url" in request.vars and request.vars["instance_url"]:
            # create new default scheduled job for this partner, it's a Sahana Eden instance
            modules = deployment_settings.modules
            _db_tables = db.tables
            db_tables = []
            for __table in _db_tables:
                if "modified_on" in db[__table].fields and "uuid" in db[__table].fields:
                    db_tables.append(__table)
            sch_resources = []
            for _module in modules:
                for _table in db_tables:
                    if _table.startswith(_module + "_"):
                        sch_resources.append(_module + "||" + _table[len(_module)+1:])

            # add job to db
            new_partner_uuid = request.vars["uuid"]
            new_partner_instance_type = request.vars["instance_type"]
            new_partner_policy = int(request.vars["policy"])
            new_partner_name = None
            if "name" in request.vars and request.vars["name"]:
                new_partner_name = request.vars["name"]
            sch_comments = "Default manually triggered schedule job for sync partner '"
            if new_partner_name:
                sch_comments += new_partner_name
            else:
                sch_comments += new_partner_uuid
            sch_comments += "'"
            sch_cmd = dict()
            sch_cmd["partner_uuid"] = new_partner_uuid
            sch_cmd["policy"] = new_partner_policy
            sch_cmd["resources"] = sch_resources
            sch_cmd["complete"] = False
            sch_cmd["mode"] = 3
            db["sync_schedule"].insert(
                comments = sch_comments,
                period = "m",
                hours = None,
                days_of_week = None,
                time_of_day = None,
                runonce_datetime = None,
                job_type = 1,
                job_command = json.dumps(sch_cmd),
                last_run = None,
                enabled = True,
                created_on = datetime.datetime.now(),
                modified_on = datetime.datetime.now()
            )

    return shn_rest_controller("sync", "partner")


# -----------------------------------------------------------------------------
@auth.shn_requires_membership(1)
def setting(): # OK

    """ Synchronisation Settings """

    if not "update" in request.args:
        redirect(URL(r=request, args=["update", 1]))

    # Table settings
    table = db.sync_setting

    table.uuid.writable = False
    table.uuid.label = "UUID"
    table.uuid.comment = DIV(_class="tooltip",
        _title="UUID|" + Tstr("The unique identifier which identifies this instance to other instances."))

    table.comments.label = T("Comments")
    table.comments.comment = DIV(_class="tooltip",
        _title=Tstr("Comments") + "|" + Tstr("Any comments for this instance."))

    table.beacon_service_url.readable = False
    table.beacon_service_url.writable = False
#    table.beacon_service_url.label = T("Beacon Service URL")
#    table.beacon_service_url.comment = DIV(_class="tooltip",
#        _title=Tstr("Beacon Service URL") + "|" + Tstr("Beacon service allows searching for other instances that wish to synchronise. This is the URL of the beacon service this instance will use."))

    table.sync_pools.readable = False
    table.sync_pools.writable = False

    # CRUD strings
    s3.crud_strings.sync_setting = Storage(
        title_update = T("Edit Sync Settings"),
        label_list_button = T("Sync Settings"),
        msg_record_modified = T("Sync Settings updated"))

    # Return to this
    crud.settings.update_next = URL(r=request, args=["update", 1])

    return shn_rest_controller("sync", "setting", deletable=False, listadd=False)


# -----------------------------------------------------------------------------
@auth.shn_requires_membership(1)
def schedule():

    """ Synchronisation Schedules """

    import gluon.contrib.simplejson as json
    title = T("Syncronisation Schedules")

    jobs = None
    confirmation_msg = None

    if "create" in request.args:

        response.view = "sync/schedule_create.html"

        if "form_action" in request.vars and request.vars["form_action"] == "submit":
            # create new job - add it to database
            sch_enabled = True
            if "job_enabled" in request.vars and request.vars["job_enabled"] == "0":
                sch_enabled = False
            sch_comments = None
            if "comments" in request.vars:
                sch_comments = request.vars["comments"]
            sch_source_type = "eden"
            if "sync_data_source_type" in request.vars:
                sch_source_type = request.vars["sync_data_source_type"]
            sch_period = "h"
            if "sync_schedule_period" in request.vars:
                sch_period = request.vars["sync_schedule_period"]
            sch_period_hours = 5
            if "sync_schedule_period_hours" in request.vars:
                sch_period_hours = request.vars["sync_schedule_period_hours"]
            sch_days_of_week = []
            if "sync_schedule_weekly_days" in request.vars and request.vars["sync_schedule_weekly_days"]:
                sch_days_of_week = request.vars["sync_schedule_weekly_days"]
            sch_time_of_day = None
            if sch_period == "d":
                sch_time_of_day = datetime.datetime.strptime(str(request.vars["sync_schedule_daily_time"]), "%H:%M").time()
            elif sch_period == "w":
                sch_time_of_day = datetime.datetime.strptime(str(request.vars["sync_schedule_weekly_time"]), "%H:%M").time()
            sch_runonce_datetime = None
            if "sync_schedule_once_datetime" in request.vars and request.vars["sync_schedule_once_datetime"]:
                sch_runonce_datetime = datetime.datetime.strptime(str(request.vars["sync_schedule_once_datetime"]), "%Y-%m-%d %H:%M:%S")

            sch_job_type = 1
            sch_cmd = dict()
            sch_cmd["partner_uuid"] = request.vars["sync_partner_uuid"]
            sch_cmd["policy"] = int(request.vars["sync_policy"])
            if sch_source_type == "eden":
                # eden data source
                if "sync_resources" in request.vars and request.vars["sync_resources"]:
                    sch_cmd["resources"] = request.vars["sync_resources"]
                    if type(sch_cmd["resources"]) == str:
                        sch_cmd["resources"] = [sch_cmd["resources"]]
                else:
                    sch_cmd["resources"] = None
                sch_cmd["complete"] = False
                if "sync_complete" in request.vars and request.vars["sync_complete"] == "1":
                    sch_cmd["complete"] = True
                sch_cmd["mode"] = 3
                if "sync_mode" in request.vars and request.vars["sync_mode"]:
                    sch_cmd["mode"] = int(request.vars["sync_mode"])
            else:
                # custom data source
                sch_job_type = 2
                sch_cmd["custom_command"] = request.vars["sync_custom"]

            # add job to db
            db["sync_schedule"].insert(
                comments = sch_comments,
                period = sch_period,
                hours = sch_period_hours,
                days_of_week = ",".join(map(str, sch_days_of_week)),
                time_of_day = sch_time_of_day,
                runonce_datetime = sch_runonce_datetime,
                job_type = sch_job_type,
                job_command = json.dumps(sch_cmd),
                last_run = None,
                enabled = sch_enabled,
                created_on = datetime.datetime.now(),
                modified_on = datetime.datetime.now()
            )

            confirmation_msg = "New Scheduled job created"
            response.view = "sync/schedule.html"
    else:
        if "form_action" in request.vars and "selected_jobs" in request.vars:
            sel_jobs = request.vars["selected_jobs"]
            if request.vars["form_action"] == "enable":
                for s_job_id in sel_jobs:
                    vals = {"enabled": True}
                    db(db.sync_schedule.id==int(s_job_id)).update(**vals)
            elif request.vars["form_action"] == "disable":
                for s_job_id in sel_jobs:
                    vals = {"enabled": False}
                    db(db.sync_schedule.id==int(s_job_id)).update(**vals)
            elif request.vars["form_action"] == "delete":
                for s_job_id in sel_jobs:
                    db(db.sync_schedule.id==int(s_job_id)).delete()

    jobs = db().select(db.sync_schedule.ALL)

    return dict(title=title, jobs=jobs, confirmation_msg=confirmation_msg)


# -----------------------------------------------------------------------------
def schedule_cron():
    # only accept requests from local machine
    if not request.env.remote_addr == "127.0.0.1":
        return

    while True:
        try:
            # look at each job and run if it it's scheduled time
            jobs = db(db.sync_schedule.enabled==True).select(db.sync_schedule.ALL)
            for job in jobs:
                last_run = job.last_run
                if not last_run:
                    last_run = job.created_on - datetime.timedelta(days=2)
                try:
                    if job.period == "h":
                        if datetime.datetime.now() >= (last_run + datetime.timedelta(hours=job.hours)):
                            schedule_process_job(job.id)
                            db.commit()
                    elif job.period == "d":
                        if job.time_of_day and last_run.date() != datetime.datetime.now().date() and datetime.datetime.now().hour >= job.time_of_day.hour and datetime.datetime.now().minute >= job.time_of_day.minute:
                            schedule_process_job(job.id)
                            db.commit()
                    elif job.period == "w":
                        days_of_week = None
                        last_run_weekday = last_run.weekday() + 1
                        if last_run_weekday == 8:
                            last_run_weekday = 1
                        now_weekday = datetime.datetime.now().weekday() + 1
                        if now_weekday == 8:
                            now_weekday = 1
                        if job.days_of_week:
                            days_of_week = map(int, job.days_of_week.split(","))
                        if job.time_of_day and now_weekday in days_of_week and last_run_weekday < now_weekday and datetime.datetime.now().hour >= job.time_of_day.hour and datetime.datetime.now().minute >= job.time_of_day.minute:
                            schedule_process_job(job.id)
                            db.commit()
                    elif job.period == "o":
                        if job.runonce_datetime and last_run < job.runonce_datetime and datetime.datetime.now() >= job.runonce_datetime:
                            schedule_process_job(job.id)
                            db.commit()
                except Error, e:
                    # log scheduler error
                    try:
                        log_file = open("applications/" + request.application + "/cron/scheduler_errors.txt", "a")
                        log_file.write(str(datetime.datetime.now()) + " - error while running job " + str(job.id) + ":\n" + str(e) + "\n\n")
                        log_file.close()
                    except:
                        pass
                        #print "error while appending scheduler error log file!"
            db.commit()
        except Error, e:
            # log scheduler error
            try:
                log_file = open("applications/" + request.application + "/cron/scheduler_errors.txt", "a")
                log_file.write(str(datetime.datetime.now()) + " - error while running job " + str(job.id) + ":\n" + str(e) + "\n\n")
                log_file.close()
            except:
                pass
                #print "error while appending scheduler error log file!"

        # pause for 15 seconds
        time.sleep(15)

    return


# -----------------------------------------------------------------------------
def schedule_process_job(job_id):

    """ docstring??? """

    import gluon.contrib.simplejson as json
    import urllib, urlparse

    #global sync_policy # @todo: do not use global vars

    job_sel = db(db.sync_schedule.id==job_id).select(db.sync_schedule.ALL)
    if not job_sel:
        return
    job = job_sel[0]
    if not job:
        return
    if not job.enabled:
        return

    job_cmd = json.loads(job.job_command)

    # url fetcher
    #fetcher = FetchURL()
    # retrieve settings
    settings = db().select(db.sync_setting.ALL)[0]
    peer_sel = db(db.sync_partner.uuid==str(job_cmd["partner_uuid"])).select(db.sync_partner.ALL)
    if not peer_sel:
        return
    peer = peer_sel[0]

    peer_sync_success = True
    last_sync_on = job.last_run
    complete_sync = False
    sync_mode = 1
    if "complete" in job_cmd and str(job_cmd["complete"]) == "True":
        complete_sync = True
    if "policy" in job_cmd:
        sync_policy = int(job_cmd["policy"])
    if "mode" in job_cmd:
        sync_mode = int(job_cmd["mode"])
    sync_resources = []
    sync_errors = ""

    # Keep Session for local URLs
    cookie = str(response.session_id_name) + "=" + str(response.session_id)

    if job.job_type == 1:
        # Sync Eden sync
        if (not last_sync_on is None) and complete_sync == False:
            last_sync_on_str = "?msince=" + last_sync_on.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            last_sync_on_str = ""

        log_file = open("applications/" + request.application + "/cron/scheduler_log.txt", "a")
        log_file.write(str(datetime.datetime.now()) + " - running job " + str(job.id) + "\n")
        log_file.close()
        for res_item in job_cmd["resources"]:
            _module, _resource = res_item.split("||")
            _resource_name = _module + "_" + _resource
            peer_instance_url = list(urlparse.urlparse(peer.instance_url))
            if peer_instance_url[2].endswith("/")==False:
                peer_instance_url[2] += "/"
            resource_remote_pull_url = peer.instance_url
            if resource_remote_pull_url.endswith("/")==False:
                resource_remote_pull_url += "/"
            resource_remote_pull_url += "sync/sync." + import_export_format + "/" + _module + "/" + _resource + last_sync_on_str
            resource_remote_push_url = peer_instance_url[2] + "sync/sync." + import_export_format + "/push/" + _module + "/" + _resource + "?sync_partner_uuid=" + str(settings.uuid)
            resource_local_pull_url = "/" + request.application + "/sync/sync." + import_export_format + "/" + _module + "/" + _resource + last_sync_on_str
            resource_local_push_url = "/" + request.application + "/sync/sync." + import_export_format + "/create/" + _module + "/" + _resource
            if sync_mode in [1, 3]:
                # Sync -> Pull
                _request_params = urllib.urlencode({"sync_partner_uuid": str(peer.uuid), "fetchurl": resource_remote_pull_url})
                _request_vars_copy = request.vars
                _request_get_vars_copy = request.get_vars
                _request_post_vars_copy = request.post_vars
                _request_args_copy = request.args
                _request_extension_copy = request.extension
                _request_env_request_method_copy = request.env.request_method
                try:
                    #_response = fetcher.fetch("PUT", request.env.http_host, resource_local_push_url, _request_params, cookie)
                    request.vars = Storage()
                    request.vars["sync_partner_uuid"] = str(peer.uuid)
                    request.vars["fetchurl"] = resource_remote_pull_url
                    request.args = ["push", _module, _resource]
                    request.extension = import_export_format
                    request.env.request_method = "PUT"
                    session.auth = Storage()
                    session.auth["user"] = None
                    session.s3.roles.append(1)
                    _response = sync()
                except Error, e:
                    if not _resource_name + " (error)" in sync_resources and not _resource_name in sync_resources:
                        sync_resources.append(_resource_name + " (error)")
                        error_str = str(e)
                        sync_errors +=  "Error while syncing => " + _resource_name + ": \n" + error_str + "\n\n"
                        #print "Error while syncing => " + _resource_name + ": \n" + error_str + "\n\n"
                else:
                    if not _resource_name + " (error)" in sync_resources and not _resource_name in sync_resources:
                        sync_resources.append(_resource_name)
                request.args = _request_args_copy
                request.get_vars = _request_get_vars_copy
                request.post_vars = _request_post_vars_copy
                request.vars = _request_vars_copy
                request.extension = _request_extension_copy
                request.env.request_method = _request_env_request_method_copy
            if sync_mode in [2, 3]:
                # Sync -> Push
                try:
                    _local_data = fetcher.fetch("GET", request.env.http_host, resource_local_pull_url, None, cookie)
                    _response = fetcher.fetch("PUT", peer_instance_url[1], resource_remote_push_url, _local_data, None, peer.username, peer.password)
                except Error, e:
                    if not _resource_name + " (error)" in sync_resources and not _resource_name in sync_resources:
                        sync_resources.append(_resource_name + " (error)")
                    error_str = str(e)
                    sync_errors +=  "Error while syncing => " + _resource_name + ": \n" + error_str + "\n\n"
                else:
                    if not _resource_name + " (error)" in sync_resources and not _resource_name in sync_resources:
                        sync_resources.append(_resource_name)

    else:
        # Custom sync
        sync_mode = 1
        _request_vars_copy = request.vars
        _request_get_vars_copy = request.get_vars
        _request_post_vars_copy = request.post_vars
        _request_args_copy = request.args
        _request_extension_copy = request.extension
        try:
            request.vars = Storage()
            request.vars["sync_partner_uuid"] = str(peer.uuid)
            request.vars["fetchurl"] = job_cmd["custom_command"]
            request.args = ["create", "sync", "log"]
            request.extension = import_export_format
            _response = sync()
        except Error, e:
            error_str = str(e)
            sync_errors =  "Error while syncing job " + str(job.id) + ": \n" + error_str + "\n\n"
            #print sync_errors
        request.args = _request_args_copy
        request.get_vars = _request_get_vars_copy
        request.post_vars = _request_post_vars_copy
        request.vars = _request_vars_copy
        request.extension = _request_extension_copy

    if sync_mode == 1:
        sync_method = "Pull"
    elif sync_mode == 2:
        sync_method = "Push"
    elif sync_mode == 3:
        sync_method = "Pull-Push"

    # log sync job
    log_table_id = db[log_table].insert(
        partner_uuid = peer.uuid,
        timestmp = datetime.datetime.utcnow(),
        sync_resources = ", ".join(map(str, sync_resources)),
        sync_errors = sync_errors,
        sync_mode = "online",
        sync_method = sync_method,
        complete_sync = complete_sync
    )

    # update last_sync_on
    vals = {"last_sync_on": datetime.datetime.utcnow()}
    db(db.sync_partner.id==peer.id).update(**vals)
    vals = {"last_run": datetime.datetime.utcnow()}
    db(db.sync_schedule.id==job_id).update(**vals)

    return


# -----------------------------------------------------------------------------
@auth.requires_login()
def history():

    """ Shows history of database synchronisations

        @todo: argument list processing too vulnerable
    """

    title = T("Synchronisation History")

    table = db[log_table]
    if len(request.args) > 0:
        logs = db(table.id==int(request.args[0])).select(table.ALL, orderby=table.timestmp)
    else:
        logs = db().select(table.ALL, orderby=table.timestmp)

    return dict(title=title, logs=logs)


# -----------------------------------------------------------------------------
@auth.shn_requires_membership(1)
def conflict():

    """ Conflict Resolution UI """

    import cPickle
    title = T("Conflict Resolution")

    def get_modified_by(user_email):
        modified_by = user_email
        user = db(db.auth_user.email == user_email).select().first()
        if user:
            modified_by  = user.first_name
            if user.last_name:
                modified_by += " " + user.last_name
        return modified_by

    skip_fields = ["uuid", "id"]
    field_errors = dict()

    conflicts = db(db[conflict_table].resolved==False).select(db[conflict_table].ALL, orderby=db[conflict_table].logged_on)
    for idx in xrange(0, len(conflicts)):
        if not conflicts[idx].resource_table in db.tables:
            del conflicts[idx]
    record_nbr = 1
    if "record_nbr" in request.vars:
        record_nbr = int(request.vars["record_nbr"])
    total_conflicts = len(conflicts)
    if record_nbr < 1 or record_nbr > total_conflicts:
        record_nbr = 1
    if total_conflicts == 0:
        conflict = None
    else:
        conflict = conflicts[record_nbr - 1]
    remote_record = None
    local_record = None
    local_modified_by = None
    remote_modified_by = None
    if conflict:
        remote_record = cPickle.loads(conflict.remote_record)
        local_record = db(db[conflict.resource_table].uuid==conflict.uuid).select().first()
        if conflict.remote_modified_by:
            remote_modified_by = get_modified_by(conflict.remote_modified_by)
        if "modified_by" in local_record:
            local_modified_by = get_modified_by(local_record.modified_by.email)

    if "form_action" in request.vars:
        if request.vars["form_action"] == "resolve" and conflict:
            if local_record:
                # update local record
                for field in remote_record:
                    if (not field in skip_fields) and (field in db[conflict.resource_table].fields):
                        if "final_"+str(field) in request.vars:
                            vals = {field: request.vars["final_" + str(field)]}
                        else:
                            if db[conflict.resource_table][field].type == "boolean":
                                vals = {field: "False"}
                            else:
                                vals = {field: ""}

                        field_error = db[conflict.resource_table][field].validate(vals[field])[1]
                        if field_error:
                            field_errors[field] = field_error
                        # update only if no errors
                        if len(field_errors) == 0:
                            db(db[conflict.resource_table].uuid==conflict.uuid).update(**vals)
                            # undelete record
                            if "deleted" in db[conflict.resource_table].fields:
                                vals = {"deleted": False}
                                db(db[conflict.resource_table].uuid==conflict.uuid).update(**vals)
            else:
                # insert record
                new_rec = dict()
                for field in remote_record:
                    if field in db[conflict_table].fields:
                        if "final_"+field in request.vars:
                            new_rec[field] = request.vars["final_"+field]
                        else:
                            new_rec[field] = remote_record[field]
                        field_error = db[conflict.resource_table][field].validate(vals[field])[1]
                        if field_error:
                            field_errors[field] = field_error
                # insert only if no errors
                if len(field_errors) == 0:
                    db[conflict.resource_table].insert(**new_rec)

            # set status to resolved if no errors
            if len(field_errors) == 0:
                conflict.update_record(resolved = True)
            # next conflict
            conflicts = db(db[conflict_table].resolved==False).select(db[conflict_table].ALL, orderby=db[conflict_table].logged_on)
            for idx in xrange(0, len(conflicts)):
                if not conflicts[idx].resource_table in db.tables:
                    del conflicts[idx]
            total_conflicts = len(conflicts)
            if record_nbr < 1 or record_nbr > total_conflicts:
                record_nbr = 1
            if total_conflicts == 0:
                conflict = None
            else:
                conflict = conflicts[record_nbr - 1]
            remote_record = None
            local_record = None
            if conflict:
                remote_record = cPickle.loads(conflict.remote_record)
                local_record = db(db[conflict.resource_table].uuid==conflict.uuid).select().first()
                if conflict.remote_modified_by:
                    remote_modified_by = get_modified_by(conflict.remote_modified_by)
                if "modified_by" in local_record:
                    local_modified_by = get_modified_by(local_record.modified_by.email)

    form = None
    if conflict:
        form = SQLFORM.factory(db[conflict.resource_table])

    return dict(title=title,
                skip_fields=skip_fields,
                total_conflicts=total_conflicts,
                conflict=conflict,
                record_nbr=record_nbr,
                local_record=local_record,
                remote_record=remote_record,
                local_modified_by=local_modified_by,
                remote_modified_by=remote_modified_by,
                form=form,
                field_errors=field_errors)

# -----------------------------------------------------------------------------
