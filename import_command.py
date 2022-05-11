import sys, getopt, bpy, os, bpy_extras
import re, subprocess

IMPORT_COLLECTION_NAME = 'TILA_IMPORT_COLLECTION'

class Logger(object):
	def __init__(self, addon_name='ROOT', debug_mode=False):
		self.addon_name = addon_name
		self.debug_mode = debug_mode

	def info(self, message):
		self.print_message(message, 'INFO')

	def debug(self, message):
		self.print_message(message, 'DEBUG')

	def warning(self, message):
		self.print_message(message, 'WARNING')

	def error(self, message):
		self.print_message(message, 'ERROR')

	def print_message(self, message, mode):
		if self.debug_mode:
			print(f'{self.addon_name} : {mode} : {message}')
  
class ImportCommand():
	def __init__(self, argv, debug=False):
		self.parse_argsv(argv[argv.index("--") + 1:])
		self.debug = debug
		self.log = Logger(addon_name='Import Command', debug_mode=debug)
		self._imported_objects = None
		self._valid_collections = None
		self.collection_names = {}
		for i,c in enumerate(bpy.data.collections):
			bpy_extras.io_utils.unique_name(i, c.name, self.collection_names)
		
	# Properties
	@property
	def imported_objects(self):
		if self._imported_objects is None:
			if os.path.exists(self.source_file) :
				self._imported_objects = {o.name:o for o in bpy.data.objects if o.library != None and os.path.normpath(o.library.filepath) == os.path.normpath(self.source_file)}
		return self._imported_objects
	
	@property
	def imported_collections(self):
		pass

