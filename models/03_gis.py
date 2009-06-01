module = 'gis'

# Settings
resource = 'setting'
table = module + '_' + resource
db.define_table(table,
                db.Field('audit_read', 'boolean'),
                db.Field('audit_write', 'boolean'))
# Populate table with Default options
# - deployments can change these live via appadmin
if not len(db().select(db[table].ALL)): 
   db[table].insert(
        # If Disabled at the Global Level then can still Enable just for this Module here
        audit_read = False,
        audit_write = False
    )

# GIS Markers (Icons)
resource = 'marker'
table = module + '_' + resource
db.define_table(table, timestamp, uuidstamp,
                db.Field('name'),
                #db.Field('height', 'integer'), # In Pixels, for display purposes
                #db.Field('width', 'integer'),  # Not needed since we get size client-side using Javascript's Image() class
                db.Field('image', 'upload'))
db[table].uuid.requires = IS_NOT_IN_DB(db, '%s.uuid' % table)
db[table].name.requires = [IS_NOT_EMPTY(), IS_NOT_IN_DB(db, '%s.name' % table)]
db[table].name.comment = SPAN("*", _class="req")
db[table].image.autodelete = True 
# Populate table with Default options
if not len(db().select(db[table].ALL)):
    # We want to start at ID 1
    db[table].truncate() 
    db[table].insert(
        name = "marker",
        # Can't do sub-folders :/
        # need to script a bulk copy & rename
        image = "gis_marker.image.default.png"
    )
    # We should now read in the list of default markers from the filesystem & populate the DB 1 by 1
    # - we need to get the size automatically
    # TEMP: Manual markers for some pre-defined Feature Classes
    db[table].insert(
        name = "shelter",
        image = "gis_marker.image.shelter.png"
    )
title_create = T('Add Marker')
title_display = T('Marker Details')
title_list = T('List Markers')
title_update = T('Edit Marker')
title_search = T('Search Markers')
subtitle_create = T('Add New Marker')
subtitle_list = T('Markers')
label_list_button = T('List Markers')
label_create_button = T('Add Marker')
msg_record_created = T('Marker added')
msg_record_modified = T('Marker updated')
msg_record_deleted = T('Marker deleted')
msg_list_empty = T('No Markers currently available')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
# Reusable field for other tables to reference
marker_id = SQLTable(None,'marker_id',
            db.Field('marker',
                db.gis_marker, requires = IS_NULL_OR(IS_IN_DB(db, 'gis_marker.id', 'gis_marker.name')),
                represent = lambda id: DIV(A(IMG(_src=URL(r=request, c='default', f='download', args=(id and [db(db.gis_marker.id==id).select()[0].image] or ["None"])[0]), _height=40), _class='zoom', _href='#zoom-gis_config-marker-%s' % id), DIV(IMG(_src=URL(r=request, c='default', f='download', args=(id and [db(db.gis_marker.id==id).select()[0].image] or ["None"])[0]),_width=600), _id='zoom-gis_config-marker-%s' % id, _class='hidden')),
                comment = DIV(A(T('Add Marker'), _class='popup', _href=URL(r=request, c='gis', f='marker', args='create', vars=dict(format='plain')), _target='top'), A(SPAN("[Help]"), _class="tooltip", _title=T("Marker|Defines the icon used for display.")))
                ))

# GIS Projections
resource = 'projection'
table = module+'_'+resource
db.define_table(table,timestamp,uuidstamp,
                db.Field('name'),
                db.Field('epsg','integer'),
                db.Field('maxExtent'),
                db.Field('maxResolution','double'),
                db.Field('units'))
