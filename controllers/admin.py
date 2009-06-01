module = 'admin'
# Current Module (for sidebar title)
module_name = db(db.s3_module.name==module).select()[0].name_nice
# Options Menu (available in all Functions' Views)
# - can Insert/Delete items from default menus within a function, if required.
# NB Sync manually with the copy in 'appadmin.py'
response.menu_options = [
    [T('Home'), False, URL(r=request, c='admin', f='index')],
    [T('Settings'), False, URL(r=request, c='admin', f='setting', args=['update', 1])],
    [T('User Management'), False, '#', [
        [T('Users'), False, URL(r=request, c='admin', f='user')],
        [T('Roles'), False, URL(r=request, c='admin', f='group')],
        #[T('Membership'), False, URL(r=request, c='admin', f='membership')]
    ]],
    [T('Database'), False, '#', [
        [T('Import'), False, URL(r=request, c='admin', f='import_data')],
        [T('Export'), False, URL(r=request, c='admin', f='export_data')],
        [T('Raw Database access'), False, URL(r=request, c='appadmin', f='index')]
    ]],
    [T('Edit Application'), False, URL(r=request, a='admin', c='default', f='design', args=['sahana'])],
    [T('Functional Tests'), False, URL(r=request, c='static', f='selenium', args=['core', 'TestRunner.html'], vars=dict(test='../tests/TestSuite.html', auto='true', resultsUrl=URL(r=request, c='admin', f='handleResults')))]
]

# S3 framework functions
def index():
    "Module's Home Page"
    return dict(module_name=module_name)

@auth.requires_membership('Administrator')
def setting():
    "RESTlike CRUD controller"
    s3.crud_strings.setting.label_list_button = None
    return shn_rest_controller('s3', 'setting', deletable=False)

@auth.requires_membership('Administrator')
def user():
    "RESTlike CRUD controller"
    # Add users to Person Registry & 'Authenticated' role
    crud.settings.create_onaccept = lambda form: auth.register_post(form)
    # Allow the ability for admin to Disable logins
    db.auth_user.registration_key.writable = True
    db.auth_user.registration_key.label = T('Disabled?')
    db.auth_user.registration_key.requires = IS_IN_SET(['','disabled'])
    return shn_rest_controller('auth', 'user', main='first_name', extra='last_name', format='table')
    
@auth.requires_membership('Administrator')
def group():
    "RESTlike CRUD controller"
    return shn_rest_controller('auth', 'group', main='role', extra='description', format='table')
    
# Unused as poor UI
@auth.requires_membership('Administrator')
def membership():
    "RESTlike CRUD controller"
    return shn_rest_controller('auth', 'membership', main='user_id', extra='group_id', format='table')
    
@auth.requires_membership('Administrator')
def users():
    "List/amend which users are in a Group"
    if len(request.args) == 0:
        session.error = T("Need to specify a role!")
        redirect(URL(r=request, f='group'))
    group = request.args[0]
    table = db.auth_membership
    query = table.group_id==group
    title = str(T('Role')) + ': ' + db.auth_group[group].role
    description = db.auth_group[group].description
    # Start building the Return
    output = dict(module_name=module_name, title=title, description=description, group=group)

    # Many<>Many selection (Deletable, no Quantity)
    item_list = []
    sqlrows = db(query).select()
    forms = Storage()
    even = True
    for row in sqlrows:
        if even:
            theclass = "even"
            even = False
        else:
            theclass = "odd"
            even = True
        id = row.user_id
        item_first = db.auth_user[id].first_name
        item_second = db.auth_user[id].last_name
        item_description = db.auth_user[id].email
        id_link = A(id,_href=URL(r=request,f='user',args=['read', id]))
        checkbox = INPUT(_type="checkbox", _value="on", _name=id, _class="remove_item")
        item_list.append(TR(TD(id_link), TD(item_first), TD(item_second), TD(item_description), TD(checkbox), _class=theclass))
        
    table_header = THEAD(TR(TH('ID'), TH(T('First Name')), TH(T('Last Name')), TH(T('Email')), TH(T('Remove'))))
    table_footer = TFOOT(TR(TD(_colspan=4), TD(INPUT(_id='submit_delete_button', _type='submit', _value=T('Remove')))))
    items = DIV(FORM(TABLE(table_header, TBODY(item_list), table_footer, _id="table-container"), _name='custom', _method='post', _enctype='multipart/form-data', _action=URL(r=request, f='group_remove_users', args=[group])))
        
    subtitle = T("Users")
    crud.messages.submit_button=T('Add')
    crud.messages.record_created = T('Role Updated')
    form = crud.create(table, next=URL(r=request, args=[group]))
    addtitle = T("Add New User to Role")
    output.update(dict(subtitle=subtitle, items=items, addtitle=addtitle, form=form))
    return output

@auth.requires_membership('Administrator')
def group_remove_users():
    "Remove users from a group"
    if len(request.args) == 0:
        session.error = T("Need to specify a group!")
        redirect(URL(r=request, f='group'))
    group = request.args[0]
    table = db.auth_membership
    for var in request.vars:
        user = var
        query = (table.group_id==group) & (table.user_id==user)
        db(query).delete()
    session.flash = T("Users removed")
    redirect(URL(r=request, f='users', args=[group]))

