# -*- coding: utf-8 -*-

#
# RESTlike CRUD controller
#
# created by Fran Boon, amendments by nursix
#

# *****************************************************************************
# Joint Resource Layer
jrlayer = JRLayer(db)

# *****************************************************************************
# Constants to ensure consistency

# Error messages
UNAUTHORISED = T('Not authorised!')
BADFORMAT = T('Unsupported format!')
BADMETHOD = T('Unsupported method!')
BADRECORD = T('No such record!')
BADFORMAT = T('Bad request format!')
INVALIDREQUEST = T('Invalid request!')

# How many rows to show per page in list outputs
ROWSPERPAGE = 20

# *****************************************************************************
# Data conversion

#
# export_csv ------------------------------------------------------------------
#
def export_csv(resource, query, record=None):
    "Export record(s) as CSV"
    import gluon.contenttype
    response.headers['Content-Type'] = gluon.contenttype.contenttype('.csv')
    if record:
        filename = "%s_%s_%d.csv" % (request.env.server_name, resource, record)
    else:
        # List
        filename = "%s_%s_list.csv" % (request.env.server_name, resource)
    response.headers['Content-disposition'] = "attachment; filename=%s" % filename
    return str(db(query).select())

#
# export_json -----------------------------------------------------------------
#
def export_json(table, query):
    "Export record(s) as JSON"
    response.headers['Content-Type'] = 'text/x-json'
    return db(query).select(table.ALL).json()

#
# export_pdf ------------------------------------------------------------------
#
def export_pdf(table, query):
    "Export record(s) as Adobe PDF"
    try:
        from reportlab.lib.units import cm
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    except ImportError:
        session.error = T('ReportLab module not available within the running Python - this needs installing for PDF output!')
        redirect(URL(r=request))
    try:
        from geraldo import Report, ReportBand, Label, ObjectValue, SystemField, landscape, BAND_WIDTH
        from geraldo.generators import PDFGenerator
    except ImportError:
        session.error = T('Geraldo module not available within the running Python - this needs installing for PDF output!')
        redirect(URL(r=request))

    objects_list = db(query).select(table.ALL)
    if not objects_list:
        session.warning = T('No data in this table - cannot create PDF!')
        redirect(URL(r=request))
    
    import StringIO
    output = StringIO.StringIO()
    
    fields = [table[f] for f in table.fields if table[f].readable]
    _elements = [SystemField(expression='%(report_title)s', top=0.1*cm,
                    left=0, width=BAND_WIDTH, style={'fontName': 'Helvetica-Bold',
                    'fontSize': 14, 'alignment': TA_CENTER})]
    detailElements = []
    COLWIDTH = 2.5
    LEFTMARGIN = 0.2
    for field in fields:
        _elements.append(Label(text=str(field.label)[:16], top=0.8*cm, left=LEFTMARGIN*cm))
        tab, col = str(field).split('.')
        #db[table][col].represent = 'foo'
        detailElements.append(ObjectValue(attribute_name=col, left=LEFTMARGIN*cm, width=COLWIDTH*cm))
        LEFTMARGIN += COLWIDTH
    
    mod, res = str(table).split('_', 1)
    mod_nice = db(db.s3_module.name==mod).select()[0].name_nice
    _title = mod_nice + ': ' + res.capitalize()
        
    class MyReport(Report):
        title = _title
        page_size = landscape(A4)
        class band_page_header(ReportBand):
            height = 1.3*cm
            auto_expand_height = True
            elements = _elements
            borders = {'bottom': True}
        class band_page_footer(ReportBand):
            height = 0.5*cm
            elements = [
                Label(text='%s' % request.utcnow.date(), top=0.1*cm, left=0),
                SystemField(expression='Page # %(page_number)d of %(page_count)d', top=0.1*cm,
                    width=BAND_WIDTH, style={'alignment': TA_RIGHT}),
            ]
            borders = {'top': True}
        class band_detail(ReportBand):
            height = 0.5*cm
            auto_expand_height = True
            elements = tuple(detailElements)
    report = MyReport(queryset=objects_list)
    report.generate_by(PDFGenerator, filename=output)

    output.seek(0)
    import gluon.contenttype
    response.headers['Content-Type'] = gluon.contenttype.contenttype('.pdf')
    filename = "%s_%s.pdf" % (request.env.server_name, str(table))
    response.headers['Content-disposition'] = "attachment; filename=\"%s\"" % filename
    return output.read()