db[table].uuid.requires = IS_NOT_IN_DB(db,'%s.uuid' % table)
db[table].name.requires = [IS_NOT_EMPTY(),IS_NOT_IN_DB(db,'%s.name' % table)]
db[table].name.comment = SPAN("*",_class="req")
db[table].epsg.requires = IS_NOT_EMPTY()
db[table].epsg.label = "EPSG"
db[table].epsg.comment = SPAN("*",_class="req")
db[table].maxExtent.requires = IS_NOT_EMPTY()
db[table].maxExtent.label = "maxExtent"
db[table].maxExtent.comment = SPAN("*",_class="req")
db[table].maxResolution.requires = IS_NOT_EMPTY()
db[table].maxResolution.label = "maxResolution"
db[table].maxResolution.comment = SPAN("*",_class="req")
db[table].units.requires = IS_IN_SET(['m','degrees'])
# Populate table with Default options
if not len(db().select(db[table].ALL)): 
   # We want to start at ID 1
   db[table].truncate() 
   db[table].insert(
        uuid = uuid.uuid4(),
        name = "Spherical Mercator",
        epsg = 900913,
        maxExtent = "-20037508, -20037508, 20037508, 20037508.34",
        maxResolution = 156543.0339,
        units = "m"
    )
   db[table].insert(
        uuid = uuid.uuid4(),
        name = "WGS84",
        epsg = 4326,
        maxExtent = "-180,-90,180,90",
        maxResolution = 1.40625,
        units = "degrees"
    )
title_create = T('Add Projection')
title_display = T('Projection Details')
title_list = T('List Projections')
title_update = T('Edit Projection')
title_search = T('Search Projections')
subtitle_create = T('Add New Projection')
subtitle_list = T('Projections')
label_list_button = T('List Projections')
label_create_button = T('Add Projection')
msg_record_created = T('Projection added')
msg_record_modified = T('Projection updated')
msg_record_deleted = T('Projection deleted')
msg_list_empty = T('No Projections currently defined')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
# Reusable field for other tables to reference
projection_id = SQLTable(None,'projection_id',
            db.Field('projection',
                db.gis_projection,requires=IS_NULL_OR(IS_IN_DB(db,'gis_projection.id','gis_projection.name')),
                represent=lambda id: db(db.gis_projection.id==id).select()[0].name,
                comment=''
                ))

# GIS Config
# id=1 = Default settings
# separated from Framework settings above
# ToDo Extend for per-user Profiles - this is the WMC
resource = 'config'
table = module+'_'+resource
db.define_table(table,timestamp,uuidstamp,
				db.Field('lat','double'),
				db.Field('lon','double'),
				db.Field('zoom','integer'),
				projection_id,
				marker_id,
				db.Field('map_height','integer'),
				db.Field('map_width','integer'))
db[table].uuid.requires = IS_NOT_IN_DB(db,'%s.uuid' % table)
db[table].lat.requires = IS_LAT()
db[table].lat.label = T("Latitude")
db[table].lat.comment = DIV(SPAN("*",_class="req"),A(SPAN("[Help]"),_class="tooltip",_title=T("Latitude|Latitude is North-South (Up-Down). Latitude is zero on the equator and positive in the northern hemisphere and negative in the southern hemisphere.")))
db[table].lon.requires = IS_LON()
db[table].lon.label = T("Longitude")
db[table].lon.comment = DIV(SPAN("*",_class="req"),A(SPAN("[Help]"),_class="tooltip",_title=T("Longitude|Longitude is West - East (sideways). Longitude is zero on the prime meridian (Greenwich Mean Time) and is positive to the east, across Europe and Asia.  Longitude is negative to the west, across the Atlantic and the Americas.")))
db[table].zoom.requires = IS_INT_IN_RANGE(0,19)
db[table].zoom.comment = DIV(SPAN("*",_class="req"),A(SPAN("[Help]"),_class="tooltip",_title=T("Zoom|How much detail is seen. A high Zoom level means lot of detail, but not a wide area. A low Zoom level means seeing a wide area, but not a high level of detail.")))
db[table].map_height.requires = [IS_NOT_EMPTY(),IS_ALPHANUMERIC()]
db[table].map_height.comment = SPAN("*",_class="req")
db[table].map_width.requires = [IS_NOT_EMPTY(),IS_ALPHANUMERIC()]
db[table].map_width.comment = SPAN("*",_class="req")
# Populate table with Default options
if not len(db().select(db[table].ALL)): 
   # We want to start at ID 1
   db[table].truncate() 
   db[table].insert(
        lat = "6",
        lon = "79.4",
        zoom = 7,
        projection = 1,
        marker = 1,
        map_height = 600,
        map_width = 800
    )