@auth.requires_membership('Administrator')
def groups():
    "List/amend which groups a User is in"
    if len(request.args) == 0:
        session.error = T("Need to specify a user!")
        redirect(URL(r=request, f='user'))
    user = request.args[0]
    table = db.auth_membership
    query = table.user_id==user
    title = db.auth_user[user].first_name + ' ' + db.auth_user[user].last_name
    description = db.auth_user[user].email
    # Start building the Return
    output = dict(module_name=module_name, title=title, description=description, user=user)

    # Many<>Many selection (Deletable, no Quantity)
    item_list = []
    sqlrows = db(query).select()
    forms = Storage()
    even = True
    for row in sqlrows:
        if even:
            theclass = "even"
            even = False
        else:
            theclass = "odd"
            even = True
        id = row.group_id
        forms[id] = SQLFORM(table, id)
        if forms[id].accepts(request.vars, session):
            response.flash = T("Membership Updated")
        item_first = db.auth_group[id].role
        item_description = db.auth_group[id].description
        id_link = A(id, _href=URL(r=request, f='group', args=['read', id]))
        checkbox = INPUT(_type="checkbox", _value="on", _name=id, _class="remove_item")
        item_list.append(TR(TD(id_link), TD(item_first), TD(item_description), TD(checkbox), _class=theclass))
        
    table_header = THEAD(TR(TH('ID'), TH(T('Role')), TH(T('Description')), TH(T('Remove'))))
    table_footer = TFOOT(TR(TD(_colspan=3), TD(INPUT(_id='submit_delete_button', _type='submit', _value=T('Remove')))))
    items = DIV(FORM(TABLE(table_header, TBODY(item_list), table_footer, _id="table-container"), _name='custom', _method='post', _enctype='multipart/form-data', _action=URL(r=request, f='user_remove_groups', args=[user])))
        
    subtitle = T("Roles")
    crud.messages.submit_button=T('Add')
    crud.messages.record_created = T('User Updated')
    form = crud.create(table, next=URL(r=request, args=[user]))
    addtitle = T("Add New Role to User")
    output.update(dict(subtitle=subtitle, items=items, addtitle=addtitle, form=form))
    return output

@auth.requires_membership('Administrator')
def user_remove_groups():
    "Remove groups from a user"
    if len(request.args) == 0:
        session.error = T("Need to specify a user!")
        redirect(URL(r=request, f='user'))
    user = request.args[0]
    table = db.auth_membership
    for var in request.vars:
        group = var
        query = (table.group_id==group) & (table.user_id==user)
        db(query).delete()
    session.flash = T("Groups removed")
    redirect(URL(r=request, f='groups', args=[user]))

# Import Data
@auth.requires_membership('Administrator')
def import_data():
    "Import data via POST upload to CRUD controller."
    title = T('Import Data')
    return dict(module_name=module_name, title=title)

# Export Data
@auth.requires_login()
def export_data():
    "Export data via CRUD controller."
    title = T('Export Data')
    return dict(module_name=module_name, title=title)

# Functional Testing
def handleResults():
    """Process the POST data returned from Selenium TestRunner.
    The data is written out to 2 files.  The overall results are written to 
    date-time-browserName-metadata.txt as a list of key: value, one per line.  The 
    suiteTable and testTables are written to date-time-browserName-results.html.
    """
    
    if not request.vars.result:
        # No results
        return
    
    # Read in results
    result = request.vars.result
    totalTime = request.vars.totalTime
    numberOfSuccesses = request.vars.numTestPasses
    numberOfFailures = request.vars.numTestFailures
    numberOfCommandSuccesses = request.vars.numCommandPasses
    numberOfCommandFailures = request.vars.numCommandFailures
    numberOfCommandErrors = request.vars.numCommandErrors

    suiteTable = ''
    if request.vars.suite:
        suiteTable = request.vars.suite
    
    testTables = []
    testTableNum = 1
    while request.vars['testTable.%s' % testTableNum]:
        testTable = request.vars['testTable.%s' % testTableNum]
        testTables.append(testTable)
        testTableNum += 1
        try:
            request.vars['testTable.%s' % testTableNum]
            pass
        except:
            break
    
    # Unescape the HTML tables
    import urllib
    suiteTable = urllib.unquote(suiteTable)
    testTables = map(urllib.unquote, testTables)

    # We want to store results separately for each browser
    browserName = getBrowserName(request.env.http_user_agent)
    date = str(request.now)[:-16]
    time = str(request.now)[11:-10]
    time = time.replace(':','-')

    # Write out results
    outputDir = os.path.join(request.folder, 'static', 'selenium', 'results')
    metadataFile = '%s-%s-%s-metadata.txt' % (date, time, browserName)
    dataFile = '%s-%s-%s-results.html' % (date, time, browserName)
    
    #xmlText = '<selenium result="' + result + '" totalTime="' + totalTime + '" successes="' + numberOfCommandSuccesses + '" failures="' + numberOfCommandFailures + '" errors="' + numberOfCommandErrors + '" />'
    f = open(os.path.join(outputDir, metadataFile), 'w')
    for key in request.vars.keys():
        if 'testTable' in key or key in ['log','suite']:
            pass
        else:
            print >> f, '%s: %s' % (key, request.vars[key])
    f.close()

    f = open(os.path.join(outputDir, dataFile), 'w')
    print >> f, suiteTable
    for testTable in testTables:
        print >> f, '<br/><br/>'
        print >> f, testTable
    f.close()
    
    message = DIV(P('Results have been successfully posted to the server here:'),
        P(A(metadataFile, _href=URL(r=request, c='static', f='selenium', args=['results', metadataFile]))),
        P(A(dataFile, _href=URL(r=request, c='static', f='selenium', args=['results', dataFile]))))
    
    response.view = 'display.html'
    title = T('Test Results')
    return dict(module_name=module_name, title=title, item=message)