import sys, getopt, bpy, os, bpy_extras, bpy_types
import re

IMPORT_COLLECTION_NAME = 'TILA_IMPORT_COLLECTION'
DEPENDENCIES_COLLECTION_NAME = 'Dependencies'

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


class CollectionManager(object):

	collection_objects_correspondance = {}

	def __init__(self, debug=False):
		self.log = Logger(addon_name='CollectionManager', debug_mode=debug)
		self.collection_list = []

		# init collection_name
		for i, c in enumerate(bpy.data.collections):
			bpy_extras.io_utils.unique_name(i, c.name, self.collection_objects_correspondance)

	def add_collection(self, name):
		if name in bpy.data.collections:
			bpy_extras.io_utils.unique_name(bpy.data.collections[name], name, self.collection_objects_correspondance, clean_func=unique_name_clean_func)
		coll = Collection(name)
		if coll not in self.collection_list:
			self.collection_list.append(coll)
		return coll
	
	def get_collection_by_incoming_name(self, name):
		c = [col for col in self.collection_list if col.incoming_name == name]
		if len(c):
			return c[0]

		return None

	def get_collection_by_local_name(self, name):
		c = [col for col in self.collection_list if col.name == name]
		if len(c):
			return c[0]

		return None

	def conform_collection(self, collection):
		if isinstance(collection, Collection):
			return collection
		elif isinstance(collection, bpy_types.Collection):
			return Collection(collection.name)
		else:
			raise ValueError
	
	# Linking and Unlinking Methods
	def create_collection(self, collection_name):
		coll = self.add_collection(collection_name)
		self.log.info(f'Create new collection : "{coll.name}"')
		bpy.data.collections.new(coll.name)
		return coll

	def link_object_to_collection(self, object, collection):
		collection = self.conform_collection(collection).collection
		self.log.info(f'Link object "{object.name}" to collection "{collection.name}"')
		collection.objects.link(object)

	def unlink_object_from_collection(self, object, collection):
		collection = self.conform_collection(collection).collection
		self.log.info(f'Unlink object "{object.name}" from collection "{collection.name}"')
		collection.objects.unlink(object)

	def move_object_to_collection(self, object, from_collection, to_collection):
		from_collection = self.conform_collection(from_collection).collection
		to_collection = self.conform_collection(to_collection).collection
		self.log.info(f'Move object "{object.name}" from collection "{from_collection.name}" to "{to_collection.name}"')
		from_collection.objects.unlink(object)
		to_collection.objects.link(object)

	def link_collection_to_collection(self, child_collection, parent_collection):
		child_collection = self.conform_collection(child_collection).collection
		parent_collection = self.conform_collection(parent_collection).collection
		self.log.info(f'Link Collection "{child_collection.name}" to collection "{parent_collection.name}"')
		parent_collection.children.link(child_collection)

	def unlink_collection_from_collection(self, child_collection, parent_collection):
		child_collection = self.conform_collection(child_collection).collection
		parent_collection = self.conform_collection(parent_collection).collection
		self.log.info(f'Unink Collection "{child_collection.name}" from collection "{parent_collection.name}"')
		parent_collection.children.unlink(child_collection)

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


class Collection(CollectionManager):
	def __init__(self, string, debug=False):
		super(Collection, self).__init__(debug)
		self._string = {'incoming':string, 'local':string}
		self.log = Logger(addon_name='Collection', debug_mode=debug)

	@property
	def incoming_name(self):
		return self._string['incoming']
	
	@property
	def name(self):
		self.fix_local_collection_name()
		return self._string['local']

	@name.setter
	def name(self, value):
		self._string['local'] = value
	
	@property
	def children(self):
		return bpy.data.collections[self.name].children if self.name != "Scene Collection" else bpy.context.scene.collection.children

	@property
	def objects(self):
		return bpy.data.collections[self.name].objects if self.name != "Scene Collection" else bpy.context.scene.collection.objects

	@property
	def collection(self):
		if self.name == "Scene Collection":
			return bpy.context.scene.collection
		elif self.name not in bpy.data.collections:
			self.log.error(f'"{self.name}" collection not in current scene')
			raise ValueError
		else:
			return bpy.data.collections[self.name]

	def fix_local_collection_name(self):
		if self.incoming_name in bpy.data.collections:
			if bpy.data.collections[self.incoming_name] in self.collection_objects_correspondance.keys():
				self._string['local'] = self.collection_objects_correspondance[bpy.data.collections[self.incoming_name]]

	