title_create = T('Add Config')
title_display = T('Config Details')
title_list = T('List Configs')
title_update = T('Edit Config')
title_search = T('Search Configs')
subtitle_create = T('Add New Config')
subtitle_list = T('Configs')
label_list_button = T('List Configs')
label_create_button = T('Add Config')
msg_record_created = T('Config added')
msg_record_modified = T('Config updated')
msg_record_deleted = T('Config deleted')
msg_list_empty = T('No Configs currently defined')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
            
# GIS Features
resource = 'feature_class'
table = module+'_'+resource
db.define_table(table,timestamp,uuidstamp,
                db.Field('name'),
                marker_id,
                db.Field('module'),    # Used to build Edit URL
                db.Field('resource')   # Used to build Edit URL & to provide Attributes to Display
                )
db[table].uuid.requires = IS_NOT_IN_DB(db,'%s.uuid' % table)
db[table].name.requires = [IS_NOT_EMPTY(),IS_NOT_IN_DB(db,'%s.name' % table)]
db[table].name.comment = SPAN("*",_class="req")
db[table].module.requires = IS_IN_DB(db((db.s3_module.enabled=='True') & (~db.s3_module.name.like('default'))),'s3_module.name','s3_module.name_nice')
db[table].resource.requires = IS_NULL_OR(IS_IN_SET(['resource']))
title_create = T('Add Feature Class')
title_display = T('Feature Class Details')
title_list = T('List Feature Classes')
title_update = T('Edit Feature Class')
title_search = T('Search Feature Class')
subtitle_create = T('Add New Feature Class')
subtitle_list = T('Feature Classes')
label_list_button = T('List Feature Classes')
label_create_button = T('Add Feature Class')
msg_record_created = T('Feature Class added')
msg_record_modified = T('Feature Class updated')
msg_record_deleted = T('Feature Class deleted')
msg_list_empty = T('No Feature Classes currently defined')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
# Reusable field for other tables to reference
feature_class_id = SQLTable(None,'feature_class_id',
            db.Field('feature_class',
                db.gis_feature_class,requires=IS_NULL_OR(IS_IN_DB(db,'gis_feature_class.id','gis_feature_class.name')),
                represent=lambda id: (id and [db(db.gis_feature_class.id==id).select()[0].name] or ["None"])[0],
                comment=DIV(A(T('Add Feature Class'),_class='popup',_href=URL(r=request,c='gis',f='feature_class',args='create',vars=dict(format='plain')),_target='top'),A(SPAN("[Help]"),_class="tooltip",_title=T("Feature Class|Defines the marker used for display & the attributes visible in the popup.")))
                ))
# Populate table with Default options
if not len(db().select(db[table].ALL)):
	db[table].insert(
        name = 'Shelter',
        marker = db(db.gis_marker.name=='shelter').select()[0].id,
        module = 'cr',
        resource = 'shelter'
	)

resource = 'feature_metadata'
table = module+'_'+resource
db.define_table(table,timestamp,uuidstamp,authorstamp,
                db.Field('description',length=256),
                person_id,
                db.Field('source'),
                db.Field('accuracy'),       # Drop-down on a IS_IN_SET[]?
                db.Field('sensitivity'),    # Should be turned into a drop-down by referring to AAA's sensitivity table
                db.Field('event_time','datetime'),
                db.Field('expiry_time','datetime'),
                db.Field('url'),
                db.Field('image','upload'))
