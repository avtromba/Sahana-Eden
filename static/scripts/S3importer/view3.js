function alertmessage3()
{
	$(document).ready(function()
	{
		$("#message2").hide();
		$("#message3").addClass("confirmation");
		$("#message3").show('slow');
	});
}

function view3(importsheet)
{
    var resource_select = new Ext.form.FieldSet({
		items : [
			{
				xtype : 'checkboxgroup',
				id : 'selected_resources',
				fieldLabel : 'Select a module from the list on the left',
				anchor : '100%',
				columns : 3,
				width : 800,
				items : [{boxLabel : 'Then select as many resources as you wish'}]
			}
			]
		});
    var module_select = {
		xtype : 'multiselect',
		singleSelect : true,
		fieldLabel : 'Select module',
		width : 200,
		height : 200,
		name : 'module_selected',
		store : modules_nice_names,
		tbar:[{
                text: 'Clear selection',
                handler: function(){
                    msForm.getForm().findField('module_selected').reset();
                }
            }],
		listeners:{
			'change' : function()
				 {
					 resource_select.removeAll();
					 var mod = msForm.getForm().findField('module_selected').getValue();
					 var modname = modules[mod];
					 //console.log(resources);
					 var importable_resource=[];
					 for(k in resources[modname])
					 {
						 if(resources[modname][k].importer==true)
							importable_resource.push(k);
					 }
					 var num_resource = importable_resource.length;
					 var i = 0;
					 var checkboxes = [];
					 if(num_resource == 0)
						 Ext.Msg.alert("","No resources");
					 while(i<num_resource)
					 {
						checkboxes[i] = {};
						checkboxes[i]['boxLabel'] = importable_resource[i];
						checkboxes[i]['name'] = 'radio';
						i++;
					 }
					 var checkbox_object = {};
					 checkbox_object['items'] = checkboxes;
					 checkbox_object['xtype'] = 'radiogroup';
					 checkbox_object['columns'] = 3;
					 checkbox_object['singleSelect'] = true;
					 checkbox_object['fieldLabel'] = 'Select resources';
					 checkbox_object['width'] = 800;
					 checkbox_object['id'] = 'selected_resources';
					 resource_select.add(checkbox_object);
					 resource_select.doLayout();
				 }
			  }
    	};

    var container = {
		xtype : 'container',
		layout : 'hbox',
		height : 500,
		bodyStyle: 'padding : 10px;',
		layoutConfig : {
			align : 'stretch'
			},
		items : [module_select,resource_select]
		};
    
    var msForm = new Ext.form.FormPanel({
        title: 'Edit \u2794 <u>Select table</u> \u2794 Map columns to fields<br/>Select table to which data will be imported',
        width: 'auto',
        height: 300,
        bodyStyle: 'padding:10px;',
        frame : true,
        delimiter: ',',
        renderTo: 'spreadsheet',
        items: container,
	/*{
            xtype: 'multiselect',
            singleSelect: true,
            fieldLabel: 'Select table',
            name: 'table_selected',
            width: 500,
            height: 200,
            allowBlank:false,
            store: [['org_organisation','Organization Registry'],	//Server call to find component tables here
                    ['org_office', 'Organization Registry-Office'], 
                    ['pr_person', 'Person Registry'], 
                    ['cr_shelter', 'Shelter Registry'],  
                    ['budget_kits', 'Budgetting-Kits'],
                    ['budget_item', 'Budgetting-Items'],
                    ['budget_kit_item','Budgetting-Kits and items']],
	    store : modules,*/
            ddReorder: true,
        buttonAlign: 'center',
        buttons: [
        {
                text: 'Back',
                handler: function(){
                        msForm.hide();
                        view1(importsheet); 
                        }
               },
               {
            text: 'Next',
            handler: function()
            {
                var module = msForm.getForm().findField('module_selected').getValue();
                //console.log(module);
		if(module == 'Multiple rows selected')
                    Ext.Msg.alert("Error","Select one module only");
                else
                    if(module == '')
                        Ext.Msg.alert("Error","You must select a module");
                    else
                        {
                             var final_resources = msForm.getForm().findField('selected_resources').getValue();
			     /*for(var x=0 ; x < final_resources.length ;  x++)
			     {
				     final_resources[x] = final_resources[x].boxLabel;
		             }*/
			     final_resources = final_resources.boxLabel;
			     console.log(final_resources);
			     var get_fields = new Ext.LoadMask(Ext.get('spreadsheet'),{msg : 'Getting fields. This may take a while'});
			     get_fields.enable();
			     get_fields.show();
			     var resource_fields = [];
			     Ext.Ajax.request({
					url : 'http://'+url+'/'+application+'/'+final_resources.replace('_','/')+'/fields.json',
					method : 'GET',
					timeout : 90000,
					async : false,
					callback : function(options,success,response)
						{
							//console.log(response.responseText);
							//console.log("Resource->"+final_resources[x]);
							var tempobj = response.responseText;
							resource_fields = eval('('+ tempobj + ')');
							//get_fields.hide();
							importsheet.module = module;
							importsheet.resource_fields = resource_fields;
							var fields = [];
							var reference_fields = [];
							for(k in resource_fields.field)
							{
							        //console.log(resource_fields.field[k]);
								if ( resource_fields.field[k]['@writable'] == "True" && resource_fields.field[k]['@name'] != 'id' && resource_fields.field[k]['@type'] != 'reference auth_user')
								{
									console.log(resource_fields.field[k]);
									
									if(resource_fields.field[k]['@type'].substring(0,9) == 'reference')
									{
										if(resource_fields.field[k]['@type'] == 'reference s3_source')
											continue;
										reference_fields.push([resource_fields.field[k]['@name'],resource_fields.field[k]['@type'].substring(10)]);
									}
									else
										fields.push(resource_fields.field[k]['@name']);
								}
							}
							console.log('Reference ');
							console.log(reference_fields);
							console.log(' Fields ');
							console.log(fields);
							var nested_fields = 0;
							var nested_resources_structure = {};
						       if(reference_fields.length == 0)
							{
								get_fields.hide();				
								importsheet.final_resources = final_resources;
								importsheet.fields = fields;
								msForm.hide();
								console.log("And all the fields are ");
								console.log(importsheet.fields);
								console.log(nested_resources_structure);
								view4(importsheet);}
							

							
	
							for( var i = 0 ; i < reference_fields.length ; i++)
							{
							        var res = reference_fields[i][1];
							        var field = reference_fields[i][0];
							        //var res = res[0];
								Ext.Ajax.request({
									url : 'http://' + url + '/' + application + '/' + res.replace('_','/') + '/fields.json',
									method : 'GET',
									timeout : 90000,
									field_name : field,
									callback : function(options, success, response)
										{
											nested_fields += 1;
											var fields_ = response.responseText;fields_ = eval( '(' + fields_ + ')');
											nested_resources_structure[fields_['@resource']] = [];
											for(k in fields_.field)
											{
							 				       //console.log(resource_fields.field[k]);
												if ( fields_.field[k]['@writable'] == "True" && fields_.field[k]['@name'] != 'id')// && fields_.field[k]['@type'].substring(0,9) != 'reference')
								{
									
									fields.push(options.field_name + ' --> ' + fields_['@resource'] + ' --> ' + fields_.field[k]['@name']);
									nested_resources_structure[fields_['@resource']].push(fields_.field[k]['@name']);
								}
							}

							if(nested_fields == reference_fields.length)
							{
								get_fields.hide();				
								importsheet.final_resources = final_resources;
								importsheet.fields = fields;
								msForm.hide();
								console.log("And all the fields are ");
								console.log(importsheet.fields);
								console.log(nested_resources_structure);
								view4(importsheet);}
							}
							});
							if(reference_fields.length == 0)
							{
								get_fields.hide();				
								importsheet.final_resources = final_resources;
								importsheet.fields = fields;
								msForm.hide();
								console.log("And all the fields are ");
								console.log(importsheet.fields);
								console.log(nested_resources_structure);
								view4(importsheet);}
							

							}
							
						}
					});
			     /*
			     Ext.Ajax.request({
					url : 'http://'+url+'/'+application+'/'+final_resources[final_resources.length-1].replace('_','/')+'/fields.json',
					method : 'GET',
					timeout : 90000,
					callback : function(options,success,response)
						   {
							  get_fields.hide();
							  resource_fields.push(response.responseText);
							  //console.log("Resources and correspoding fields");
							  //console.log(resource_fields);
						          importsheet.module = module;
			     				  importsheet.resource_fields = resource_fields;
			                                  importsheet.final_resources = final_resources;
			     				  msForm.hide();
                             				  view4(importsheet);
			       			  }
					});
			     */
			     //console.log(resource_fields);
			     //module = module.substring(15);
                             /*importsheet.module = module;
			     importsheet.resource_fields = resource_fields;
			     importsheet.final_resources = final_resources;
			     msForm.hide();
                             view4(importsheet);*/
                        }
                     
              }
                    }
    	 ]
    });
}