#
# export_rss ------------------------------------------------------------------
#
def export_rss(module, resource, query, main='name', extra='description'):
    """Export record(s) as RSS feed
    main='field': the field used for the title
    extra='field': the field used for the description
    """
    if request.env.remote_addr == '127.0.0.1':
        server = 'http://127.0.0.1:' + request.env.server_port
    else:
        server = 'http://' + request.env.server_name + ':' + request.env.server_port
    link = '/%s/%s/%s' % (request.application, module, resource)
    entries = []
    rows = db(query).select()
    try:
        for row in rows:
            entries.append(dict(title=row[main], link=server + link + '/%d' % row.id, description=row[extra], created_on=row.created_on))
    except:
        for row in rows:
            entries.append(dict(title=row[main], link=server + link + '/%d' % row.id, description='', created_on=row.created_on))
    import gluon.contrib.rss2 as rss2
    items = [ rss2.RSSItem(title = entry['title'], link = entry['link'], description = entry['description'], pubDate = entry['created_on']) for entry in entries]
    rss = rss2.RSS2(title = str(s3.crud_strings.subtitle_list), link = server + link + '/%d' % row.id, description = '', lastBuildDate = request.utcnow, items = items)
    response.headers['Content-Type'] = 'application/rss+xml'
    return rss2.dumps(rss)

#
# export_xls ------------------------------------------------------------------
#
def export_xls(table, query):
    "Export record(s) as XLS"
    try:
        import xlwt
    except ImportError:
        session.error = T('xlwt module not available within the running Python - this needs installing for XLS output!')
        redirect(URL(r=request))

    import StringIO
    output = StringIO.StringIO()

    items = db(query).select(table.ALL)

    book = xlwt.Workbook()
    sheet1 = book.add_sheet(str(table))
    # Header row
    row0 = sheet1.row(0)
    cell = 0
    fields = [table[f] for f in table.fields if table[f].readable]
    for field in fields:
        row0.write(cell, str(field.label), xlwt.easyxf('font: bold True;'))
        cell += 1
    row = 1
    for item in items:
        # Item details
        rowx = sheet1.row(row)
        row += 1
        cell1 = 0
        for field in fields:
            tab, col = str(field).split('.')
            rowx.write(cell1, item[col])
            cell1 += 1
    book.save(output)
    output.seek(0)
    import gluon.contenttype
    response.headers['Content-Type'] = gluon.contenttype.contenttype('.xls')
    filename = "%s_%s.xls" % (request.env.server_name, str(table))
    response.headers['Content-disposition'] = "attachment; filename=\"%s\"" % filename
    return output.read()

#
# export_xml ------------------------------------------------------------------
#
def export_xml(table, query):
    "Export record(s) as XML"
    import gluon.serializers
    items = db(query).select(table.ALL).as_list()
    response.headers['Content-Type'] = 'text/xml'
    return str(gluon.serializers.xml(items))
    
#
# import_csv ------------------------------------------------------------------
#
def import_csv(file, table=None):
    "Import CSV file into Database"
    if table:
        table.import_from_csv_file(file)
    else:
        # This is the preferred method as it updates reference fields
        db.import_from_csv_file(file)

#
# import_json -----------------------------------------------------------------
#
def import_json(method):
    """Import GET vars into Database & respond in JSON
    Supported methods: 'create' & 'update'
    """
    record = Storage()
    uuid = False
    for var in request.vars:
        # Skip the Representation
        if var == 'format':
            pass
        if var == 'uuid' and method == 'update':
            uuid = True
        else:
            record[var] = request.vars[var]
    if not uuid:
        item = '{"Status":"failed","Error":{"StatusCode":400,"Message":"UUID required!"}}'
    else:
        item = ''
        for var in record:
            # Validate request manually
            if table[var].requires(record[var])[1]:
                item += '{"Status":"failed","Error":{"StatusCode":403,"Message":"' + var + ' invalid: ' + table[var].requires(record[var])[1] + '"}}'
        if item:
            # Don't import if validation failed
            pass
        else:
            try:
                if method == 'create':
                    id = table.insert(**dict (record))
                    item = '{"Status":"success","Error":{"StatusCode":201,"Message":"Created as ' + URL(r=request, c=module, f=resource, args=id) + '"}}'
                elif method == 'update':
                    result = db(table.uuid==request.vars.uuid).update(**dict (record))
                    if result:
                        item = '{"Status":"success","Error":{"StatusCode":200,"Message":"Record updated."}}'
                    else:
                        item = '{"Status":"failed","Error":{"StatusCode":404,"Message":"Record ' + request.vars.uuid + ' does not exist."}}'
                else:
                    item = '{"Status":"failed","Error":{"StatusCode":400,"Message":"Unsupported Method!"}}'
            except:
                item = '{"Status":"failed","Error":{"StatusCode":400,"Message":"Invalid request!"}}'
    response.headers['Content-Type'] = 'text/x-json'
    return item