db[table].uuid.requires = IS_NOT_IN_DB(db,'%s.uuid' % table)
db[table].person_id.represent = lambda id: (id and [db(db.pr_person.id==id).select()[0].name] or ["None"])[0]
db[table].person_id.label = T("Contact")
db[table].event_time.requires = IS_NULL_OR(IS_DATETIME())
db[table].expiry_time.requires = IS_NULL_OR(IS_DATETIME())
db[table].url.requires = IS_NULL_OR(IS_URL())
db[table].url.label = 'URL'
title_create = T('Add Feature Metadata')
title_display = T('Feature Metadata Details')
title_list = T('List Feature Metadata')
title_update = T('Edit Feature Metadata')
title_search = T('Search Feature Metadata')
subtitle_create = T('Add New Feature Metadata')
subtitle_list = T('Feature Metadata')
label_list_button = T('List Feature Metadata')
label_create_button = T('Add Feature Metadata')
msg_record_created = T('Feature Metadata added')
msg_record_modified = T('Feature Metadata updated')
msg_record_deleted = T('Feature Metadata deleted')
msg_list_empty = T('No Feature Metadata currently defined')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)

resource = 'feature'
table = module+'_'+resource
db.define_table(table,timestamp,uuidstamp,
                db.Field('name'),
                feature_class_id,
                marker_id,
                db.Field('metadata',db.gis_feature_metadata),      # NB This can have issues with sync unless going via CSV
                db.Field('type',default='point'),
                db.Field('lat','double'),    # Only needed for Points
                db.Field('lon','double'),    # Only needed for Points
                db.Field('wkt',length=256),  # WKT is auto-calculated from lat/lon for Points
                db.Field('resource_id','integer')) # Used to build Edit URL for Feature Class.
db[table].uuid.requires = IS_NOT_IN_DB(db,'%s.uuid' % table)
db[table].name.requires = IS_NOT_EMPTY()
db[table].name.comment = SPAN("*",_class="req")
db[table].metadata.requires = IS_NULL_OR(IS_IN_DB(db,'gis_feature_metadata.id'))
db[table].metadata.represent = lambda id: (id and [db(db.gis_feature_metadata.id==id).select()[0].description] or ["None"])[0]
db[table].metadata.comment = DIV(A(T('Add Metadata'),_class='popup',_href=URL(r=request,c='gis',f='feature_metadata',args='create',vars=dict(format='plain')),_target='top'),A(SPAN("[Help]"),_class="tooltip",_title=T("Metadata|Additional attributes associated with this Feature.")))
db[table].type.requires = IS_IN_SET(['point','line','polygon'])
db[table].lat.requires = IS_NULL_OR(IS_LAT())
db[table].lat.label = T("Latitude")
db[table].lat.comment = DIV(SPAN("*",_class="req"),A(SPAN("[Help]"),_class="tooltip",_title=T("Latitude|Latitude is North-South (Up-Down). Latitude is zero on the equator and positive in the northern hemisphere and negative in the southern hemisphere.")))
db[table].lon.requires = IS_NULL_OR(IS_LON())
db[table].lon.label = T("Longitude")
db[table].lon.comment = DIV(SPAN("*",_class="req"),A(SPAN("[Help]"),_class="tooltip",_title=T("Longitude|Longitude is West - East (sideways). Longitude is zero on the prime meridian (Greenwich Mean Time) and is positive to the east, across Europe and Asia.  Longitude is negative to the west, across the Atlantic and the Americas.")))
# WKT validation is done in the onvalidation callback
#db[table].wkt.requires=IS_NULL_OR(IS_WKT())
db[table].wkt.label = T("Well-Known Text")
db[table].wkt.comment = DIV(SPAN("*",_class="req"),A(SPAN("[Help]"),_class="tooltip",_title=T("WKT|The <a href='http://en.wikipedia.org/wiki/Well-known_text' target=_blank>Well-Known Text</a> representation of the Polygon/Line.")))
title_create = T('Add Feature')
title_display = T('Feature Details')
title_list = T('List Features')
title_update = T('Edit Feature')
title_search = T('Search Features')
subtitle_create = T('Add New Feature')
subtitle_list = T('Features')
label_list_button = T('List Features')
label_create_button = T('Add Feature')
msg_record_created = T('Feature added')
msg_record_modified = T('Feature updated')
msg_record_deleted = T('Feature deleted')
msg_list_empty = T('No Features currently defined')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
# Reusable field for other tables to reference
feature_id = SQLTable(None,'feature_id',
            db.Field('feature',
                db.gis_feature,requires=IS_NULL_OR(IS_IN_DB(db,'gis_feature.id','gis_feature.name')),
                represent=lambda id: (id and [db(db.gis_feature.id==id).select()[0].name] or ["None"])[0],
                comment=DIV(A(T('Add Feature'),_class='popup',_href=URL(r=request,c='gis',f='feature',args='create',vars=dict(format='plain')),_target='top'),A(SPAN("[Help]"),_class="tooltip",_title=T("Feature|The centre Point or Polygon used to display this Location on a Map.")))
                ))
    
