from dataclasses import dataclass
import sys
import bpy
import os
import bpy_extras
import bpy_types
import argparse
import re

IMPORT_COLLECTION_NAME = 'TILA_IMPORT_COLLECTION'
DEPENDENCIES_COLLECTION_NAME = 'Dependencies'


class Logger(object):
	def __init__(self, addon_name='ROOT', print=False):
		self.addon_name = addon_name
		self.print = print

	def info(self, message):
		self.print_message(message, 'INFO')

	def debug(self, message):
		self.print_message(message, 'DEBUG')

	def warning(self, message):
		self.print_message(message, 'WARNING')

	def error(self, message):
		self.print_message(message, 'ERROR')

	def print_message(self, message, mode):
		if self.print:
			print(f'{self.addon_name} : {mode} : {message}')


class Manager:
	element_correspondance = {}
	def __init__(self, name, bpy_data, element_class, print_message=False):
		self.log = Logger(addon_name=name, print=print_message)
		self.element_list = []
		self.bpy_data = bpy_data
		self.element_class = element_class
		self.element_correspondance = {}

		# init incoming name
		for i, e in enumerate(bpy_data):
			bpy_extras.io_utils.unique_name(i, e.name, self.element_correspondance)
	
	@property
	def bpy_type(self):
		if len(self.bpy_data):
			return type(self.bpy_data[0])
		else:
			try:
				ex = ValueError()
				ex.strerror = f"No element in  {type(self.bpy_data)}"
				raise ex
			except ValueError as e:
				print(f'Value Error : {e.strerror}')

	def get_element_by_incoming_name(self, name):
		e = [elem for elem in self.element_list if elem.incoming_name == name]
		if len(e):
			return e[0]

		return None

	def get_element_by_local_name(self, name):
		e = [elem for elem in self.element_list if elem.name == name]
		if len(e):
			return e[0]

		return None

	def conform_element(self, element):
		if isinstance(element, self.element_class):
			return element
		elif isinstance(element, self.bpy_type):
			return self.element_class(manager=self, string=element.name)
		else:
			try:
				ex = ValueError()
				ex.strerror = f"Unrecognise type for Collection {type(element)}"
				raise ex
			except ValueError as e:
				print(f'Value Error : {e.strerror}')

	def add_element(self, name):
		if name in self.bpy_data:
			bpy_extras.io_utils.unique_name(
				self.bpy_data[name], name, self.element_correspondance, clean_func=unique_name_clean_func)
		elem = self.element_class(manager = self, string = name)
		if elem not in self.element_list:
			self.element_list.append(elem)
		return elem


class ObjectManager(Manager):
	def __init__(self, bpy_data, element_class, print_message=False):
		super(ObjectManager, self).__init__(
			'Object Manager', bpy_data, element_class, print_message)

	def parent(self, parent, child, keep_transform=False):
		self.log.info(f'Parent "{child.name}" object to "{parent.name}" object')
		child.parent = parent
		if keep_transform:
			child.matrix_parent_inverse = parent.matrix_world.inverted()


class CollectionManager(Manager):
	def __init__(self, bpy_data, element_class, print_message=False):
		super(CollectionManager, self).__init__('Collection Manager', bpy_data, element_class, print_message)
	
	# Linking and Unlinking Methods
	def create_collection(self, collection_name):
		coll = self.add_element(collection_name)
		self.log.info(f'Create new collection : "{coll.name}"')
		self.bpy_data.new(coll.name)
		return coll

	def link_object_to_collection(self, object, collection):
		collection = self.conform_element(collection).collection
		self.log.info(f'Link object "{object.name}" to collection "{collection.name}"')
		collection.objects.link(object)

	def unlink_object_from_collection(self, object, collection):
		collection = self.conform_element(collection).collection
		self.log.info(f'Unlink object "{object.name}" from collection "{collection.name}"')
		collection.objects.unlink(object)

	def move_object_to_collection(self, object, from_collection, to_collection):
		from_collection = self.conform_element(from_collection).collection
		to_collection = self.conform_element(to_collection).collection
		self.log.info(f'Move object "{object.name}" from collection "{from_collection.name}" to "{to_collection.name}"')
		from_collection.objects.unlink(object)
		to_collection.objects.link(object)

	def link_collection_to_collection(self, child_collection, parent_collection):
		child_collection = self.conform_element(child_collection).collection
		parent_collection = self.conform_element(parent_collection).collection
		self.log.info(f'Link Collection "{child_collection.name}" to collection "{parent_collection.name}"')
		parent_collection.children.link(child_collection)

	def unlink_collection_from_collection(self, child_collection, parent_collection):
		child_collection = self.conform_element(child_collection).collection
		parent_collection = self.conform_element(parent_collection).collection
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