# *****************************************************************************
# Authorisation

#
# shn_has_permission ----------------------------------------------------------
#
def shn_has_permission(name, table_name, record_id = 0):
    """
    S3 framework function to define whether a user can access a record
    Designed to be called from the RESTlike controller
    """
    if session.s3.security_policy == 1:
        # Simple policy
        # Anonymous users can Read.
        if name == 'read':
            authorised = True
        else:
            # Authentication required for Create/Update/Delete.
            authorised = auth.is_logged_in() or auth.basic()
    else:
        # Full policy
        if auth.is_logged_in() or auth.basic():
            # Administrators are always authorised
            if auth.has_membership(1):
                authorised = True
            else:
                # Require records in auth_permission to specify access
                authorised = auth.has_permission(name, table_name, record_id)
        else:
            # No access for anonymous
            authorised = False
    return authorised

#
# shn_accessible_query --------------------------------------------------------
#
def shn_accessible_query(name, table):
    """
    Returns a query with all accessible records for the current logged in user
    This method does not work on GAE because uses JOIN and IN
    """
    # If using the 'simple' security policy then show all records
    if session.s3.security_policy == 1:
        # simple
        return table.id > 0
    # Administrators can see all data
    if auth.has_membership(1):
        return table.id > 0
    # If there is access to the entire table then show all records
    try:
        user_id = auth.user.id
    except:
        user_id = 0
    if auth.has_permission(name, table, 0, user_id):
        return table.id > 0
    # Filter Records to show only those to which the user has access
    session.warning = T("Only showing accessible records!")
    membership = auth.settings.table_membership
    permission = auth.settings.table_permission
    return table.id.belongs(db(membership.user_id == user_id)\
                       (membership.group_id == permission.group_id)\
                       (permission.name == name)\
                       (permission.table_name == table)\
                       ._select(permission.record_id))

# *****************************************************************************
# Audit

#
# shn_audit_read --------------------------------------------------------------
#
def shn_audit_read(operation, resource, record=None, representation=None):
    "Called during Read operations to enable optional Auditing"
    if session.s3.audit_read:
        db.s3_audit.insert(
                person = auth.user.id if session.auth else 0,
                operation = operation,
                module = request.controller,
                resource = resource,
                record = record,
                representation = representation,
            )
    return

#
# shn_audit_create ------------------------------------------------------------
#
def shn_audit_create(form, resource, representation=None):
    """
    Called during Create operations to enable optional Auditing
    Called as an onaccept so that it only takes effect when saved & can read the new values in:
    crud.settings.create_onaccept = lambda form: shn_audit_create(form, resource, representation)
    """
    if session.s3.audit_write:
        record =  form.vars.id
        new_value = []
        for var in form.vars:
            new_value.append(var + ':' + str(form.vars[var]))
        db.s3_audit.insert(
                person = auth.user.id if session.auth else 0,
                operation = 'create',
                module = request.controller,
                resource = resource,
                record = record,
                representation = representation,
                new_value = new_value
            )
    return

#
# shn_audit_update ------------------------------------------------------------
#
def shn_audit_update(form, resource, representation=None):
    """
    Called during Update operations to enable optional Auditing
    Called as an onaccept so that it only takes effect when saved & can read the new values in:
    crud.settings.update_onaccept = lambda form: shn_audit_update(form, resource, representation)
    """
    if session.s3.audit_write:
        record =  form.vars.id
        new_value = []
        for var in form.vars:
            new_value.append(var + ':' + str(form.vars[var]))
        db.s3_audit.insert(
                person = auth.user.id if session.auth else 0,
                operation = 'update',
                module = request.controller,
                resource = resource,
                record = record,
                representation = representation,
                #old_value = old_value, # Need to store these beforehand if we want them
                new_value = new_value
            )
    return