# Feature Groups
# Used to select a set of Features for either Display or Export
resource = 'feature_group'
table = module+'_'+resource
db.define_table(table,timestamp,uuidstamp,
                db.Field('author',db.auth_user,writable=False), #,default=session.auth.user.id
                db.Field('name'),
                db.Field('description',length=256),
                db.Field('features','text'),        # List of features (to be replaced by many-to-many table)
                db.Field('feature_classes','text'), # List of feature classes (to be replaced by many-to-many table)
                db.Field('display','boolean',default='True'))
db[table].uuid.requires = IS_NOT_IN_DB(db,'%s.uuid' % table)
db[table].author.requires = IS_IN_DB(db,'auth_user.id','%(id)s: %(first_name)s %(last_name)s')
db[table].name.requires = [IS_NOT_EMPTY(),IS_NOT_IN_DB(db,'%s.name' % table)]
db[table].name.comment = SPAN("*",_class="req")
db[table].features.comment = A(SPAN("[Help]"),_class="tooltip",_title=T("Multi-Select|Click Features to select, Click again to Remove. Dark Green is selected."))
db[table].feature_classes.comment = A(SPAN("[Help]"),_class="tooltip",_title=T("Multi-Select|Click Features to select, Click again to Remove. Dark Green is selected."))
title_create = T('Add Feature Group')
title_display = T('Feature Group Details')
title_list = T('List Feature Groups')
title_update = T('Edit Feature Group')
title_search = T('Search Feature Groups')
subtitle_create = T('Add New Feature Group')
subtitle_list = T('Feature Groups')
label_list_button = T('List Feature Groups')
label_create_button = T('Add Feature Group')
msg_record_created = T('Feature Group added')
msg_record_modified = T('Feature Group updated')
msg_record_deleted = T('Feature Group deleted')
msg_list_empty = T('No Feature Groups currently defined')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
# Reusable field for other tables to reference
feature_group_id = SQLTable(None,'feature_group_id',
            db.Field('feature_group',
                db.gis_feature_group,requires=IS_NULL_OR(IS_IN_DB(db,'gis_feature_group.id','gis_feature_group.name')),
                represent=lambda id: (id and [db(db.gis_feature_group.id==id).select()[0].name] or ["None"])[0],
                comment=''
                ))

            
# Many-to-Many tables
# are we using these or a tag-like pseudo M2M?
resource = 'feature_to_feature_group'
table = module+'_'+resource
db.define_table(table,timestamp,
                feature_group_id,
                feature_id)
                
resource = 'feature_class_to_feature_group'
table = module+'_'+resource
db.define_table(table,timestamp,
                feature_group_id,
                feature_class_id)

resource = 'landmark'
table = module+'_'+resource
db.define_table(table,timestamp,uuidstamp,authorstamp,
                db.Field('name'),
                db.Field('type'),
                db.Field('description',length=256),
                db.Field('url'),
                db.Field('image','upload'))
db[table].uuid.requires = IS_NOT_IN_DB(db,'%s.uuid' % table)
db[table].name.requires = IS_NOT_EMPTY()
db[table].name.comment = SPAN("*",_class="req")
db[table].type.requires = IS_NULL_OR(IS_IN_SET(['church','school','hospital']))
db[table].url.requires = IS_NULL_OR(IS_URL())
title_create = T('Add Landmark')
title_display = T('Landmark Details')
title_list = T('List Landmarks')
title_update = T('Edit Landmark')
title_search = T('Search Landmarks')
subtitle_create = T('Add New Landmark')
subtitle_list = T('Landmarks')
label_list_button = T('List Landmarks')
label_create_button = T('Add Landmark')
msg_record_created = T('Landmark added')
msg_record_modified = T('Landmark updated')
msg_record_deleted = T('Landmark deleted')
msg_list_empty = T('No Landmarks currently defined')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)

