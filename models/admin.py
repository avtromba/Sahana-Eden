﻿# -*- coding: utf-8 -*-

module = 'admin'

# Settings
resource = 'setting'
table = module + '_' + resource
db.define_table(table,
                Field('audit_read', 'boolean'),
                Field('audit_write', 'boolean'),
                migrate=migrate)

# Import Jobs
resource = 'import_job'
table = '%s_%s' % (module, resource)
db.define_table(table,
                Field('module', 'string',
                      default='or', notnull=True),
                Field('resource', 'string',
                      widget=SQLFORM.widgets.options.widget,
                      default='organisation', notnull=True),
                Field('description', 'string', notnull=True),
                Field('source_file', 'upload', notnull=True),
                Field('status', 'string', default='new', writable=False),
                Field('column_map', 'blob', writable=False, readable=False),
                Field('failure_reason', 'string', writable=False),
                timestamp,
                authorstamp,
                )
db[table].status.requires = IS_IN_SET(['new', 'failed', 'processing', 'completed'])
db[table].module.requires = IS_IN_DB(db, 's3_module.name', '%(name_nice)s')
# TODO(mattb): These need to be pulled dynamically!!
db[table].resource.requires = IS_IN_SET(['organisation', 'office', 'contact'])


# Import lines
resource = 'import_line'
table = '%s_%s' % (module, resource)
db.define_table(table,
                Field('import_job', db.admin_import_job, writable=False),
                Field('line_no', 'integer'),
                Field('valid', 'boolean', writable=False),
                Field('errors', 'string', writable=False),
                Field('status', 'string'),
                Field('data', 'blob', writable=False)
                )
db[table].import_job.requires = IS_IN_DB(db, 'admin_import_job.id', '%(description)')
db[table].status.requires = IS_IN_SET(['ignore', 'import', 'imported'])