class ImportCommand():
	def __init__(self, argv, debug=False):
		self.parse_argsv(argv[argv.index("--") + 1:])
		self.debug = debug
		self.log = Logger(addon_name='Import Command', debug_mode=debug)
		self._imported_objects = None
		self._valid_collections = None
		self.cm = CollectionManager(debug)
		
	# Properties
	@property
	def imported_objects(self):
		if self._imported_objects is None:
			if os.path.exists(self.source_file) :
				self._imported_objects = {o.name:o for o in bpy.data.objects if o.library != None and os.path.normpath(o.library.filepath) == os.path.normpath(self.source_file)}
		return self._imported_objects
	
	# need to convert to argparse instead of getopt
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
		if self.export_to_clean_file and self.override == "OVERRIDE":
			self.clean_scene()

		self.initial_count = len(bpy.data.objects)
		self.initial_objects = [o.name for o in bpy.data.objects]

		if self.source == 'CURRENT_SCENE':
			self.import_scene()
		elif self.source == 'SELECTED_OBJECTS':
			self.import_objects()

		# Pack Files
		if self.pack_external_data and self.mode == 'APPEND':
			try:
				bpy.ops.file.pack_all()

			except RuntimeError as e:
				self.log.error("Cannot pack data or data does not exist on drive.  " + e)

		# Save File
		bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=self.destination)

	def import_scene(self):
		self.log.info(f"Importing Scene {self.scene_name}")

		filepath = os.path.join(self.source_file, 'Scene', self.scene_name)
		directory = os.path.join(self.source_file, 'Scene')

		# Import Scene
		bpy.ops.wm.append(	filepath=filepath,
							directory=directory,
						  	filename=self.scene_name,
							link=self.mode == 'LINK'
					 	 )

		if self.export_to_clean_file and self.override == "OVERRIDE" and self.mode == "APPEND":
			bpy.data.scenes.remove(bpy.data.scenes[bpy.context.scene.name])

	def import_objects(self):
		self.log.info("Importing Objects")

		self.scene_root_collection = bpy.context.scene.collection

		# Create Import Collection and set active
		self.import_collection = self.cm.create_collection(IMPORT_COLLECTION_NAME)
		self.cm.link_collection_to_collection(self.import_collection, bpy.context.scene.collection)
   
		self.cm.set_collection_active(IMPORT_COLLECTION_NAME)

		# Link object from source file
		self.link_objects(self.source_file, self.selected_objects, bpy.data.collections[IMPORT_COLLECTION_NAME])

		self.cm.set_collection_active(self.scene_root_collection.name)

		# Create New Collection and Link all imported object in it
		if self.export_in_new_collection:
			self.create_and_link_to_new_collection()
		# Move imported Objects to root collection
		else:
			for o in self.imported_objects.values():
				self.cm.move_object_to_collection(o, self.import_collection, bpy.context.scene.collection)
			self.root_collection = self.scene_root_collection
  
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

	# Main Flow Methods
	def create_and_link_to_new_collection(self):
		if self.new_collection_name == '':
			self.log.warning(f'New collection name is empty, skipping root collection creation.')
			self.report({'ERROR'}, 'Export As Blend : New collection name is empty, skipping root collection creation.')
			self.export_in_new_collection = False
		else:
			self.log.info(f'Creating "{self.new_collection_name}" new collection and move imported files to it')
			self.root_collection = self.cm.create_collection(self.new_collection_name)
			self.cm.link_collection_to_collection(bpy.data.collections[self.new_collection_name], self.scene_root_collection)
			if self.mode != 'LINK':
				for o in self.imported_objects.values():
					self.cm.unlink_object_from_collection(o, self.import_collection)
					self.cm.link_object_to_collection(o, self.root_collection)

	def create_and_link_collection_hierarchy(self):
		self.log.info("Create Collection Hierarchy")
		tip_coll = None
		for c, p in self.parent_collections.items():
			c = Collection(c, self.debug)
			if c.incoming_name not in self.objects_collection_list:
				continue
			
			new_coll = None
			for i, pp in enumerate(p):
				pp = Collection(pp, self.debug)
				if pp.incoming_name not in self.objects_collection_list:
					continue
 
				if i == 0:
					tip_coll = self.cm.create_collection(c.name)

				if pp.incoming_name == self.root_collection_name:
					if self.export_in_new_collection:
						self.cm.link_collection_to_collection(tip_coll, self.root_collection)
				else:
					if pp.name not in bpy.data.collections:
						new_coll = self.cm.create_collection(pp.name)

					if new_coll is None:
						new_coll = pp
						
					if c.name not in new_coll.children:
						self.cm.link_collection_to_collection(tip_coll, new_coll)
		
		# Link Object to collections
		self.log.info("Link Objects to Collection")
		for o in self.selected_objects:
			for c in self.selected_objects_parent_collection[o]:
				if c in self.parent_collections.keys():
					c = Collection(c, self.debug)
					self.cm.link_object_to_collection(self.imported_objects[o], c)
			self.cm.unlink_object_from_collection(self.imported_objects[o], self.root_collection)
	
	def link_dependencies_in_dedicated_collection(self):
		if self.mode != "LINK":
			self.log.info(f'Link Dependencies in "{DEPENDENCIES_COLLECTION_NAME}" collection')
			if len(self.selected_objects) < len(bpy.data.objects) - self.initial_count:
				dependency_collection = self.cm.create_collection(DEPENDENCIES_COLLECTION_NAME)
				self.cm.link_collection_to_collection(dependency_collection, self.root_collection)

				for o in self.imported_objects.keys():
					if o in self.selected_objects:
						continue
					if o not in self.root_collection.objects:
						continue

					self.cm.move_object_to_collection(self.imported_objects[o], self.root_collection, dependency_collection)
	
	def link_dependencies_in_their_respective_collection(self):
		self.log.info('Link Dependencies to their respective collection')
		if len(self.selected_objects) < len(bpy.data.objects) - self.initial_count:
			for o in self.imported_objects.keys():
				if o in self.selected_objects:
					continue

				self.log.info(f'Linking Dependency : {o}')
	
				for obj, h in self.all_objects_collection_hierarchy.items():
					if obj != o:
						continue
					if obj not in self.root_collection.objects:
						continue
					for hh in h:
						hierarchy = list(reversed(hh))
						for i, c in enumerate(hierarchy):
							c = self.cm.add_collection(c)
							if i == 0:
								if c.name not in bpy.data.collections:
									self.cm.create_collection(c.name)
									self.cm.link_collection_to_collection(c, self.root_collection)

								if c.name not in self.root_collection.children:
									self.cm.link_collection_to_collection(c, self.root_collection)
							else:
								if c.name not in bpy.data.collections:
									self.cm.create_collection(c.name)
		 
								parent_coll = self.cm.add_collection(hierarchy[i-1])
								if c.name not in parent_coll.children:
									self.cm.link_collection_to_collection(c, parent_coll)
						else:
							parent_coll = self.cm.add_collection(hierarchy[len(hierarchy)-1])
							self.cm.move_object_to_collection(self.imported_objects[o], self.root_collection, parent_coll)
	
	# Helper Methods
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

	def link_objects(self, blend_file, object_names, collection):
		self.log.info(f'Linking objects in target file {blend_file}')
		def library_link_all(data_blocks, libpath, collection):
			for x in data_blocks:
				if x.library is not None:
					if os.path.normpath(libpath) == os.path.normpath(x.library.filepath):
						self.log.info(f"Importing : {x}")
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