# GIS Locations
resource = 'location'
table = module+'_'+resource
db.define_table(table,timestamp,uuidstamp,
                db.Field('name'),
                feature_id,         # Either just a Point or a Polygon
                db.Field('sector'), # Government, Health
                db.Field('level'),  # Region, Country, District
                admin_id,
                db.Field('parent', 'reference gis_location'))   # This form of hierarchy may not work on all Databases
db[table].uuid.requires = IS_NOT_IN_DB(db,'%s.uuid' % table)
db[table].name.requires = IS_NOT_EMPTY()       # Placenames don't have to be unique
db[table].feature.label = T("GIS Feature")
db[table].sector.requires = IS_NULL_OR(IS_IN_SET(['Government','Health']))
db[table].level.requires = IS_NULL_OR(IS_IN_SET(['Country','Region','District','Town']))
db[table].parent.requires = IS_NULL_OR(IS_IN_DB(db,'gis_location.id','gis_location.name'))
db[table].parent.represent = lambda id: (id and [db(db.gis_location.id==id).select()[0].name] or ["None"])[0]
title_create = T('Add Location')
title_display = T('Location Details')
title_list = T('List Locations')
title_update = T('Edit Location')
title_search = T('Search Locations')
subtitle_create = T('Add New Location')
subtitle_list = T('Locations')
label_list_button = T('List Locations')
label_create_button = T('Add Location')
msg_record_created = T('Location added')
msg_record_modified = T('Location updated')
msg_record_deleted = T('Location deleted')
msg_list_empty = T('No Locations currently available')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
# Reusable field for other tables to reference
location_id = SQLTable(None,'location_id',
            db.Field('location',
                db.gis_location,requires=IS_NULL_OR(IS_IN_DB(db,'gis_location.id','gis_location.name')),
                represent=lambda id: (id and [db(db.gis_location.id==id).select()[0].name] or ["None"])[0],
                comment=DIV(A(s3.crud_strings.gis_location.label_create_button,_class='popup',_href=URL(r=request,c='gis',f='location',args='create',vars=dict(format='plain')),_target='top'),A(SPAN("[Help]"),_class="tooltip",_title=T("Location|The Location of this Office, which can be general (for Reporting) or precise (for displaying on a Map).")))
                ))

# GIS Keys - needed for commercial mapping services
resource = 'apikey' # Can't use 'key' as this has other meanings for dicts!
table = module+'_'+resource
db.define_table(table,timestamp,
                db.Field('name'),
                db.Field('apikey'),
				db.Field('description',length=256))
# FIXME
# We want a THIS_NOT_IN_DB here: http://groups.google.com/group/web2py/browse_thread/thread/27b14433976c0540/fc129fd476558944?lnk=gst&q=THIS_NOT_IN_DB#fc129fd476558944
db[table].name.requires = IS_IN_SET(['google','multimap','yahoo']) 
db[table].name.label = T("Service")
#db[table].apikey.requires = THIS_NOT_IN_DB(db(db[table].name==request.vars.name),'gis_apikey.name',request.vars.name,'Service already in use')
db[table].apikey.requires = IS_NOT_EMPTY()
db[table].apikey.label = T("Key")
# Populate table with Default options
if not len(db().select(db[table].ALL)): 
   db[table].insert(
        name = "google",
        apikey = "ABQIAAAAgB-1pyZu7pKAZrMGv3nksRRi_j0U6kJrkFvY4-OX2XYmEAa76BSH6SJQ1KrBv-RzS5vygeQosHsnNw",
        description = "localhost"
    )
   db[table].insert(
        name = "yahoo",
        apikey = "euzuro-openlayers",
        description = "To be replaced for Production use"
    )
   db[table].insert(
        name = "multimap",
        apikey = "metacarta_04",
        description = "trial"
    )