#
# shn_audit_update_m2m --------------------------------------------------------
#
def shn_audit_update_m2m(resource, record, representation=None):
    """
    Called during Update operations to enable optional Auditing
    Designed for use in M2M 'Update Qty/Delete' (which can't use crud.settings.update_onaccept)
    shn_audit_update_m2m(resource, record, representation)
    """
    if session.s3.audit_write:
        db.s3_audit.insert(
                person = auth.user.id if session.auth else 0,
                operation = 'update',
                module = request.controller,
                resource = resource,
                record = record,
                representation = representation,
                #old_value = old_value, # Need to store these beforehand if we want them
                #new_value = new_value  # Various changes can happen, so would need to store dict of {item_id: qty}
            )
    return

#
# shn_audit_delete ------------------------------------------------------------
#
def shn_audit_delete(resource, record, representation=None):
    "Called during Delete operations to enable optional Auditing"
    if session.s3.audit_write:
        module = request.controller
        table = '%s_%s' % (module, resource)
        old_value = []
        _old_value = db(db[table].id==record).select()[0]
        for field in _old_value:
            old_value.append(field + ':' + str(_old_value[field]))
        db.s3_audit.insert(
                person = auth.user.id if session.auth else 0,
                operation = 'delete',
                module = module,
                resource = resource,
                record = record,
                representation = representation,
                old_value = old_value
            )
    return

# *****************************************************************************
# Display Representations

# t2.itemize now deprecated
# but still used for t2.search

#
# shn_represent ---------------------------------------------------------------
#
def shn_represent(table, module, resource, deletable=True, main='name', extra=None):
    "Designed to be called via table.represent to make t2.search() output useful"
    db[table].represent = lambda table:shn_list_item(table, resource, action='display', main=main, extra=shn_represent_extra(table, module, resource, deletable, extra))
    return

#
# shn_represent_extra ---------------------------------------------------------
#
def shn_represent_extra(table, module, resource, deletable=True, extra=None):
    "Display more than one extra field (separated by spaces)"
    authorised = shn_has_permission('delete', table)
    item_list = []
    if extra:
        extra_list = extra.split()
        for any_item in extra_list:
            item_list.append("TD(db(db.%s_%s.id==%i).select()[0].%s)" % (module, resource, table.id, any_item))
    if authorised and deletable:
        item_list.append("TD(INPUT(_type='checkbox', _class='delete_row', _name='%s', _id='%i'))" % (resource, table.id))
    return ','.join( item_list )

#
# shn_list_item ---------------------------------------------------------------
#
def shn_list_item(table, resource, action, main='name', extra=None):
    "Display nice names with clickable links & optional extra info"
    item_list = [TD(A(table[main], _href=URL(r=request, f=resource, args=[action, table.id])))]
    if extra:
        item_list.extend(eval(extra))
    items = DIV(TABLE(TR(item_list)))
    return DIV(*items)

#
# pagenav ---------------------------------------------------------------------
#
def pagenav(page=1, totalpages=None, first='1', prev='<', next='>', last='last', pagenums=10):
    '''
      Generate a page navigator around current record number, eg 1 < 3 4 5 > 36
      Derived from: http://99babysteps.appspot.com/how2/default/article_read/2
    '''
    if not totalpages:
        maxpages = page + 1
    else:
        maxpages = totalpages
        page = min(page, totalpages)
    pagerange = pagenums / 2 # half the page numbers will be below the startpage, half above
    # create page selector list eg 1 2 3
    pagelinks = [i for i in range(max(1, page - pagerange), min(page + pagerange, maxpages) + 1)]
    startpagepos = pagelinks.index(page)
    # make pagelist into hyperlinks:
    pagelinks = [A(str(pagelink), _href=URL(r=request, vars={'page':pagelink})) for pagelink in pagelinks]
    # remove link to current page & make text emphasised:
    pagelinks[startpagepos] = B(str(page))
    if page < maxpages:
        nextlink = A(next, _href=URL(r=request, vars={'page':page + 1}))
    else:
        # no link if no next
        nextlink = next
    if page > 1:
        prevlink = A(prev, _href=URL(r=request, vars={'page':page - 1}))
        firstlink = A(first, _href=URL(r=request, vars={'page':1}))
    else:
        # no links if no prev
        prevlink = prev
        firstlink = DIV(first)
    if last <> '':
        if totalpages > 0:
            lasttext = last + '(' + str(totalpages) + ')'
        else:
            lasttext = last + '...'
    lastlink = A(lasttext, _href=URL(r=request, vars={'page':maxpages}))
    delim = XML('&nbsp;') # nonbreaking delim
    pagenav = firstlink
    pagenav.append(delim)
    pagenav.append(prevlink)
    pagenav.append(delim)
    for pageref in pagelinks:
        pagenav.append(pageref)
        pagenav.append(delim)
    pagenav.append(nextlink)
    pagenav.append(delim)
    pagenav.append(lastlink)
    return pagenav