# argparse
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

		self.scene_root_collection = bpy.context.scene.collection

		# Create Import Collection and set active
		self.create_collection(IMPORT_COLLECTION_NAME)
		self.link_collection_to_collection(bpy.data.collections[IMPORT_COLLECTION_NAME], bpy.context.scene.collection)
		self.import_collection_name = IMPORT_COLLECTION_NAME
   
		self.set_collection_active(IMPORT_COLLECTION_NAME)
   
		self.link_objects(self.source_file, self.selected_objects, bpy.data.collections[IMPORT_COLLECTION_NAME])

		for o in self.imported_objects.keys():
			self.log.info(f"Importing : {o}")
    
  		# Register imported_objects
		self.log.info("Move imported files in the temporary import collection")
		self.set_collection_active(self.scene_root_collection.name)

		# Create New Collection and Link all imported object in it
		if self.export_in_new_collection:
			self.create_and_link_to_new_collection()
		# Move imported Objects to root collection
		else:
			for o in self.imported_objects.values():
				self.move_object_to_collection(o, bpy.data.collections[self.import_collection_name], bpy.context.scene.collection)
		
		# Set root_collection
		condition = self.export_in_new_collection and self.new_collection_name in bpy.data.collections
		self.root_collection = bpy.data.collections[self.new_collection_name] if condition else bpy.context.collection
  
		# Create Collection Hierarchy
		if self.create_collection_hierarchy:
			self.create_and_link_collection_hierarchy()
  
		if self.dependencies_in_dedicated_collection:
			self.link_dependencies_in_dedicated_collection()
		elif not self.dependencies_in_dedicated_collection and self.create_collection_hierarchy:
			self.link_dependencies_in_their_respective_collection()
  
		# Remove Import Collection and make local if needed
		bpy.data.collections.remove(bpy.data.collections[IMPORT_COLLECTION_NAME])
		if self.mode == 'APPEND':
			self.make_imported_objects_local()

		# Pack Files
		if self.pack_external_data and self.mode == 'APPEND':
			try:
				bpy.ops.file.pack_all()
	
			except RuntimeError as e:
				self.log.error("Cannot pack data or data does not exist on drive.  " + e)
	
		# Save File
		bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=self.destination)

	
	# Main Flow Methods
	def create_and_link_to_new_collection(self):
		if self.new_collection_name == '':
			self.log.warning(f'New collection name is empty, skipping root collection creation.')
			self.report({'ERROR'}, 'Export As Blend : New collection name is empty, skipping root collection creation.')
			self.export_in_new_collection = False
		else:
			self.log.info(f'Creating "{self.new_collection_name}" new collection and move imported files to it')
			self.create_collection(self.new_collection_name)
			self.link_collection_to_collection(bpy.data.collections[self.new_collection_name], self.scene_root_collection)
			if self.mode != 'LINK':
				for o in self.imported_objects.values():
					self.unlink_object_from_collection(o, bpy.data.collections[self.import_collection_name])
					self.link_object_to_collection(o, bpy.data.collections[self.new_collection_name])

	def create_and_link_collection_hierarchy(self):
		self.log.info("Create Collection Hierarchy")
		tip_coll = None
		for c, p in self.parent_collections.items():
			if c not in self.objects_collection_list:
				continue

			new_coll = None
			for i, pp in enumerate(p):
				if pp not in self.objects_collection_list:
					continue
 
				if i == 0:
					tip_coll = self.create_collection(c)

				if pp == self.root_collection_name:
					if self.export_in_new_collection:
						self.link_collection_to_collection(tip_coll, bpy.data.collections[self.new_collection_name])
				else:
					pp = self.get_valid_collection_name(pp)
					if pp not in bpy.data.collections:
						new_coll = self.create_collection(pp)
						pp = self.get_valid_collection_name(pp)
					else:
						new_coll = bpy.data.collections[pp]

					if c not in new_coll.children:
						self.link_collection_to_collection(tip_coll, new_coll)
		
		# Link Object to collections
		self.log.info("Link Objects to Collection")
		for o in self.selected_objects:
			for c in self.selected_objects_parent_collection[o]:
				if c in self.parent_collections.keys():
					self.link_object_to_collection(self.imported_objects[o], bpy.data.collections[c])
			self.unlink_object_from_collection(self.imported_objects[o], self.root_collection)
	
	def link_dependencies_in_dedicated_collection(self):
		if self.mode != "LINK":
			self.log.info('Link Dependencies in "Dependencies" collection')
			if len(self.selected_objects) < len(bpy.data.objects) - self.initial_count:
				self.create_collection('Dependencies')
				self.link_collection_to_collection(bpy.data.collections["Dependencies"], self.root_collection)

				for o in self.imported_objects.keys():
					if o in self.selected_objects:
						continue
					if o not in self.root_collection.objects:
						continue

					self.move_object_to_collection(self.imported_objects[o], self.root_collection, bpy.data.collections["Dependencies"])
	
	def link_dependencies_in_their_respective_collection(self):
		self.log.info('Link Dependencies to their respective collection')
		if len(self.selected_objects) < len(bpy.data.objects) - self.initial_count:
			for o in self.imported_objects.keys():
				if o in self.selected_objects:
					continue

				for obj, h in self.all_objects_collection_hierarchy.items():
					if obj != o:
						continue
					if obj not in self.root_collection.objects:
						continue
					print(o)
					for hh in h:
						hierarchy = list(reversed(hh))
						for i, c in enumerate(hierarchy):
							c = self.get_valid_collection_name(c)
							if i == 0:
								if c not in bpy.data.collections:
									self.create_collection(c)
									c = self.get_valid_collection_name(c)
									self.link_collection_to_collection(bpy.data.collections[c], self.root_collection)

								if c not in self.root_collection.children:
									self.link_collection_to_collection(bpy.data.collections[c], self.root_collection)
							else:
								if c not in bpy.data.collections:
									self.create_collection(c)
		 
								c = self.get_valid_collection_name(c)
								parent_coll = self.get_valid_collection_name(hierarchy[i-1])
								if c not in bpy.data.collections[parent_coll].children:
									self.link_collection_to_collection(bpy.data.collections[c], bpy.data.collections[parent_coll])
						else:
							parent_coll = self.get_valid_collection_name(hierarchy[len(hierarchy)-1])
							self.move_object_to_collection(self.imported_objects[o], self.root_collection, bpy.data.collections[parent_coll])
	
 
	# Linking and Unlinking Methods
	def create_collection(self, collection_name):
		# automaticly use an incremented collection name if the given name already exists
		if collection_name in bpy.data.collections:
			bpy_extras.io_utils.unique_name(bpy.data.collections[collection_name], collection_name, self.collection_names, clean_func=unique_name_clean_func)
			# self.valid_collections[collection_name] = bpy.data.collections[collection_name]
			collection_name = self.collection_names[bpy.data.collections[collection_name]]
		self.log.info(f'Create new collection : "{collection_name}"')
		return bpy.data.collections.new(collection_name)
  
	def link_object_to_collection(self, object, collection):
		if collection in self.collection_names.keys():
			collection = bpy.data.collections[self.collection_names[collection]]
		self.log.info(
			f'Link object "{object.name}" to collection "{collection.name}"')
		collection.objects.link(object)
	
	def unlink_object_from_collection(self, object, collection):
		if collection in self.collection_names.keys():
			collection = bpy.data.collections[self.collection_names[collection]]
		self.log.info(
			f'Unlink object "{object.name}" from collection "{collection.name}"')
		collection.objects.unlink(object)
	
	def move_object_to_collection(self, object, from_collection, to_collection):
		if from_collection in self.collection_names.keys():
			from_collection = bpy.data.collections[self.collection_names[from_collection]]
		if to_collection in self.collection_names.keys():
			to_collection = bpy.data.collections[self.collection_names[to_collection]]
		self.log.info(f'Move object "{object.name}" from collection "{from_collection.name}" to "{to_collection.name}"')
		from_collection.objects.unlink(object)
		to_collection.objects.link(object)
  
	def link_collection_to_collection(self, child_collection, parent_collection):
		if child_collection in self.collection_names.keys():
			child_collection = bpy.data.collections[self.collection_names[child_collection]]
		if parent_collection in self.collection_names.keys():
			parent_collection = bpy.data.collections[self.collection_names[parent_collection]]
		self.log.info(f'Link Collection "{child_collection.name}" to collection "{parent_collection.name}"')
		parent_collection.children.link(child_collection)
	
	def unlink_collection_from_collection(self, child_collection, parent_collection):
		if child_collection in self.collection_names.keys():
			child_collection = bpy.data.collections[self.collection_names[child_collection]]
		if parent_collection in self.collection_names.keys():
			parent_collection = bpy.data.collections[self.collection_names[parent_collection]]

		self.log.info(f'Unink Collection "{child_collection.name}" from collection "{parent_collection.name}"')
		parent_collection.children.unlink(child_collection)
	
 
	# Helper Methods
	def get_layer_collection_by_name(self, layer_collection, collection_name):
		found = None
		if (layer_collection.name == collection_name):
			return layer_collection
		for layer in layer_collection.children:
			found = self.get_layer_collection_by_name(layer, collection_name)
			if found:
				return found

	def set_collection_active(self, collection_name):
		layer_collection = bpy.context.view_layer.layer_collection
		layerColl = self.get_layer_collection_by_name(layer_collection, collection_name)
		bpy.context.view_layer.active_layer_collection = layerColl
  
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
 
	def get_valid_collection_name(self, original_name):
		if original_name in bpy.data.collections:
			if bpy.data.collections[original_name] in self.collection_names.keys():
				return self.collection_names[bpy.data.collections[original_name]]
			else:
				return original_name
		else:
			return original_name

	def link_objects(self, blend_file, object_names, collection):
		self.log.info(f'Linking objects in target file {blend_file}')
		def library_link_all(data_blocks, libpath, collection):
			for x in data_blocks:
				if x.library is not None:
					if os.path.normpath(libpath) == os.path.normpath(x.library.filepath):
						collection.objects.link(x)
      
		# Link objects
		with bpy.data.libraries.load(blend_file, link=True) as (data_from, data_to):
			for name in data_from.objects:
				if name in object_names:
					data_to.objects.append(name)
		
		library_link_all(bpy.data.objects, blend_file, collection)
  
	def make_imported_objects_local(self):
		for o in self.imported_objects.values():
			o.make_local()
			if o.data is None:
				continue
			
			o.data.make_local()
				
 
def unique_name_clean_func(name):
	word_pattern = re.compile(r'(\.[0-9]{3})$', re.IGNORECASE)
	name_iter = word_pattern.finditer(name)
	name_iter_match = [w.group(1) for w in name_iter]

	if len(name_iter_match) and name_iter_match[0] is not None:
		return name.replace(name_iter_match[0], '')
	else:
		return name

if __name__ == "__main__":
	print('-- RUNNING IMPORT COMMAND --')
	IC = ImportCommand(sys.argv, debug=True)
	IC.import_command()
