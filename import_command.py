import bpy
import os
import sys
import argparse

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eab_utils")
sys.path.append(os.path.dirname(SCRIPT_DIR))

from eab_utils.logger import Logger
from eab_utils.manager import ObjectManager, CollectionManager
from eab_utils.element import Collection, Object
from eab_utils.object_dependencies import ObjectDependencies
import eab_utils.utils as U

IMPORT_COLLECTION_NAME = 'TILA_IMPORT_COLLECTION'
DEPENDENCIES_COLLECTION_NAME = 'Dependencies'				

class ImportCommand():
	def __init__(self, argv):
		self.parse_argsv(argv[argv.index("--") + 1:])
		self.log = Logger(addon_name='Import Command', print=self.print_debug)
		self.init_source_lists()
		self._imported_objects = None
		self._valid_collections = None
		self.cm = CollectionManager(bpy.data.collections, Collection, self.print_debug)
		self.om = ObjectManager(bpy.data.objects, Object, self.print_debug)

	def conform_path(self, path):
		return os.path.normpath(bpy.path.abspath(path))
		
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
							default='ACTIVE_SCENE',
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
		
		name_collision_group = parser.add_argument_group('Name Collsion')
		name_collision_group.add_argument('-i', '--imported_names', nargs='+',
									help='Each object matching "imported_names" names will be renamed to "new_name" after import, both list need to have the same length',
									required=False)
		name_collision_group.add_argument('-x', '--new_names', nargs='+',
									help='Each object matching "imported_names" names will be renamed to "new_name" after import, both list need to have the same length',
								   required=False)

								   

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

		imported_names = args.imported_names
		new_names = args.new_names

		if imported_names is None or new_names is None:
			self.name_correspondance = {}
		else:
			if len(imported_names) != len(new_names):
				self.log.error('imported_names and new_names need to have the same length')
				self.log.error(f'new_names = {new_names}')
				self.log.error(f'imported_names = {imported_names}')
				sys.exit()
			else:
				self.name_correspondance = {imported_names[i]: new_names[i] for i in range(len(imported_names))}
		
		self.print_debug = eval(args.print_debug)
	
	def init_source_lists(self):
		# register previously loaded libraries
		self.previous_library_objects = {	o.name: o for o in bpy.data.objects if
											o.library is not None and
											self.conform_path(o.library.filepath) == self.conform_path(self.source_file)}
		self.previous_library_collections = {	c.name: c for c in bpy.data.collections if
												c.library is not None and
												self.conform_path(c.library.filepath) == self.conform_path(self.source_file)}
		self.previous_library_scenes = {s.name: s for s in bpy.data.scenes if
										s.library is not None and
										self.conform_path(s.library.filepath) == self.conform_path(self.source_file)}

		self.previous_collections = {	c.name: c for c in bpy.data.collections}

		with bpy.data.libraries.load(self.source_file, link=True) as (data_from, data_to):
			for s in data_from.scenes:
				data_to.scenes.append(s)
			for c in data_from.collections:
				data_to.collections.append(c)
			for o in data_from.objects:
				data_to.objects.append(o)

		# register imported library datas
		objects = {	o.name: o for o in bpy.data.objects if
					o.library is not None and
					self.conform_path(o.library.filepath) == self.conform_path(self.source_file)}
		collections = {	c.name: c for c in bpy.data.collections if
						c.library is not None and
				  		self.conform_path(c.library.filepath) == self.conform_path(self.source_file)}
		scenes = {	s.name:s for s in bpy.data.scenes if
					s.library is not None and
					self.conform_path(s.library.filepath) == self.conform_path(self.source_file)}

		# register object children
		self.objects_children = {}
		object_to_process = self.source_object_list.copy()

		while len(object_to_process):
			o = object_to_process.pop(0)
			self.objects_children[o] = U.get_object_children(objects[o])
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
		
		# register object depencencies
		self.object_dependencies = {}
		self.dependency_object_list = []
		for o in objects.values():
			dep = ObjectDependencies(o)
			self.object_dependencies[o.name] = dep.dependencies
			self.dependency_object_list += dep.dependency_objects

		for o in self.dependency_object_list:
			if o not in self.source_object_list:
				self.source_object_list.append(o)

		# register parent collections
		self.parent_collections = self.parent_lookup(scenes[self.source_scene_name].collection)

		self.selected_objects_parent_collection = {}
		for o in self.source_object_list:
			self.selected_objects_parent_collection[o] = [c.name for c in objects[o].users_collection]
			if o not in self.objects_children.keys():
				continue
			for c in self.objects_children[o]:
				self.selected_objects_parent_collection[c] = [cc.name for cc in objects[c].users_collection]
		
		# register root collection name
		self.root_collection_name = scenes[self.source_scene_name].collection.name

		# register collections in scene
		self.collections_in_scene = [c.name for c in collections.values() if scenes[self.source_scene_name].user_of_id(c)]

		# register object_collection_hierarchy
		self.objects_collection_hierarchy = self.get_objects_collection_hierarchy([o for o in objects.values() if o.name in self.source_object_list], self.collections_in_scene, collections.values())

		# register objects collection list
		self.objects_collection_list = [scenes[self.source_scene_name].collection.name]
		for c in self.objects_collection_hierarchy.values():
			for cc in c:
				if cc not in self.objects_collection_list:
					self.objects_collection_list.append(cc)

		# register all objects collection hierarchy
		self.all_objects_collection_hierarchy = {}
		for o in objects.values():
			hierarchies = []
			for c in o.users_collection:
				if c.name in self.previous_collections.keys():
					continue
				coll = []
				self.get_parent_collection_names(c, coll, collections.values())
				hierarchies.append(coll)
			self.all_objects_collection_hierarchy[o.name] = hierarchies

		self.imported_childs = []

		# remove objects and collections
		self.remove_source_library()
		
		# log all registered parameters
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
		self.log.info(f'objects_children = {self.objects_children}')
		self.log.info(f'object_dependencies = {self.object_dependencies}')
		self.log.info(f'dependency_object_list = {self.dependency_object_list}')
		self.log.info(f'name_correspondance = {self.name_correspondance}')

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
		if self.target_scene != 'ACTIVE_SCENE':
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
		self.link_objects(self.source_file, self.source_object_list, bpy.data.collections[IMPORT_COLLECTION_NAME], self.export_mode == 'LINK')

		self.have_dependencies = len(bpy.data.collections[IMPORT_COLLECTION_NAME].objects) > len(self.source_object_list)

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

		if self.export_object_children:
			self.parent_children_hierarchy()
		# else:
		# 	self.remove_objects_chilren()
			
		if self.export_mode == 'APPEND':
			for imported_name, new_name in self.name_correspondance.items():
				new_name = self.om.get_next_valid_name(new_name)
				self.log.info(f'Renaming object "{imported_name}" to "{new_name}"')
				bpy.data.objects[imported_name].name = new_name

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
			nc = self.cm.get_element_by_incoming_name(c)
			if nc.incoming_name not in self.objects_collection_list:
				continue
			
			new_coll = None
			for i, pp in enumerate(p):
				npp = self.cm.get_element_by_incoming_name(pp)
				if npp.incoming_name not in self.objects_collection_list:
					continue
				
				if i == 0 and nc.name not in bpy.data.collections:
					tip_coll = self.cm.create_collection(c)
				else:
					tip_coll = nc

				if npp.incoming_name == self.root_collection_name:
					self.cm.link_collection_to_collection(tip_coll, self.root_collection)
				else:
					if npp.name not in bpy.data.collections:
						new_coll = self.cm.create_collection(pp)

					if new_coll is None:
						new_coll = npp
						
					if nc.name not in new_coll.children:
						self.cm.link_collection_to_collection(tip_coll, new_coll)
		
		# Link Object to collections
		self.log.info("Link Objects to Collection")
		for o in self.source_object_list:
			for c in self.selected_objects_parent_collection[o]:
				if c in self.parent_collections.keys():
					c = self.cm.get_element_by_incoming_name(c)
					if c.name not in bpy.data.collections:
						self.cm.create_collection(c.name)
						parents = self.parent_collections[c.incoming_name]
						for p in parents:
							parent = self.cm.get_element_by_incoming_name(p)
							if parent.name not in bpy.data.collections:
								self.cm.create_collection(parent.name)
							self.cm.link_collection_to_collection(c, parent)
					self.cm.link_object_to_collection(self.imported_objects[o], c)
			self.cm.unlink_object_from_collection(self.imported_objects[o], self.root_collection)
	
	
	def link_dependencies_in_dedicated_collection(self):
		if self.have_dependencies:
			dependency_collection = self.cm.add_element(DEPENDENCIES_COLLECTION_NAME)
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
							c = self.cm.get_element_by_incoming_name(c)
							if i == 0:
								if c.name not in bpy.data.collections:
									self.cm.create_collection(c.name)
									self.cm.link_collection_to_collection(c, self.root_collection)
								elif c.name not in self.root_collection.children:
									self.cm.link_collection_to_collection(c, self.root_collection)
							else:
								if c.name not in bpy.data.collections:
									self.cm.create_collection(c.name)
		 
								parent_coll = self.cm.get_element_by_incoming_name(hierarchy[i-1])
								if c.name not in parent_coll.children:
									self.cm.link_collection_to_collection(c, parent_coll)
						else:
							parent_coll = self.cm.get_element_by_incoming_name(hierarchy[len(hierarchy)-1])
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
					c = self.om.add_element(bpy.data.objects[c])
					if c in bpy.data.objects:
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

	def link_objects(self, blend_file, object_names, collection, is_link):
		self.log.info(f'Linking objects from source file {blend_file} to Collection {collection}')
		imported_objects = []
		def library_link_all(data_blocks, libpath, collection):
			for x in data_blocks:
				if x.name not in imported_objects:
					continue

				if self.export_mode == 'LINK':
					if x.library is not None:
						if self.conform_path(libpath) == self.conform_path(x.library.filepath):
							link_to_collection(x, collection)
				else:
					link_to_collection(x, collection)
						
		def link_to_collection(object, collection):
			if object.name in self.imported_childs:
				self.log.info(f'Linking child "{object.name}" to collection "{collection.name}"')
			else:
				self.log.info(f'Linking "{object.name}" to collection "{collection.name}"')
			collection.objects.link(object)
		
		def load_loop(data_from, data_to, object_to_include):
			object_to_include = object_to_include.copy()
			for name in data_from.objects:
				# Import objects
				if name in object_to_include:
					if name not in data_to.objects:
						self.log.info(f'Importing : {name}')
						data_to.objects.append(name)
					if name not in imported_objects:
						imported_objects.append(name)

				if self.export_object_children:
					if name not in self.objects_children.keys():
						continue
					
					children = self.objects_children[name]
					for c in children:
						if c not in self.imported_childs:
							self.imported_childs.append(c)
						if c not in data_to.objects:
							self.log.info(f'Importing child : {c}')
							data_to.objects.append(c)
						if c not in imported_objects:
							imported_objects.append(c)

		# Link objects
		with bpy.data.libraries.load(blend_file, link=is_link) as (data_from, data_to):
			load_loop(data_from, data_to, object_names)

		self.imported_objects = {o.name:o for o in bpy.data.objects if o.name in imported_objects}

		library_link_all(bpy.data.objects, blend_file, collection)

		if self.export_object_children:
			self.ordered_children = self.reorder_list_child_first(list(self.imported_objects.values()), include_parent=True)
			self.log.info(f'ordered_children = {self.ordered_children}')
	

	def make_imported_objects_local(self):
		self.log.info(f'Make all imported objects local')
		if self.export_object_children:
			object_list = self.ordered_children
		else:
			object_list = [bpy.data.objects[o] for o in self.imported_objects]

		for o in object_list:
			self.log.info(f'Make local : {o.name}')
			obj = self.om.add_element(o, register=True)
			o.make_local()
			if o.data is None:
				continue
			
			o.data.make_local()

			layer = bpy.context.view_layer
			layer.update()

			self.om.update_element_name(o, o.name)
			obj.name = o.name

	def resolve_dependencies(self):
		self.log.info(f'Resolve objects dependencies')
		for e in self.om.element_list:
			print(e.incoming_name, e.name, e.object.name)
		for o in self.om.element_list:
			dependency = ObjectDependencies(o.object, True)
			dependency.depenencies = self.object_dependencies[o.incoming_name]
			dependency.resolve_dependencies(self.om)

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
	

	def remove_source_library(self):
		if len(self.previous_library_objects) or len(self.previous_library_collections) or len(self.previous_library_scenes):
			objects = [o for o in bpy.data.objects if o.library is not None and self.conform_path(o.library.filepath) == self.conform_path(self.source_file) and o not in self.previous_library_objects.values()]
			collections = [c for c in bpy.data.collections if c.library is not None and self.conform_path(c.library.filepath) == self.conform_path(self.source_file) and c not in self.previous_library_collections.values()]
			scenes = [s for s in bpy.data.scenes if s.library is not None and self.conform_path(s.library.filepath) == os.path.normpath(self.source_file) and s not in self.previous_library_scenes.values()]

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
			p = self.om.add_element(bpy.data.objects[o])
			for h in c:
				cc = self.om.add_element(bpy.data.objects[h])
				self.om.parent(p, cc, keep_transform=True)

	def reorder_list_child_first(self, object_list, include_parent=False):
		object_list = object_list.copy()
		ordered_list = []
		def insert_in_list(o, index):
			if o not in ordered_list:
				ordered_list.insert(index, o)

		while len(object_list):
			o = object_list.pop(0)
			if not len(o.children):
				insert_in_list(o, 0)
			else:
				if o.parent is None:
					insert_in_list(o, len(ordered_list))
				else:
					if o.parent in ordered_list:
						insert_in_list(o, ordered_list.index(o.parent)-1)
					else:
						if include_parent:
							object_list.insert(0, o.parent)
						insert_in_list(o, 0)
					if len(o.children):
						for c in o.children:
							if c in ordered_list:
								insert_in_list(o, ordered_list.index(c)+1)
							else:
								insert_in_list(o, 0)
								insert_in_list(c, 0)
		return ordered_list


if __name__ == "__main__":
	IC = ImportCommand(sys.argv)
	IC.import_command()
