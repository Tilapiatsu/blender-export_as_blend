import sys, getopt

def parse_argsv(argv):
	print(argv)
	current_file = ''
	source = ''
	override = ''
	mode = ''
	export_in_new_collection = ''
	new_collection_name = ''
	dependencies_in_dedicated_collection = ''
	pack_external_data = ''
	scene_name = ''
	selected_objects = ''
	parent_collections = ''
	root_collection = ''
	objects_collection_list = ''
	all_objects_collection_hierarchy = ''
	help_command = f'''{argv[0]} -f <current-file>
-s <source>
-o <override> 
-m <mode> 
-N <export_in_new_collection> 
-n <new_collection_name>
-d <dependencies_in_dedicated_collection>
-p <pack_external_data>
-S <scene_name>
-O <selected_objects>
-P <parent_collections>
-r <root_collection>
-l <objects_collection_list>
-H <all_Objects_collection_hierarchy>
'''
	try:
		print('Parsing argv...')
		opts, args = getopt.getopt(argv, "hf:s:o:m:N:n:d:p:S:O:P:r:l:H:", ["help",
													  	"current_file=",
													  	"source=",
														"override=",
													  	"mode=",
														"export_in_new_collection=",
													  	"new_collection_name=",
														"dependencies_in_dedicated_collection=",
														"pack_external_data=",
														"scene_name=",
														"selected_objects=",
														"parent_collections=",
														"root_collection=",
														"objects_collection_list=",
														"all_objects_collection_hierarchy="
													  ])
	except:
		print(help_command)
		sys.exit(2)
	
	for opt, arg in opts:
		print(opt, '=', arg)
		if opt in ("-h", "--help"):
			print(help_command)  # print the help message
			sys.exit(2)
		elif opt in ("-f", "--current_file"):
			current_file = arg
		elif opt in ("-s", "--source"):
			source = arg
		elif opt in ("-o", "--override"):
			override = arg
		elif opt in ("-m", "--mode"):
			mode = arg
		elif opt in ("-N", "--export_in_new_collection"):
			export_in_new_collection = arg
		elif opt in ("-n", "--new_collection_name"):
			new_collection_name = arg
		elif opt in ("-d", "--dependencies_in_dedicated_collection"):
			dependencies_in_dedicated_collection = arg
		elif opt in ("-p", "--pack_external_data"):
			pack_external_data = arg
		elif opt in ("-S", "--scene_name"):
			scene_name = arg
		elif opt in ("-O", "--selected_objects"):
			selected_objects = arg
		elif opt in ("-P", "--parent_collections"):
			parent_collections = arg
		elif opt in ("-r", "--root_collection"):
			root_collection = arg
		elif opt in ("-l", "--objects_collection_list"):
			objects_collection_list = arg
		elif opt in ("-H", "--all_objects_collection_hierarchy"):
			all_objects_collection_hierarchy = arg

	
	return (current_file,
         	source,
			override,
          	mode,
           	eval(export_in_new_collection),
            new_collection_name,
            eval(dependencies_in_dedicated_collection),
            eval(pack_external_data),
            scene_name,
            selected_objects,
            parent_collections,
            root_collection,
            objects_collection_list,
            all_objects_collection_hierarchy
            ) 


def import_command(argv):
	current_file, source, override, mode, export_in_new_collection, new_collection_name, dependencies_in_dedicated_collection, pack_external_data, scene_name, selected_objects, parent_collections, root_collection, objects_collection_list, all_objects_collection_hierarchy = parse_argsv(argv[argv.index("--") + 1:])
	print(current_file, source, override, mode, export_in_new_collection, new_collection_name, dependencies_in_dedicated_collection, pack_external_data, scene_name, selected_objects, parent_collections, root_collection, objects_collection_list, all_objects_collection_hierarchy)

if __name__ == "__main__":
	print('-- RUNNING IMPORT COMMAND --')
	import_command(sys.argv)