title_create = T('Add Key')
title_display = T('Key Details')
title_list = T('List Keys')
title_update = T('Edit Key')
title_search = T('Search Keys')
subtitle_create = T('Add New Key')
subtitle_list = T('Keys')
label_list_button = T('List Keys')
label_create_button = T('Add Key')
msg_record_created = T('Key added')
msg_record_modified = T('Key updated')
msg_record_deleted = T('Key deleted')
msg_list_empty = T('No Keys currently defined')
s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)

# GIS Layers
#gis_layer_types = ['features','georss','kml','gpx','shapefile','scan','google','openstreetmap','virtualearth','wms','yahoo']
gis_layer_types = ['openstreetmap','google','yahoo','virtualearth']
gis_layer_openstreetmap_subtypes = ['Mapnik','Osmarender','Aerial']
gis_layer_google_subtypes = ['Satellite','Maps','Hybrid','Terrain']
gis_layer_yahoo_subtypes = ['Satellite','Maps','Hybrid']
gis_layer_virtualearth_subtypes = ['Satellite','Maps','Hybrid']
# Base table from which the rest inherit
gis_layer = SQLTable(db,'gis_layer',timestamp,
            #uuidstamp, # Layers like OpenStreetMap, Google, etc shouldn't sync
            db.Field('name'),
            db.Field('description',length=256),
            #db.Field('priority','integer'),    # System default priority is set in ol_layers_all.js. User priorities are set in WMC.
            db.Field('enabled','boolean',default=True))
gis_layer.name.requires = IS_NOT_EMPTY()
for layertype in gis_layer_types:
    resource = 'layer_'+layertype
    table = module+'_'+resource
    title_create = T('Add Layer')
    title_display = T('Layer Details')
    title_list = T('List Layers')
    title_update = T('Edit Layer')
    title_search = T('Search Layers')
    subtitle_create = T('Add New Layer')
    subtitle_list = T('Layers')
    label_list_button = T('List Layers')
    label_create_button = T('Add Layer')
    msg_record_created = T('Layer added')
    msg_record_modified = T('Layer updated')
    msg_record_deleted = T('Layer deleted')
    msg_list_empty = T('No Layers currently defined')
    # Create Type-specific Layer tables
    if layertype == "openstreetmap":
        t = SQLTable(db,table,
            db.Field('subtype'),
            gis_layer)
        t.subtype.requires = IS_IN_SET(gis_layer_openstreetmap_subtypes)
        db.define_table(table,t)
        if not len(db().select(db[table].ALL)):
            # Populate table
            for subtype in gis_layer_openstreetmap_subtypes:
                db[table].insert(
                        name = 'OSM '+subtype,
                        subtype = subtype
                    )
        # Customise CRUD strings if-desired
        label_list_button = T('List OpenStreetMap Layers')
        msg_list_empty = T('No OpenStreetMap Layers currently defined')
        s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
    if layertype == "google":
        t = SQLTable(db,table,
            db.Field('subtype'),
            gis_layer)
        t.subtype.requires = IS_IN_SET(gis_layer_google_subtypes)
        db.define_table(table,t)
        if not len(db().select(db[table].ALL)):
            # Populate table
            for subtype in gis_layer_google_subtypes:
                db[table].insert(
                        name = 'Google '+subtype,
                        subtype = subtype,
                        enabled = False
                    )
        # Customise CRUD strings if-desired
        label_list_button = T('List Google Layers')
        msg_list_empty = T('No Google Layers currently defined')
        s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
    if layertype == "yahoo":
        t = SQLTable(db,table,
            db.Field('subtype'),
            gis_layer)
        t.subtype.requires = IS_IN_SET(gis_layer_yahoo_subtypes)
        db.define_table(table,t)
        if not len(db().select(db[table].ALL)):
            # Populate table
            for subtype in gis_layer_yahoo_subtypes:
                db[table].insert(
                        name = 'Yahoo '+subtype,
                        subtype = subtype,
                        enabled = False
                    )
        # Customise CRUD strings if-desired
        label_list_button = T('List Yahoo Layers')
        msg_list_empty = T('No Yahoo Layers currently defined')
        s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
    if layertype == "virtualearth":
        t = SQLTable(db,table,
            db.Field('subtype'),
            gis_layer)
        t.subtype.requires = IS_IN_SET(gis_layer_virtualearth_subtypes)
        db.define_table(table,t)
        if not len(db().select(db[table].ALL)):
            # Populate table
            for subtype in gis_layer_virtualearth_subtypes:
                db[table].insert(
                        name = 'VE '+subtype,
                        subtype = subtype,
                        enabled = False
                    )
        # Customise CRUD strings if-desired
        label_list_button = T('List Virtual Earth Layers')
        msg_list_empty = T('No Virtual Earth Layers currently defined')
        s3.crud_strings[table] = Storage(title_create=title_create,title_display=title_display,title_list=title_list,title_update=title_update,title_search=title_search,subtitle_create=subtitle_create,subtitle_list=subtitle_list,label_list_button=label_list_button,label_create_button=label_create_button,msg_record_created=msg_record_created,msg_record_modified=msg_record_modified,msg_record_deleted=msg_record_deleted,msg_list_empty=msg_list_empty)
    
