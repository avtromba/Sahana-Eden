# -*- coding: utf-8 -*-

"""
    Mobile Messaging - Controllers
"""

module = 'admin'
# Current Module (for sidebar title)
module_name = db(db.s3_module.name==module).select().first().name_nice
# Options Menu (available in all Functions' Views)
# - can Insert/Delete items from default menus within a function, if required.
response.menu_options = admin_menu_options

# Web2Py Tools functions
def call():
    "Call an XMLRPC, JSONRPC or RSS service"
    # Sync webservices don't use sessions, so avoid cluttering up the storage
    session.forget()
    return service()

# S3 framework functions
def index():
    "Module's Home Page"
    return dict(module_name=module_name)

@auth.requires_membership('Administrator')
def settings():
    "Modem and Mobile related settings"
    module = 'mobile'
    resource = 'settings'
    table = module + '_' + resource

    # Model options
    db[table].port.comment = A(SPAN("[Help]"), _class="tooltip",
        _title=T('Port|The serial port where your modem is connected.'))
    db[table].baud.comment = A(SPAN("[Help]"), _class="tooltip",
        _title=T('Baud|The Baud rate of your modem - Usually listed in your modem manual.'))
    db[table].account_name.comment = A(SPAN("[Help]"), _class="tooltip",
            _title=T('Account Name|Convenient name to identify the account.'))
    db[table].url.comment = A(SPAN("[Help]"), _class="tooltip",
            _title=T('URL|The url for your gateway'))
    db[table].parameters.comment = A(SPAN("[Help]"), _class="tooltip",
            _title=T('Parameters|The parameters for gateway'))
    db[table].message_variable.comment = A(SPAN("[Help]"), _class="tooltip",
            _title=T('Message variable|The message variable used for the gateway'))
    db[table].to_variable.comment = A(SPAN("[Help]"), _class="tooltip",
            _title=T('To variable|The variable containing the phone number '))
#    db[table].preference.comment = A(SPAN("[Help]"), _class="tooltip",
#            _title=T('Preference|Prefered weight assigned to this gatway '))

    # CRUD Strings
    ADD_SETTING = T('Add Setting')
    VIEW_SETTINGS = T('View Settings')
    s3.crud_strings[table] = Storage(
        title_create = ADD_SETTING,
        title_display = T('Setting Details'),
        title_list = VIEW_SETTINGS,
        title_update = T('Edit Mobile Settings'),
        title_search = T('Search Settings'),
        subtitle_list = T('Settings'),
        label_list_button = VIEW_SETTINGS,
        label_create_button = ADD_SETTING,
        msg_record_created = T('Setting added'),
        msg_record_modified = T('Mobile settings updated'),
        msg_record_deleted = T('Setting deleted'),
        msg_list_empty = T('No Settings currently defined'))

    crud.settings.update_next = URL(r=request, args=['update', 1])

    return shn_rest_controller(module, resource, deletable=False, listadd=False)