#
# shn_custom_view -------------------------------------------------------------
#
def shn_custom_view(jr, default_name):

    if jr.jresource:

        custom_view = '%s_%s_%s' % (jr.resource, jr.jresource, default_name)
        _custom_view = os.path.join(request.folder, 'views', jr.module, custom_view)

        if not os.path.exists(_custom_view):
            custom_view = '%s_%s' % (jr.resource, default_name)
            _custom_view = os.path.join(request.folder, 'views', jr.module, custom_view)

    else:
        custom_view = '%s_%s' % (jr.resource, default_name)
        _custom_view = os.path.join(request.folder, 'views', jr.module, custom_view)


    if os.path.exists(_custom_view):
        response.view = jr.module + '/' + custom_view
    else:
        response.view = default_name

# *****************************************************************************
# CRUD Functions

#
# shn_read --------------------------------------------------------------------
#
def shn_read(jr, editable=True, deletable=True):
    """
        Read a single record
    """
    # No next, since no submit
    print "audit_read"
    if jr.representation=="html":
        shn_custom_view(jr, 'display.html')
        # Takes:
        #  title, pheader, subtitle, edit, item, delete, list_btn
        item = 'read %s %s' % (jr.resource, jr.jresource)
        return dict(item=item)
    else:
        session.error = BADFORMAT
        redirect(URL(r=request, f='index'))

#
# shn_list --------------------------------------------------------------------
#
def shn_list(jr, listadd=True, main=None, extra=None, orderby=None, sortby=None, onvalidation=None, onaccept=None):
    """
        List records matching the request
    """
    # No next, since always returning to itself
    print "audit_list"
    if jr.representation=="html":
        shn_custom_view(jr, 'list.html')
        # Takes (list.html):
        #  title, pheader, subtitle, items, add_btn
        # Takes (list_create.html):
        #  title, pheader, subtitle, items, addtitle, form
        items = 'list %s %s' % (jr.resource, jr.jresource)
        return dict(items=items)
    else:
        session.error = BADFORMAT
        redirect(URL(r=request, f='index'))

#
# shn_create ------------------------------------------------------------------
#
def shn_create(jr, onvalidation=None, onaccept=None, next=None):
    """
        Create a new record
    """
    print "audit_create"
    if jr.representation=="html":
        shn_custom_view(jr, 'create.html')
        # Takes:
        #  title, pheader, subtitle, form, list_btn
        form = 'create %s %s' % (jr.resource, jr.jresource)
        return dict(form=form)
    else:
        session.error = BADFORMAT
        redirect(URL(r=request, f='index'))

#
# shn_update ------------------------------------------------------------------
#
def shn_update(jr, deletable=True, onvalidation=None, onaccept=None, next=None):
    """
        Update an existing record
    """
    print "audit_update"
    if jr.representation=="html":
        shn_custom_view(jr, 'update.html')
        # Takes:
        #  title, pheader, subtitle, form, list_btn
        form = 'update %s %s' % (jr.resource, jr.jresource)
        return dict(form=form)
    else:
        session.error = BADFORMAT
        redirect(URL(r=request, f='index'))

#
# shn_delete ------------------------------------------------------------------
#
def shn_delete(jr, onvalidation, onaccept):
    """
        Delete record(s)
    """
    # No next, since nothing to display - controller fixes the return
    print "audit_delete"
    print 'delete %s %s' % (jr.resource, jr.jresource)
    return

# *****************************************************************************
# Main controller function