class Element:
	def __init__(self, manager, string):
		self._string = {'incoming': string, 'local': string}
		self.manager = manager

	@property
	def incoming_name(self):
		return self._string['incoming']

	@property
	def name(self):
		self.fix_local_element_name()
		return self._string['local']

	@name.setter
	def name(self, value):
		self._string['local'] = value

	def fix_local_element_name(self):
		if self.incoming_name in self.manager.bpy_data:
			if self.manager.bpy_data[self.incoming_name] in self.manager.element_correspondance.keys():
				self._string['local'] = self.manager.element_correspondance[self.manager.bpy_data[self.incoming_name]]


class Collection(Element):
	def __init__(self, manager, string, print_message=False):
		super(Collection, self).__init__(manager, string)
		self.log = Logger(addon_name='Collection', print=print_message)

	@property
	def children(self):
		return self.manager.bpy_data[self.name].children if self.name != "Scene Collection" else bpy.context.scene.collection.children

	@property
	def objects(self):
		return self.manager.bpy_data[self.name].objects if self.name != "Scene Collection" else bpy.context.scene.collection.objects

	@property
	def collection(self):
		if self.name == "Scene Collection":
			return bpy.context.scene.collection
		elif self.name not in self.manager.bpy_data:
			self.log.error(f'"{self.name}" collection not in current file')
			try:
				ex = ValueError()
				ex.strerror = f'Name "{self.name}" not in Collections'
				raise ex
			except ValueError as e:
				print(f'Value Error : {e.strerror}')
		else:
			return self.manager.bpy_data[self.name]


class Object(Element):
	def __init__(self, manager, string, print_message=False):
		super(Object, self).__init__(manager, string)
		self.log = Logger(addon_name='Object', print=print_message)

	@property
	def object(self):
		if self.name not in self.manager.bpy_data:
			self.log.error(f'"{self.name}" Object not in current file')
			try:
				ex = ValueError()
				ex.strerror = f'Name "{self.name}" not in Objects'
				raise ex
			except ValueError as e:
				print(f'Value Error : {e.strerror}')
		else:
			return self.manager.bpy_data[self.name]