# GIS Styles: SLD
#db.define_table('gis_style',timestamp,
#                db.Field('name'))
#db.gis_style.name.requires = [IS_NOT_EMPTY(),IS_NOT_IN_DB(db,'gis_style.name')]

# GIS WebMapContexts
# (User preferences)
# GIS Config's Defaults should just be the version for user=0?
#db.define_table('gis_webmapcontext',timestamp,
#                db.Field('user',db.auth_user))
#db.gis_webmapcontext.user.requires = IS_IN_DB(db,'auth_user.id','auth_user.email')

# Onvalidation callbacks
def wkt_centroid(form):
    """GIS
    If a Point has LonLat defined: calculate the WKT.
    If a Line/Polygon has WKT defined: validate the format & calculate the LonLat of the Centroid
    Centroid calculation is done using Shapely, which wraps Geos.
    A nice description of the algorithm is provided here: http://www.jennessent.com/arcgis/shapes_poster.htm
    """
    if form.vars.type == 'point':
        if form.vars.lon == None:
            form.errors['lon'] = T("Invalid: Longitude can't be empty!")
            return
        if form.vars.lat == None:
            form.errors['lat'] = T("Invalid: Latitude can't be empty!")
            return
        form.vars.wkt = 'POINT(%(lon)f %(lat)f)' % form.vars
    elif form.vars.type == 'line':
        try:
            from shapely.wkt import loads
            try:
                line = loads(form.vars.wkt)
            except:
                form.errors['wkt'] = T("Invalid WKT: Must be like LINESTRING(3 4,10 50,20 25)!")
                return
            centroid_point = line.centroid
            form.vars.lon = centroid_point.wkt.split('(')[1].split(' ')[0]
            form.vars.lat = centroid_point.wkt.split('(')[1].split(' ')[1][:1]
        except:
            #form.errors['type'] = str(A('Shapely',_href='http://pypi.python.org/pypi/Shapely/',_target='_blank'))+str(T(" library not found, so can't find centroid!"))
            form.errors['type'] = T("Shapely library not found, so can't find centroid!")
    elif form.vars.type == 'polygon':
        try:
            from shapely.wkt import loads
            try:
                polygon = loads(form.vars.wkt)
            except:
                form.errors['wkt'] = T("Invalid WKT: Must be like POLYGON((1 1,5 1,5 5,1 5,1 1),(2 2, 3 2, 3 3, 2 3,2 2))!")
                return
            centroid_point = polygon.centroid
            form.vars.lon = centroid_point.wkt.split('(')[1].split(' ')[0]
            form.vars.lat = centroid_point.wkt.split('(')[1].split(' ')[1][:1]
        except:
            form.errors['type'] = T("Shapely library not found, so can't find centroid!")
    else:
        form.errors['type'] = T('Unknown type!')
    return