#
# shn_rest_controller ---------------------------------------------------------
#
def shn_rest_controller(module, resource,
    deletable=True,
    editable=True,
    listadd=True,
    main='name',
    extra=None,
    orderby=None,
    sortby=None,
    pheader=None,
    onvalidation=None,
    onaccept=None):
    """
    RESTlike controller function.

    Provides CRUD operations for the given module/resource.

    Optional parameters:
        deletable=False                 don't provide visible options for deletion
        editable=False                  don't provide visible options for editing
        listadd=False                   don't provide an add form in the list view
        main='field'                    the field used for the title in RSS output
        extra='field'                   the field used for the description in RSS output & in Search AutoComplete
        orderby=expression              the sort order for server-side paginated list views e.g: db.mytable.myfield1|db.mytable.myfield2
        sortby=list                     the sort order for client-side paginated list views e.g: [[1, "asc"], [2, "desc"]]
            see: http://datatables.net/examples/basic_init/table_sorting.html

        onvalidation=lambda form: function(form)    callback processed *before* DB IO
        onaccept=lambda form: function(form)        callback processed *after* DB IO

        pheader=function(resource, record_id, representation, next=there, same=same)
                                        function to produce a page header for the primary resource

    Request options:

        request.filter              contains custom query to filter list views

    Customisable Security Policy
    Auditing options for Read &/or Write.

    Representation is recognized from the extension of the target resource.
    You can still pass a "?format=" to override this.

    Supported Representations:
        HTML                        is the default (including full Layout)
        PLAIN                       is HTML with no layout
                                        - can be inserted into DIVs via AJAX calls
                                        - can be useful for clients on low-bandwidth or small screen sizes
        JSON                        designed to be accessed via JavaScript
                                        - responses in JSON format
                                        - create/update/delete done via simple GET vars (no form displayed)
        CSV                         useful for synchronization / database migration
                                        - List/Display/Create for now
        RSS (list only)
        XML (list/read only)
        AJAX (designed to be run asynchronously to refresh page elements)
        POPUP
        XLS (list/read only)
        PDF (list/read only)

    ToDo:
        Alternate Representations
            CSV update
            SMS, LDIF
    """

    # Parse original request --------------------------------------------------

    jr = JRequest(jrlayer, request, session=session)

    # Invalid request?
    if jr.invalid:
        if jr.badmethod:
            session.error = BADMETHOD
        elif jr.badrecord:
            session.error = BADRECORD
        elif jr.badformat:
            session.error = BADFORMAT
        else:
            session.error = INVALIDREQUEST
        redirect(URL(r=request, c=module, f='index'))

    # Get backlinks
    here = jr.here()
    there = jr.there()
    same = jr.same()

    # Check read permission on primary table
    if not shn_has_permission('read', jr.table):
        session.error = UNAUTHORIZED
        redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here}))

    # Record ID is required in joined-table operations and read action:
    if not jr.record_id and (jr.jresource or jr.method=="read"):

        # TODO: Cleanup - this is PR specific
        if jr.module=="pr" and jr.resource=="person" and jr.representation=='html':
            redirect(URL(r=request, c='pr', f='person', args='search_simple', vars={"_next": same}))

        else:
            session.error = BADRECORD
            redirect(URL(r=request, c=module, f='index'))

    # *************************************************************************
    # Joined Table Operation

    if jr.jresource:
        if jr.method and jr.custom_action:
            try:
                return(jr.custom_action(
                    jr.module,
                    jr.resource,
                    jr.record_id,
                    jr.method,
                    jmodule=jr.jmodule,
                    jresource=jr.jresource,
                    jrecord_id=jr.jrecord_id,
                    joinby=jr.fkey,
                    multiple=jr.multiple,
                    representation=jr.representation,
                    onvalidation=None,
                    onaccept=None))
            except:
                raise HTTP(501)

        # HTTP Multi-Record Operation *****************************************
        if jr.method==None and jr.multiple and not jr.jrecord_id:

            # HTTP List/List-add ----------------------------------------------
            if jr.http=='GET' or jr.http=='POST':
                authorised = shn_has_permission('read', jr.jtable)
                if authorised:
                    return shn_list(jr)
                else:
                    session.error = UNAUTHORIZED
                    redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here }))

            # HTTP Create -----------------------------------------------------
            elif jr.http=='PUT':
                # Not implemented
                raise HTTP(501)

            # HTTP Delete -----------------------------------------------------
            elif jr.http=='DELETE':
                # Not implemented
                raise HTTP(501)

            # Unsupported HTTP method -----------------------------------------
            else:
                # Unsupported HTTP method for this context:
                # HEAD, OPTIONS, TRACE, CONNECT
                # Not implemented
                raise HTTP(501)

        # HTTP Single-Record Operation ****************************************
        elif jr.method==None and (jr.jrecord_id or not jr.multiple):

            # HTTP Read/Update ------------------------------------------------
            if jr.http=='GET':
                authorised = shn_has_permission('read', jr.jtable)
                if authorised:
                    return shn_read(jr)
                else:
                    session.error = UNAUTHORIZED
                    redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here }))

            # HTTP Update -----------------------------------------------------
            elif jr.http=='PUT':
                # Not implemented
                raise HTTP(501)

            # HTTP Delete -----------------------------------------------------
            elif jr.http=='DELETE':
                # Not implemented
                raise HTTP(501)
        
            # Unsupported HTTP method -----------------------------------------
            else:
                # Unsupported HTTP method for this context:
                # POST, HEAD, OPTIONS, TRACE, CONNECT
                # Not implemented
                raise HTTP(501)

        # Create (joined table) ************************************************
        elif jr.method=="create":
            authorised = shn_has_permission(jr.method, jr.jtable)
            if authorised:
                return shn_create(jr)
            else:
                session.error = UNAUTHORIZED
                redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here}))

        # Read (joined table) *************************************************
        elif jr.method=="read" or jr.method=="display":
            authorised = shn_had_permission('read', jr.jtable)
            if authorised:
                if jr.multiple and not jr.jrecord_id:
                    # This is a list action
                    return shn_list(jr)
                else:
                    # This is a read action
                    return shn_read(jr)
            else:
                session.error = UNAUTHORIZED
                redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here }))

        # Update (joined table) ***********************************************
        elif jr.method=="update":
            authorised = shn_has_permission(jr.method, jr.jtable)
            if authorised:
                return shn_update(jr)
            else:
                session.error = UNAUTHORIZED
                redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here}))

        # Delete (joined table) ***********************************************
        elif jr.method=="delete":
            authorised = shn_has_permission(jr.method, jr.jtable)
            if authorised:
                shn_delete(jr)
                redirect(there)
            else:
                session.error = UNAUTHORIZED
                redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here}))

        # Unsupported Method **************************************************
        else:
            session.error = BADMETHOD
            redirect(URL(r=request, c=module, f='index'))

    # *************************************************************************
    # Single Table Operation
    #
    else:

        # Custom Method *******************************************************
        if jr.method and jr.custom_action:
            try:
                return(jr.custom_action(
                    jr.module,
                    jr.resource,
                    jr.record_id,
                    jr.method,
                    jmodule=None,
                    jresource=None,
                    jrecord_id=None,
                    joinby=None,
                    multiple=True,
                    representation=jr.representation,
                    onvalidation=onvalidation,
                    onaccept=onaccept))
            except:
                raise HTTP(501)

        # Clear Session *******************************************************
        elif jr.method=="clear":

            # Clear session
            jrlayer.clear_session(session, jr.module, jr.resource)

            if '_next' in request.vars:
                request_vars = dict(_next=request.vars._next)
            else:
                request_vars = {}

            # Redirect to search
            # TODO: build a generic search function, this here is PR specific
            if jr.module=="pr" and jr.resource=="person" and jr.representation=="html":
                redirect(URL(r=request, c='pr', f='person', args='search_simple', vars=request_vars))
            else:
                redirect(URL(r=request, c='pr', f=jr.resource))

        # HTTP Multi-Record Operation *****************************************
        elif not jr.method and not jr.record_id:

            # HTTP List or List-Add -------------------------------------------
            if jr.http == 'GET' or request.env.request_method == 'POST':
                return shn_list(jr)

            # HTTP Create -----------------------------------------------------
            elif jr.http == 'PUT':
                # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6
                # Not implemented
                raise HTTP(501)

            # Unsupported HTTP method -----------------------------------------
            else:
                # Unsupported HTTP method for this context:
                # DELETE, HEAD, OPTIONS, TRACE, CONNECT
                # Not implemented
                raise HTTP(501)

        # HTTP Single Record Operation ****************************************
        elif jr.record_id and not jr.method:

            # HTTP Read (single record) ---------------------------------------
            if jr.http == 'GET':
                return shn_read(jr)

            # HTTP Delete (single record) -------------------------------------
            elif jr.http == 'DELETE':
                # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.7
                if db(db[jr.table].id == jr.record_id).select():
                    authorised = shn_has_permission('delete', jr.table, jr.record_id)
                    if authorised:
                        shn_delete(jr)
                        item = '{"Status":"OK","Error":{"StatusCode":200}}'
                        response.view = 'plain.html'
                        return dict(item=item)
                    else:
                        # Unauthorised
                        raise HTTP(401)
                else:
                    # Not found
                    raise HTTP(404)

            # HTTP Create/Update (single record) ------------------------------
            elif jr.http == 'PUT':
                # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6
                # We don't yet implement PUT for create/update, although Web2Py does now support it
                # Not implemented
                raise HTTP(501)

                # HTTP Update (single record) ---------------------------------
                #if db(db[jr.table].id == jr.record_id).select():

                # HTTP Create (single record) ---------------------------------
                #else:

            # Unsupported HTTP method -----------------------------------------
            else:
                # Unsupported HTTP method for this context:
                # POST, HEAD, OPTIONS, TRACE, CONNECT
                # Not implemented
                raise HTTP(501)

        # Create (single table) ***********************************************
        elif jr.method == "create":
            authorised = shn_has_permission(jr.method, jr.table)
            if authorised:
                return shn_create(jr)
            else:
                session.error = UNAUTHORISED
                redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here}))

        # Read (single table) *************************************************
        elif jr.method == "read" or jr.method == "display":
            request.args.remove(jr.method)
            redirect(URL(r=request, args=request.args))

        # Update (single table) ***********************************************
        elif jr.method == "update":
            authorised = shn_has_permission(jr.method, jr.table, jr.record_id)
            if authorised:
                return shn_update(jr)
            else:
                session.error = UNAUTHORISED
                redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here}))

        # Delete (single table) ***********************************************
        elif jr.method == "delete":
            authorised = shn_has_permission(jr.method, jr.table, jr.record_id)
            if authorised:
                return shn_delete(jr)
                redirect(there)
            else:
                session.error = UNAUTHORISED
                redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here}))

        # Search (single table) ***********************************************
        elif jr.method == "search":
            authorised = shn_has_permission('read', jr.table)
            if authorised:
                # Filter Search list to just those records which user can read
                #query = shn_accessible_query('read', table)
                # Fails on t2's line 739: AttributeError: 'SQLQuery' object has no attribute 'get'

                # Audit
                shn_audit_read(operation='search', resource=jr.resource, representation=jr.representation)

                if jr.representation == "html":

                    shn_represent(jr.table, jr.module, jr.resource, deletable, main, extra)
                    #search = t2.search(table, query)
                    search = t2.search(jr.table)

                    # Check for presence of Custom View
                    shn_custom_view(jr, 'search.html')

                    # CRUD Strings
                    title = s3.crud_strings.title_search

                    return dict(module_name=module_name, search=search, title=title)

                if representation == "json":
                    # JQuery Autocomplete uses 'q' instead of 'value'
                    value = request.vars.value or request.vars.q or None
                    if request.vars.field and request.vars.filter and value:
                        field = str.lower(request.vars.field)
                        filter = request.vars.filter
                        if filter == '=':
                            query = (jr.table[field]==value)
                            item = db(query).select().json()
                        elif filter == '~':
                            query = (jr.table[field].like('%' + value + '%'))
                            limit = int(request.vars.limit) or None
                            if limit:
                                item = db(query).select(limitby=(0, limit)).json()
                            else:
                                item = db(query).select().json()
                        else:
                            item = '{"Status":"failed","Error":{"StatusCode":501,"Message":"Unsupported filter! Supported filters: =, ~"}}'
                    else:
                        item = '{"Status":"failed","Error":{"StatusCode":501,"Message":"Search requires specifying Field, Filter & Value!"}}'
                    response.view = 'plain.html'
                    return dict(item=item)

                else:
                    session.error = BADFORMAT
                    redirect(URL(r=request))
            else:
                session.error = UNAUTHORISED
                redirect(URL(r=request, c='default', f='user', args='login', vars={'_next': here}))

        # Unsupported Method **************************************************
        else:
            session.error = BADMETHOD
            redirect(URL(r=request))

# END
# *****************************************************************************