class ImportCommand():
	def __init__(self, argv):
		self.parse_argsv(argv[argv.index("--") + 1:])
		self.log = Logger(addon_name='Import Command', print=self.print_debug)
		self.init_source_lists()
		self._imported_objects = None
		self._valid_collections = None
		self.cm = CollectionManager(bpy.data.collections, Collection, self.print_debug)
		self.om = ObjectManager(bpy.data.objects, Object, self.print_debug)

	# Properties
	@property
	def imported_objects(self):
		if self._imported_objects is None:
			if os.path.exists(self.source_file) :
				self._imported_objects = {o.name:o for o in bpy.data.objects if o.library != None and os.path.normpath(o.library.filepath) == os.path.normpath(self.source_file)}
		return self._imported_objects

	@property
	def have_dependencies(self):
		return len(self.source_object_list) < len(bpy.context.scene.objects) - self.initial_count

	def parse_argsv(self, argv):
		parser = argparse.ArgumentParser(description='This command allow you to import objects or scene to a blend file and save it once done.')

		file_group = parser.add_argument_group('File path')
		file_group.add_argument('-f', '--source_file', nargs='?',
							help='Path to blend file to export data from',
							required=True)
		file_group.add_argument('-d', '--destination_file', nargs='?',
							help='Path to blend file you want the export data to',
							required=True)

		import_option_group = parser.add_argument_group('Import Options')
		import_option_group.add_argument('-s', '--source_data', choices=['OBJECTS', 'SCENE'],
							default='OBJECTS',
							help='Defines what data will be exported',
							required=True)
		import_option_group.add_argument('-o', '--file_override', choices=['OVERRIDE', 'APPEND_LINK'],
							default='OVERRIDE',
							help='Determine if the file will be override or if the data will be appended or linked to destination file',
							required=True)
		import_option_group.add_argument('-t', '--target_scene',
								default='CURRENT_SCENE',
								help='Determine the scene you want the objects to be appended/linked to',
								required=False)
		import_option_group.add_argument('-m', '--export_mode', choices=['APPEND', 'LINK'],
							default='APPEND',
							help='Determine if the data is linked or appended from source file',
							required=True)
		import_option_group.add_argument('-X', '--export_to_clean_file', default=True,
							help='If enabled, data is imported in a clean file, otherwise it will be imported in the default startup file',
							required=True)
		import_option_group.add_argument('-p', '--pack_external_data', default=False,
					 		help='If enabled, all external data will be packed into blend file',
							required=True)
		import_option_group.add_argument('-C', '--export_object_children', default=False,
							help='if enabled, all listed object children will be exported',
							required=True)
		import_option_group.add_argument('-S', '--source_scene_name',
							help='The name of the scene from which export data from',
							required=True)
		import_option_group.add_argument('-O', '--source_object_list', nargs='+',
							help='List of objects to export',
							required=True)

		collection_hierarchy_group = parser.add_argument_group('Collection Hierarchy')
		collection_hierarchy_group.add_argument('-c', '--create_collection_hierarchy', default=True,
							help='If enabled, the collection hierarchy of each objects will be created',
							required=True)
		collection_hierarchy_group.add_argument('-N', '--export_in_new_collection', default=False,
							help='If enabled, all objects and dependencies will be placed in a new collection',
							required=True)
		collection_hierarchy_group.add_argument('-n', '--new_collection_name', default='Root Collection',
							help='The name of the new collection that will be created',
							required=True)
		collection_hierarchy_group.add_argument('-D', '--dependencies_in_dedicated_collection', default=False,
					  		help='If enabled, the dependencies of each objects will be placed in a "Dependencies" collection, otherwise they will be placed in ther respective collection if --create_collection_hierarchy is True or in root collection if False',
							required=True)
		
		debug_group = parser.add_argument_group('Collection Hierarchy')
		debug_group.add_argument('-P', '--print_debug', default=False,
										  help='Print debug message in console',
										  required=False)
		args = parser.parse_args(argv)
		self.source_file = args.source_file
		self.destination_file = args.destination_file
		self.source_data = args.source_data
		self.file_override = args.file_override
		self.target_scene = args.target_scene
		self.export_mode = args.export_mode
		self.export_to_clean_file = eval(args.export_to_clean_file)
		self.pack_external_data = eval(args.pack_external_data)
		self.export_object_children = eval(args.export_object_children)
		self.source_scene_name = args.source_scene_name
		self.source_object_list = args.source_object_list
		self.create_collection_hierarchy = eval(args.create_collection_hierarchy)
		self.export_in_new_collection = eval(args.export_in_new_collection)
		self.new_collection_name = args.new_collection_name
		self.dependencies_in_dedicated_collection = eval(args.dependencies_in_dedicated_collection)
		self.print_debug = eval(args.print_debug)
	
	def init_source_lists(self):
		# register previously loaded libraries
		self.previous_library_objects = {o.name: o for o in bpy.data.objects if o.library is not None and os.path.normpath(o.library.filepath) == os.path.normpath(self.source_file)}
		self.previous_library_collections = {c.name: c for c in bpy.data.collections if c.library is not None and os.path.normpath(c.library.filepath) == os.path.normpath(self.source_file)}
		self.previous_library_scenes = {s.name: s for s in bpy.data.scenes if s.library is not None and os.path.normpath(s.library.filepath) == os.path.normpath(self.source_file)}

		with bpy.data.libraries.load(self.source_file, link=True) as (data_from, data_to):
			for s in data_from.scenes:
				data_to.scenes.append(s)
			for c in data_from.collections:
				data_to.collections.append(c)
			for o in data_from.objects:
				data_to.objects.append(o)
		
		# register imported libraries data
		objects = {o.name:o for o in bpy.data.objects if o.library is not None and os.path.normpath(o.library.filepath) == os.path.normpath(self.source_file)}
		collections = {c.name:c for c in bpy.data.collections if c.library is not None and os.path.normpath(c.library.filepath) == os.path.normpath(self.source_file)}
		scenes = {s.name:s for s in bpy.data.scenes if s.library is not None and os.path.normpath(s.library.filepath) == os.path.normpath(self.source_file)}
		
		self.objects_children = {}
		object_to_process = self.source_object_list.copy()
		while len(object_to_process):
			o = object_to_process.pop()
			self.objects_children[o] = self.get_object_children(objects[o])
			if len(self.objects_children[o]):
				for c in self.objects_children[o]:
					if c not in object_to_process:
						object_to_process.append(c)
					if self.export_object_children and c not in self.source_object_list:
						self.source_object_list.append(c)
		if self.export_object_children:
			for c in self.objects_children.values():
				for cc in c:
					if cc not in objects.keys():
						o = bpy.data.objects[cc]
						if o.library is not None and os.path.normpath(o.library.filepath) == os.path.normpath(self.source_file):
							objects[cc] = o

		self.parent_collections = self.parent_lookup(scenes[self.source_scene_name].collection)

		self.selected_objects_parent_collection = {}
		for o in self.source_object_list:
			self.selected_objects_parent_collection[o] = [c.name for c in objects[o].users_collection]
			if o not in self.objects_children.keys():
				continue
			for c in self.objects_children[o]:
				self.selected_objects_parent_collection[c] = [cc.name for cc in objects[c].users_collection]
		
		self.root_collection_name = scenes[self.source_scene_name].collection.name

		self.collections_in_scene = [c.name for c in collections.values() if scenes[self.source_scene_name].user_of_id(c)]
		self.objects_collection_hierarchy = self.get_objects_collection_hierarchy([o for o in objects.values() if o.name in self.source_object_list], self.collections_in_scene, collections.values())

		self.objects_collection_list = [scenes[self.source_scene_name].collection.name]
		for c in self.objects_collection_hierarchy.values():
			for cc in c:
				if cc not in self.objects_collection_list:
					self.objects_collection_list.append(cc)

		self.all_objects_collection_hierarchy = {}
		for o in objects.values():
			hierarchies = []
			for c in o.users_collection:
				coll = []
				self.get_parent_collection_names(c, coll, collections.values())
				hierarchies.append(coll)
			self.all_objects_collection_hierarchy[o.name] = hierarchies

		self.imported_childs = []

		# remove objects and collections
		self.remove_source_library()
		
		self.log.info(f'source_file = {self.source_file}')
		self.log.info(f'destination_file = {self.destination_file}')
		self.log.info(f'source_data = {self.source_data}')
		self.log.info(f'file_override = {self.file_override}')
		self.log.info(f'export_mode = {self.export_mode}')
		self.log.info(f'export_to_clean_file = {self.export_to_clean_file}')
		self.log.info(f'pack_external_data = {self.pack_external_data}')
		self.log.info(f'source_scene_name = {self.source_scene_name}')
		self.log.info(f'source_object_list = {self.source_object_list}')
		self.log.info(f'export_object_children = {self.export_object_children}')
		self.log.info(f'create_collection_hierarchy = {self.create_collection_hierarchy}')
		self.log.info(f'export_in_new_collection = {self.export_in_new_collection}')
		self.log.info(f'new_collection_name = {self.new_collection_name}')
		self.log.info(f'dependencies_in_dedicated_collection = {self.dependencies_in_dedicated_collection}')
		self.log.info(f'print_debug = {self.print_debug}')


		self.log.info(f'collections_in_scene = {self.collections_in_scene}')
		self.log.info(f'parent_collections = {self.parent_collections}')
		self.log.info(f'selected_objects_parent_collection = {self.selected_objects_parent_collection}')
		self.log.info(f'root_collection_name = {self.root_collection_name}')
		self.log.info(f'objects_collection_list = {self.objects_collection_list}')
		self.log.info(f'objects_collection_hierarchy = {self.objects_collection_hierarchy}')
		self.log.info(f'all_objects_collection_hierarchy = {self.all_objects_collection_hierarchy}')
		self.log.info(f'objects_childen = {self.objects_children}')

	def import_command(self):
		if self.export_to_clean_file and self.file_override == "OVERRIDE":
			self.clean_file()

		self.initial_count = len(bpy.context.scene.objects)

		if self.source_data == 'SCENE':
			self.import_scene()
		elif self.source_data == 'OBJECTS':
			self.import_objects()

		# Pack Files
		if self.pack_external_data and self.export_mode == 'APPEND':
			try:
				bpy.ops.file.pack_all()

			except RuntimeError as e:
				self.log.error("Cannot pack data or data does not exist on drive.  " + e)

		# Save File
		bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=self.destination_file)

	def import_scene(self):
		self.log.info(f"Importing Scene {self.source_scene_name}")

		filepath = os.path.join(self.source_file, 'Scene', self.source_scene_name)
		directory = os.path.join(self.source_file, 'Scene')

		# Import Scene
		bpy.ops.wm.append(	filepath=filepath,
							directory=directory,
						  	filename=self.source_scene_name,
							link=self.export_mode == 'LINK'
					 	 )

		if self.export_to_clean_file and self.file_override == "OVERRIDE" and self.export_mode == "APPEND":
			bpy.data.scenes.remove(bpy.data.scenes[bpy.context.scene.name])

	def import_objects(self):
		if self.target_scene != 'CURRENT_SCENE':
			if self.target_scene not in bpy.data.scenes:
				self.log.error(f'The target scene "{self.target_scene}" doesn\'t exists in the file, the objects will be placed in the current scene')
			else:
				self.log.info(f'Switching to "{self.target_scene}" scene')
				bpy.context.window.scene = bpy.data.scenes[self.target_scene]
		self.log.info("Importing Objects")

		self.scene_root_collection = bpy.context.scene.collection

		# Create Import Collection and set active
		self.import_collection = self.cm.create_collection(IMPORT_COLLECTION_NAME)
		self.cm.link_collection_to_collection(self.import_collection, bpy.context.scene.collection)
   
		self.cm.set_collection_active(IMPORT_COLLECTION_NAME)

		# Link object from source file
		self.link_objects(self.source_file, self.source_object_list, bpy.data.collections[IMPORT_COLLECTION_NAME])

		self.cm.set_collection_active(self.scene_root_collection.name)

		# Create New Collection and Link all imported object in it
		if self.export_in_new_collection:
			self.create_and_link_to_new_collection()
		# Move imported Objects to root collection
		else:
			self.log.info('Move Objects to Scene Root Collection')
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

		if self.export_mode == 'APPEND':
			self.make_imported_objects_local()
			self.remove_source_library()

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
			for o in self.imported_objects.values():
				self.cm.unlink_object_from_collection(o, self.import_collection)
				self.cm.link_object_to_collection(o, self.root_collection)

	def create_and_link_collection_hierarchy(self):
		self.log.info("Create Collection Hierarchy")
		tip_coll = None
		for c, p in self.parent_collections.items():
			c = self.cm.add_element(c)
			if c.incoming_name not in self.objects_collection_list:
				continue
			
			new_coll = None
			for i, pp in enumerate(p):
				pp = self.cm.add_element(pp)
				if pp.incoming_name not in self.objects_collection_list:
					continue
				
				if i == 0:
					tip_coll = self.cm.create_collection(c.name)

				if pp.incoming_name == self.root_collection_name:
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
		for o in self.source_object_list:
			for c in self.selected_objects_parent_collection[o]:
				if c in self.parent_collections.keys():
					c = self.cm.add_element(c)
					if c.name not in bpy.data.collections:
						self.cm.create_collection(c.name)
						parents = self.parent_collections[c.incoming_name]
						for p in parents:
							parent = self.cm.add_element(p)
							if parent.name not in bpy.data.collections:
								self.cm.create_collection(parent.name)
							self.cm.link_collection_to_collection(c, parent)
					self.cm.link_object_to_collection(self.imported_objects[o], c)
			self.cm.unlink_object_from_collection(self.imported_objects[o], self.root_collection)
	
	def link_dependencies_in_dedicated_collection(self):
		if self.have_dependencies:
			dependency_collection = self.cm.add_collection(DEPENDENCIES_COLLECTION_NAME)
			self.log.info(f'Link Dependencies in "{dependency_collection.name}" collection')
			dependency_collection = self.cm.create_collection(dependency_collection.name)
			self.cm.link_collection_to_collection(dependency_collection, self.root_collection)

			for o in self.imported_objects.keys():
				if o in self.source_object_list:
					continue
				if o not in self.root_collection.objects:
					continue

				self.cm.move_object_to_collection(self.imported_objects[o], self.root_collection, dependency_collection)
	
	def link_dependencies_in_their_respective_collection(self):
		if self.have_dependencies:
			self.log.info('Link Dependencies to their respective collection')
			for o in self.imported_objects.keys():
				if o in self.source_object_list:
					continue

				self.log.info(f'Linking Dependency object "{o}"')
	
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
							self.cm.link_object_to_collection(self.imported_objects[o], parent_coll)

					self.cm.unlink_object_from_collection(self.imported_objects[o], self.root_collection)
	
	# Helper Methods
	def remove_objects_chilren(self):
		self.log.info('Removing Object Children')
		for o in self.imported_objects:
			if o not in self.objects_children.keys():
				continue
			children =  self.objects_children[o]

			for c in children:
				if c not in self.source_object_list:
					c = self.om.add_element(c)
					if c.name in bpy.data.objects:
						self.log.info(f'Remove object children : "{c.name}"')
						bpy.data.objects.remove(bpy.data.objects[c.name])
	
	def clean_file(self):
		self.log.info("Cleaning File")
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
		self.log.info(f'Linking objects from source file {blend_file} to Collection {collection}')
		def library_link_all(data_blocks, libpath, collection):
			for x in data_blocks:
				if x.library is not None:
					if os.path.normpath(libpath) == os.path.normpath(x.library.filepath):
						if x.name in self.imported_childs:
							self.log.info(f"Importing child : {x.name}")
						else:
							self.log.info(f"Importing : {x.name}")
						collection.objects.link(x)
						self.om.add_element(x.name)
		
		def load_loop(data_from, data_to, object_to_include):
			object_to_include = object_to_include.copy()
			for name in data_from.objects:
				# Import objects
				if name in object_to_include:
					data_to.objects.append(name)
				
				if self.export_object_children:
					if name not in self.objects_children.keys():
						continue
					
					children =  self.objects_children[name]
					if len(children):

						for c in children:
							self.imported_childs.append(c)
							data_to.objects.append(c)

		# Link objects
		with bpy.data.libraries.load(blend_file, link=True) as (data_from, data_to):
			load_loop(data_from, data_to, object_names)
				
		library_link_all(bpy.data.objects, blend_file, collection)
  
	def make_imported_objects_local(self):
		self.log.info(f'Make all imported objects local')
		for o in self.imported_objects.values():
			self.log.info(f'Make local : {o.name}')
			o.make_local()
			if o.data is None:
				continue
			
			o.data.make_local()
		
		if self.export_object_children:
			self.parent_children_hierarchy()
		else:
			self.remove_objects_chilren()
				
	# Traverse Tree and parent lookup from brockmann: https://blender.stackexchange.com/a/172581
	def traverse_tree(self, t):
		yield t
		for child in t.children:
			yield from self.traverse_tree(child)

	def parent_lookup(self, coll):
		parent_lookup = {}
		for coll in self.traverse_tree(coll):
			for c in coll.children.keys():
				if c not in parent_lookup:
					parent_lookup.setdefault(c, [coll.name])
				else:
					parent_lookup[c].append(coll.name)
		return parent_lookup

	def get_parent_collection_names(self, collection, parent_names, collection_data):
		if collection.name not in parent_names:
			parent_names.append(collection.name)
		for parent_collection in collection_data:
			if collection.name in parent_collection.children.keys():
				if parent_collection.name not in parent_names:
					parent_names.append(parent_collection.name)
				self.get_parent_collection_names(
					parent_collection, parent_names, collection_data)
				return

	def get_objects_collection_hierarchy(self, objs, collections_in_scene, collection_data):
		collection_hierarchy = {}
		for obj in objs:
			parent_collection = []
			for coll in obj.users_collection:
				if coll.name not in collections_in_scene:
					continue
				self.get_parent_collection_names(coll, parent_collection, collection_data)
				collection_hierarchy.setdefault(obj.name, parent_collection)
		return collection_hierarchy
	
	def get_object_children(self, obj):
		children = []
		parents = [o for o in bpy.data.objects]
		for ob in parents: 
			if ob.parent == obj: 
				children.append(ob.name)
				# self.get_object_children(ob, children)
		return children 

	def remove_source_library(self):
		if len(self.previous_library_objects) or len(self.previous_library_collections) or len(self.previous_library_scenes):
			objects = [o for o in bpy.data.objects if o.library is not None and os.path.normpath(o.library.filepath) == os.path.normpath(self.source_file) and o not in self.previous_library_objects.values()]
			collections = [c for c in bpy.data.collections if c.library is not None and os.path.normpath(c.library.filepath) == os.path.normpath(self.source_file) and c not in self.previous_library_collections.values()]
			scenes = [s for s in bpy.data.scenes if s.library is not None and os.path.normpath(s.library.filepath) == os.path.normpath(self.source_file) and s not in self.previous_library_scenes.values()]

			for o in objects :
				bpy.data.objects.remove(o)

			for c in collections:
				bpy.data.collections.remove(c)

			for s in scenes:
				bpy.data.scenes.remove(s)
		else:
			for l in bpy.data.libraries:
				if l.name == os.path.basename(self.source_file):
					self.log.info(f'Remove library : {self.source_file}')
					bpy.data.libraries.remove(l)

	def parent_children_hierarchy(self):
		for o, c in self.objects_children.items():
			p = self.om.get_element_by_incoming_name(o)
			for h in c:
				cc = self.om.get_element_by_incoming_name(h)

				self.om.parent(p.object, cc.object, keep_transform = True)


def unique_name_clean_func(name):
	word_pattern = re.compile(r'(\.[0-9]{3})$', re.IGNORECASE)
	name_iter = word_pattern.finditer(name)
	name_iter_match = [w.group(1) for w in name_iter]

	if len(name_iter_match) and name_iter_match[0] is not None:
			return name.replace(name_iter_match[0], '')
	else:
		return name

if __name__ == "__main__":
	IC = ImportCommand(sys.argv)
	IC.import_command()
