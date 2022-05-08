import sys, getopt, bpy, os

class Logger(object):
	def __init__(self, addon_name='ROOT', debug=False):
		self.addon_name = addon_name
		self.debug = debug

	def info(self, message):
		self.print_message(message, 'INFO')

	def debug(self, message):
		self.print_message(message, 'DEBUG')

	def warning(self, message):
		self.print_message(message, 'WARNING')

	def error(self, message):
		self.print_message(message, 'ERROR')

	def print_message(self, message, mode):
		print(f'{self.addon_name} : {mode} : {message}')
  
class ImportCommand():
	def __init__(self, argv, debug=False):
		self.parse_argsv(argv[argv.index("--") + 1:])
		self.debug = debug
		self.log = Logger(addon_name='Import Command', debug=debug)
		
	def parse_argsv(self, argv):
		help_command = f'{argv[0]}'
		help_command += ' -f <source_file>'
		help_command += ' -s <source> '
		help_command += ' -o <override>'
		help_command += ' -m <mode>'
		help_command += ' -X <export_to_clean_file>'
		help_command += ' -c <create_collection_hierarchy>'
		help_command += ' -d <destination>'
		help_command += ' -N <export_in_new_collection>'
		help_command += ' -n <new_collection_name>'
		help_command += ' -D <dependencies_in_dedicated_collection>'
		help_command += ' -p <pack_external_data>'
		help_command += ' -S <scene_name> '
		help_command += ' -O <selected_objects>'
		help_command += ' -P <parent_collections>'
		help_command += ' -C <selected_objects_parent_collection>'
		help_command += ' -r <root_collection_name>'
		help_command += ' -l <objects_collection_list>'
		help_command += ' -H <all_objects_collection_hierarchy>'
		try:
			print('Parsing argv...')
			opts, args = getopt.getopt(argv, "hf:s:o:m:X:c:d:N:n:D:p:S:O:C:P:r:l:H:", ["help",
															"source_file=",
															"source=",
															"override=",
															"mode=",
                                                            "export_to_clean_file=",
                                                            "create_collection_hierarchy=",
															"destination=",
															"export_in_new_collection=",
															"new_collection_name=",
															"dependencies_in_dedicated_collection=",
															"pack_external_data=",
															"scene_name=",
															"selected_objects=",
															"parent_collections=",
                                                            "selected_objects_parent_collection=",
															"root_collection_name=",
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
			elif opt in ("-f", "--source_file"):
				self.source_file = arg
			elif opt in ("-s", "--source"):
				self.source = arg
			elif opt in ("-o", "--override"):
				self.override = arg
			elif opt in ("-m", "--mode"):
				self.mode = arg
			elif opt in ("-X", "--export_to_clean_file"):
				self.export_to_clean_file = eval(arg)
			elif opt in ("-c", "--create_collection_hierarchy"):
				self.create_collection_hierarchy = eval(arg)
			elif opt in ("-d", "--destination"):
				self.destination = arg
			elif opt in ("-N", "--export_in_new_collection"):
				self.export_in_new_collection = eval(arg)
			elif opt in ("-n", "--new_collection_name"):
				self.new_collection_name = arg
			elif opt in ("-D", "--dependencies_in_dedicated_collection"):
				self.dependencies_in_dedicated_collection = eval(arg)
			elif opt in ("-p", "--pack_external_data"):
				self.pack_external_data = eval(arg)
			elif opt in ("-S", "--scene_name"):
				self.scene_name = arg
			elif opt in ("-O", "--selected_objects"):
				self.selected_objects = eval(arg)
			elif opt in ("-P", "--parent_collections"):
				self.parent_collections = eval(arg)
			elif opt in ("-C", "--selected_objects_parent_collection"):
				self.selected_objects_parent_collection = eval(arg)
			elif opt in ("-r", "--root_collection_name"):
				self.root_collection_name = arg
			elif opt in ("-l", "--objects_collection_list"):
				self.objects_collection_list = eval(arg)
			elif opt in ("-H", "--all_objects_collection_hierarchy"):
				self.all_objects_collection_hierarchy = eval(arg)

	def import_command(self):
		if self.export_to_clean_file:
			self.clean_scene()
   
		# Base Command and define the link function
		self.initial_count = len(bpy.data.objects)
		self.initial_objects = [o.name for o in bpy.data.objects]
  
		if self.source == 'CURRENT_SCENE':
			self.import_scene()
		elif self.source == 'SELECTED_OBJECTS':
			self.import_objects()

	def import_scene(self):
		self.log.info(f"Importing Scene {self.scene_name}")
		filepath = os.path.join(self.source_file, 'Scene', self.scene_name)
		directory = os.path.join(self.source_file, 'Scene')

		# Import Scene
		bpy.ops.wm.append(	filepath=filepath,
                    		directory=directory,
		                  	filename=self.scene_name
                     	)
	
	def import_objects(self):
		self.log.info("Importing Objects")
		filepath = os.path.join(self.source_file, 'Object', self.selected_objects[0])
		directory = os.path.join(self.source_file, 'Object')
		files = [{"name": o, "name": o} for o in self.selected_objects]

		# Import Objects
		bpy.ops.wm.link(filepath=filepath, directory=directory, filename = self.selected_objects[0], link = self.mode == 'LINKED', files= files)

		# Register imported_objects
		self.imported_objects = [o for o in bpy.data.objects if o.name not in self.initial_objects]

		# Create New Collection and Link all imported object in it
		if self.export_in_new_collection:
			self.create_and_link_to_new_collection()
		
		# Set root_collection
		condition = self.export_in_new_collection and self.new_collection_name in bpy.data.collections
		self.root_collection = bpy.data.collections[self.new_collection_name] if condition else bpy.context.collection
		self.log.info(f'Root Collection = {self.root_collection.name}')

		# Create Collection Hierarchy
		if self.create_collection_hierarchy:
			self.create_and_link_collection_hierarchy()

		if self.dependencies_in_dedicated_collection:
			self.link_dependencies_in_dedicated_collection()
		elif not self.dependencies_in_dedicated_collection and self.create_collection_hierarchy:
			self.link_dependencies_in_their_respective_collection()

		# Pack Files
		if self.pack_external_data and self.mode == 'APPEND':
			try:
				bpy.ops.file.pack_all()
    
			except RuntimeError as e:
				self.log.error("Cannot pack data or data does not exist on drive.  " + e)
    
		# Save File
		bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=self.destination)

	def create_and_link_to_new_collection(self):
		if self.new_collection_name == '':
			self.report(
				{'ERROR'}, 'Export As Blend : Root collection name is empty, skipping root collection creation.')
			self.export_in_new_collection = False
		else:
			if self.new_collection_name not in bpy.data.collections:
				bpy.data.collections.new(self.new_collection_name)
				bpy.context.collection.children.link(bpy.data.collections[self.new_collection_name])
			if self.mode != 'LINK':
				for o in self.imported_objects:
					self.unlink_object_from_collection(o, bpy.context.collection)
					self.link_object_to_collection(o, bpy.data.collections[self.new_collection_name])
     
	def create_and_link_collection_hierarchy(self):
		self.log.info("Create Collection Hierarchy")
		for c, p in self.parent_collections.items():
			if c not in self.objects_collection_list:
				continue

			for i, pp in enumerate(p):
				if pp not in self.objects_collection_list:
					continue

				if i == 0:
					self.create_collection(c)

				if pp == self.root_collection_name:
					if self.export_in_new_collection:
						self.link_collection_to_collection(bpy.data.collections[c], bpy.data.collections[self.new_collection_name])
					else:
						self.link_collection_to_collection(bpy.data.collections[c], bpy.context.scene.collection)
				else:
					if pp not in bpy.data.collections:
						self.create_collection(pp)

					if c not in bpy.data.collections[pp].children:
						self.link_collection_to_collection(bpy.data.collections[c], bpy.data.collections[pp])
		
		# Link Object to collections
		self.log.info("Link Objects to Collection")
		for o in self.selected_objects:
			for c in self.selected_objects_parent_collection[o]:
				if c in self.parent_collections.keys():
					self.link_object_to_collection(bpy.data.objects[o], bpy.data.collections[c])
			self.unlink_object_from_collection(bpy.data.objects[o], self.root_collection)
    
	def link_dependencies_in_dedicated_collection(self):
		if self.mode != "LINK":
			if len(self.selected_objects) < len(bpy.data.objects) - self.initial_count:
				self.create_collection('Dependencies')
				self.link_collection_to_collection(bpy.data.collections["Dependencies"], self.root_collection)

				for o in self.imported_objects:
					if o.name in self.selected_objects:
						continue
					if o.name not in self.root_collection.objects:
						continue

					self.move_object_to_collection(bpy.data.objects[o.name], self.root_collection, bpy.data.collections["Dependencies"])
    
	def link_dependencies_in_their_respective_collection(self):
		if len(self.selected_objects) < len(bpy.data.objects) - self.initial_count:
			for o in self.imported_objects:
				if o.name in self.selected_objects:
					continue

				for obj, h in self.all_objects_collection_hierarchy.items():
					if obj != o.name:
						continue
					if obj not in self.root_collection.objects:
						continue

					for hh in h:
						hierarchy = list(reversed(hh))
						for i, c in enumerate(hierarchy):
							if i == 0:
								if c not in bpy.data.collections:
									self.create_collection(c)
									self.link_collection_to_collection(bpy.data.collections[c], self.root_collection)

								if c not in self.root_collection.children:
									self.link_collection_to_collection(bpy.data.collections[c], self.root_collection)
							else:
								if c not in bpy.data.collections:
									self.create_collection(c)

								if c not in bpy.data.collections[hierarchy[i-1]].children:
									self.link_collection_to_collection(bpy.data.collections[c], bpy.data.collections[hierarchy[i-1]])
						else:
							self.move_object_to_collection(bpy.data.objects[o.name], self.root_collection, bpy.data.collections[hierarchy[len(hierarchy)-1]])
	
	def create_collection(self, collection_name):
		self.log.info(f'Create new collection : "{collection_name}"')
		bpy.data.collections.new(collection_name)
  
	def link_object_to_collection(self, object, collection):
		self.log.info(
			f'Link object "{object.name}" to collection "{collection.name}"')
		collection.objects.link(object)
	
	def unlink_object_from_collection(self, object, collection):
		self.log.info(
			f'Unlink object "{object.name}" from collection "{collection.name}"')
		collection.objects.unlink(object)
	
	def move_object_to_collection(self, object, from_collection, to_collection):
		self.log.info(f'Move object "{object.name}" from collection "{from_collection.name}" to {to_collection.name}')
		from_collection.objects.unlink(object)
		to_collection.objects.link(object)
  
	def link_collection_to_collection(self, child_collection, parent_collection):
		self.log.info(f'Link Collection "{child_collection.name}" to collection "{parent_collection.name}"')
		parent_collection.children.link(child_collection)
	
	def unlink_collection_from_collection(self, child_collection, parent_collection):
		self.log.info(f'Unink Collection "{child_collection.name}" from collection "{parent_collection.name}"')
		parent_collection.children.unlink(child_collection)
  
	def clean_scene(self):
		self.log.info("Cleaning Scene")
		for d in dir(bpy.data):
			if d in ['screens', 'workspaces']:
				continue
			p = getattr(bpy.data, d)
			if isinstance(p, bpy.types.bpy_prop_collection):
				if 'remove' in dir(p):
					for e in p:
						if d == 'scenes':
							if e.name == bpy.context.scene.name:
								continue
						p.remove(e)
  
if __name__ == "__main__":
	print('-- RUNNING IMPORT COMMAND --')
	IC = ImportCommand(sys.argv, debug=True)
	IC.import_command()
