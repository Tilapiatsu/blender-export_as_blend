import bpy
import subprocess
import tempfile
import shutil
import os
import stat
from os import path
from bpy_extras.io_utils import ExportHelper

bl_info = {
	"name": "Export as Blend",
	"author": "Tilapiatsu",
	"description": "This addon allow you to export data to a new blend file, from selected Objects or a comlplete Scene.",
	"version": (1, 1, 0),
	"blender": (3, 1, 0),
	"location": "File > Export > Export as Blend (.blend)",
	"warning": "",
	"category": "Import-Export"
}

def update_override(self, context):
    if self.override != 'OVERRIDE':
    	self.export_to_clean_file = False


class TILA_OP_ExportAsBlend(bpy.types.Operator, ExportHelper):
	bl_idname = "export_scene.tila_export_as_blend"
	bl_label = "Export as Blend"
	bl_options = {'REGISTER', 'INTERNAL'}
	bl_region_type = "UI"

	filter_glob: bpy.props.StringProperty(
		default="*.blend", options={'HIDDEN'})

	check_existing: bpy.props.BoolProperty(
		name="Check Existing",
		description="Check and warn on overwriting existing files",
		default=True,
		options={'HIDDEN'},
	)

	files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
	source: bpy.props.EnumProperty(
     				items=[("SELECTED_OBJECTS", "Selected Objects", ""),
                			("CURRENT_SCENE", "Current Scene", "")])

	override :bpy.props.EnumProperty(
		items=[("OVERRIDE", "Override", ""), ("APPEND_LINK", "Append/Link", "")],
  		description = ' Choose what behaviour you want if you have choosen an existing file',
    	update=update_override)
 
	mode: bpy.props.EnumProperty(
		items=[("APPEND", "Append", ""), ("LINK", "Link", "")],
  		description='Choose how you want the data to be transfered from the current file.')
	
	create_collection_hierarchy: bpy.props.BoolProperty(name='Create Collection Hierarchy',
														description='Each Objects will be exported in its respective collection hierarchy from the source Blend file. Otherwise all Objects will be exported in the default collection',
														default=True)
	export_to_clean_file: bpy.props.BoolProperty(	name='Export To Clean File',
												  description='If enable the startup file will be skipped and the data will be exported in a clean empty file',
												  default=True)
	export_in_new_collection: bpy.props.BoolProperty(name='Export objects in new collection',
																description='Each objects, dependencies and collection hierarchy will be placed in a new collection',
																default=False)
	new_collection_name: bpy.props.StringProperty(name='Root Collection name',
                                                	description='Name of the new collection that will be created',
													default='Root Collection')
	dependencies_in_dedicated_collection: bpy.props.BoolProperty(name='Export dependencies in dedicated collection',
																		description='Each object dependencies are put in a dedicated collection named "Dependencies". If unchecked, each dependencies will be placed their respective collection from the source blend file',
																		default=False)
	pack_external_data: bpy.props.BoolProperty(	name='Pack External Data',
												description='All data exported will be packed into the blend file, to avoid external files dependencies. It would increase drastically the size of the exported file and saving time',
												default=False)
	open_exported_blend: bpy.props.BoolProperty(	name='Open Exported Blend',
												 description='The Exported blend file will be opened after export',
												 default=False)
	# relink_as_library : bpy.props.BoolProperty(	name='Relink as Library',
	#                                         	description='After export, the file is relink as a library in the current Scene',
	#                                          	default=False)
	filename_ext = '.blend'
	
	def draw(self, context):
		layout = self.layout
		col = layout.column()
		col.label(text='Export Settings')
		box = col.box()

		row = box.row()
		col = row.column()
		col.alignment = 'RIGHT'
		col.label(text='source')
		col.label(text='override')
		col.label(text='mode')

		col = row.column()
		col.alignment = 'EXPAND'
		r = col.row()
		r.prop(self, 'source', expand=True)
		r = col.row()
		r.prop(self, 'override', expand=True)
		r = col.row()
		r.prop(self, 'mode', expand=True)
  
		if self.mode == "APPEND":
			box.prop(self, 'pack_external_data')

		if self.override == 'OVERRIDE':
			box.prop(self, 'export_to_clean_file')

		if self.source == "SELECTED_OBJECTS":
			box.prop(self, 'create_collection_hierarchy')
			box.prop(self, 'dependencies_in_dedicated_collection')
			col = box.row()
			col.prop(self, 'export_in_new_collection')
			col = box.row()
			col.alignment = 'EXPAND'
			col.prop(self, 'new_collection_name', text='Name')
			col.enabled = self.export_in_new_collection

		box.prop(self, 'open_exported_blend')
		# col.prop(self, 'relink_as_library')

	@property
	def is_linked(self):
		return self.mode == "LINK"

	def execute(self, context):
		ext = path.splitext(self.filepath)[1].lower()
		if ext != '.blend':
			self.filepath += '.blend'

		# Save to a temp folder if currnt file is dirty. Otherwise some objects will not be visible from the target file.
		if bpy.data.is_dirty:
			self.tmpdir = tempfile.mkdtemp()
			self.curent_file = path.join(
				self.tmpdir, path.basename(self.filepath))
			bpy.ops.wm.save_as_mainfile(
				'EXEC_DEFAULT', filepath=self.curent_file, copy=True)
			saved_to_temp_folder = True
		else:
			self.curent_file = bpy.data.filepath
			saved_to_temp_folder = False

		if not path.exists(self.filepath):
			self.override == 'OVERRIDE'

		self.feed_scene_list(context)

		# command = self.generate_command(context)
		# print(command)

		subprocess.check_call([bpy.app.binary_path,
								   '--background',
								   path.join(path.dirname(path.realpath(__file__)), 'StartupClean', "StartupClean.blend"),
								   	'--factory-startup',
								   	'--python', path.join(path.dirname(path.realpath(__file__)), 'import_command.py'), '--',
									'-f', self.curent_file,
									'-s', self.source,
									'-o', self.override,
									'-m', self.mode,
									'-N', str(self.export_in_new_collection),
									'-n', self.new_collection_name,
									'-d', str(self.dependencies_in_dedicated_collection),
									'-p', str(self.pack_external_data),
									'-S', context.scene.name,
									'-O', self.selected_objects,
									'-P', self.parent_collections,
									'-r', self.root_collection,
									'-l', self.objects_collection_list,
									'-H', self.all_objects_collection_hierarchy
							])		
		# if self.export_to_clean_file:
		# 	subprocess.check_call([bpy.app.binary_path,
		# 						   '--background',
		# 						   path.join(path.dirname(path.realpath(
		# 							   __file__)), 'StartupClean', "StartupClean.blend"),
		# 						   '--factory-startup',
		# 						   '--python-expr', command,
		# 						   ])
		# else:
		# 	if self.override == 'OVERRIDE':
		# 		subprocess.check_call([bpy.app.binary_path,
		# 							'--background',
		# 							'--factory-startup',
		# 							'--python-expr', command,
		# 							])
		# 	else:
		# 		subprocess.check_call([bpy.app.binary_path,
		# 							self.filepath,
		# 							'--background',
		# 							'--factory-startup',
		# 							'--python-expr', command,
		# 							])
				

		#   Not Working Yet
		# if self.relink_as_library:
		# 	for o in self.selected_objects:
		# 		for c in o.users_collection:
		# 			if c.name in self.objects_collection_list:
		# 				c.objects.unlink(bpy.data.objects[o.name])

		# 		self.link_blend_file(self.filepath, 'Object', o.name)

		# 		for c in self.objects_collection_hierarchy.values():
		# 			for cc in c:
		# 				bpy.data.collections[cc].objects.link(bpy.data.objects[o.name])

		if self.open_exported_blend:
			subprocess.Popen([bpy.app.binary_path,
							  self.filepath
							  ])

		if saved_to_temp_folder:
			delete_folder_if_exist(self.tmpdir)

		return {'FINISHED'}

	def feed_scene_list(self, context):
		self.selected_objects = self.get_object_list_name(context.selected_objects)
		parent_collections = self.parent_lookup(context.scene.collection)
		self.parent_collections = self.get_dict_as_string(parent_collections)
		self.root_collection = context.scene.collection.name
		self.collections_in_scene = [c.name for c in bpy.data.collections if bpy.context.scene.user_of_id(c)]
		self.objects_collection_hierarchy = self.get_objects_collection_hierarchy(context.selected_objects)
  
		self.objects_collection_list = [bpy.context.scene.collection.name]
		for c in self.objects_collection_hierarchy.values():
			for cc in c:
				if cc not in self.objects_collection_list:
					self.objects_collection_list.append(cc)

		self.objects_collection_list = self.get_list_as_string(self.objects_collection_list)
  
		# self.object_data_dependencies = {}
		# for o in context.selected_objects:
		# 	if o.data is None:
		# 		continue
		# 	if o.data.name not in self.object_data_dependencies.keys():
		# 		self.object_data_dependencies[o.data.name] = [o.name]
		# 	else:
		# 		self.object_data_dependencies[o.data.name].append(o.name)


		self.all_objects_collection_hierarchy = {}
		for o in bpy.data.objects:
			hierarchies = []
			for c in o.users_collection:
				coll = []
				self.get_parent_collection_names(c, coll)
				hierarchies.append(coll)
			self.all_objects_collection_hierarchy[o.name] = hierarchies

		self.all_objects_collection_hierarchy = self.get_dict_as_string(self.all_objects_collection_hierarchy)

	def generate_command(self, context):
		# Base Command and define the link function
		command = '''import bpy, os
initial_count = len(bpy.data.objects)
initial_objects = [o.name for o in bpy.data.objects]
'''
		if self.source == 'CURRENT_SCENE':
			command += f'\nprint("Importing Scene {context.scene.name}")'
			command += f'''\nfilepath = os.path.join(r'{self.curent_file}', 'Scene', '{context.scene.name}')
directory = os.path.join(r'{self.curent_file}', 'Scene')
bpy.ops.wm.append(filepath = filepath, directory = directory, filename = "{context.scene.name}"'''
		elif self.source == 'SELECTED_OBJECTS':
			# Import Objects
			command += f'\nprint("Importing Objects")'
			command += f'''\nfilepath = os.path.join(r'{self.curent_file}', 'Object', '{self.selected_objects[0].name}')
directory = os.path.join(r'{self.curent_file}', 'Object')
bpy.ops.wm.link(filepath = filepath, directory = directory, filename = "{self.selected_objects[0].name}", link = {self.is_linked}'''
			if len(self.selected_objects) > 1:
				command += f', files=['
				for i, o in enumerate(self.selected_objects):
					command += '{'
					command += f'"name":"{o.name}", "name":"{o.name}"'
					if i < len(self.selected_objects)-1:
						command += '},'
					else:
						command += '}]'
				command += ')'
			else:
				command += ')'

			# Register imported_objects
			command += '\nimported_objects = [o for o in bpy.data.objects if o.name not in initial_objects]'
   
			# Create New Collection and Link all imported object in it
			if self.export_in_new_collection:
				if self.new_collection_name == '':
					self.report({'ERROR'}, 'Export As Blend : Root collection name is empty, skipping root collection creation.')
					self.export_in_new_collection = False
				else:
					command += f'''\nif '{self.new_collection_name}' not in bpy.data.collections:
	bpy.data.collections.new('{self.new_collection_name}')
	bpy.context.collection.children.link(bpy.data.collections['{self.new_collection_name}'])
 '''				
					if self.mode != 'LINK':
						command += f'''\nfor o in imported_objects:
	print('Unlinking object ' + o.name + ' from collection ' + bpy.context.collection.name)
	bpy.context.collection.objects.unlink(o)
	bpy.data.collections['{self.new_collection_name}'].objects.link(o)
 '''
			# Set root_collection
			command += f'''\ncondition = {self.export_in_new_collection} and "{self.new_collection_name}" in bpy.data.collections
root_collection = bpy.data.collections['{self.new_collection_name}'] if condition else bpy.context.collection'''
				
			# Create Collection Hierarchy
			if self.create_collection_hierarchy:
				command += f'''\nprint("Create Collection Hierarchy")'''
				for c, p in self.parent_collections.items():
					if c not in self.objects_collection_list:
						continue
					for i, pp in enumerate(p):
						if pp not in self.objects_collection_list:
							continue

						command += f'''\nprint("Linking Collection {c} to {pp}")'''
						if i == 0:
							command += f'''\nbpy.data.collections.new('{c}')'''

						if pp == self.root_collection.name:
							if self.export_in_new_collection:
								command += f'''\nbpy.data.collections['{self.new_collection_name}'].children.link(bpy.data.collections["{c}"])'''
							else:
								command += f'''\nbpy.context.scene.collection.children.link(bpy.data.collections["{c}"])'''
						else:
							command += f'''\nif "{pp}" not in bpy.data.collections:
	bpy.data.collections.new('{pp}')

if '{c}' not in bpy.data.collections["{pp}"].children:
	bpy.data.collections["{pp}"].children.link(bpy.data.collections['{c}'])
'''
 
				
				command += f'''\nprint("Link Objects to Collection")'''

    			# Link Object to collections
				for o in self.selected_objects:
					for c in o.users_collection:
						if c.name in self.parent_collections.keys():
							command += f'''\nprint("Move Object {o.name} to Collection {c.name}")'''
							command += f'''\nroot_collection.objects.unlink(bpy.data.objects["{o.name}"])'''
							command += f'''\nbpy.data.collections["{c.name}"].objects.link(bpy.data.objects["{o.name}"])'''

			# Link Dependencies in a dedicated collection
			if self.dependencies_in_dedicated_collection and self.mode != "LINK":
				command += f'''\nif {len(self.selected_objects)} < len(bpy.data.objects) - initial_count:
	bpy.data.collections.new('Dependencies')
	root_collection.children.link(bpy.data.collections["Dependencies"])
 
	for o in imported_objects:
		if o.name in {self.get_object_list_name(self.selected_objects)}:
			continue
		if o.name not in root_collection.objects:
			continue
   
		print("Move Object " + o.name + " to Dependencies Collection ")
		root_collection.objects.unlink(bpy.data.objects[o.name])
		bpy.data.collections["Dependencies"].objects.link(bpy.data.objects[o.name])
'''
			# Link Dependencies in its respective collection from source blend file
			elif not self.dependencies_in_dedicated_collection and self.create_collection_hierarchy:
				command += f'''\nif {len(self.selected_objects)} < len(bpy.data.objects) - initial_count:
	for o in imported_objects:
		if o.name in {self.get_object_list_name(self.selected_objects)}:
			continue
		
		all_collection_hierarchy = {self.get_all_objects_collection_hierarchy_as_string()}

		for obj,h in all_collection_hierarchy.items():
			if obj != o.name:
				continue
			if obj not in root_collection.objects:
				continue
	
			for hh in h:
				hierarchy = list(reversed(hh))
				for i,c in enumerate(hierarchy):
					if i == 0:
						if c not in bpy.data.collections:
							bpy.data.collections.new(c)
							root_collection.children.link(bpy.data.collections[c])

						if c not in root_collection.children:
							root_collection.children.link(bpy.data.collections[c])
					else:
						if c not in bpy.data.collections:
							bpy.data.collections.new(c)
						
						if c not in bpy.data.collections[hierarchy[i-1]].children:
							bpy.data.collections[hierarchy[i-1]].children.link(bpy.data.collections[c])
				else:
					print("Move dependency Object " + o.name + " to Collection " +  c)
					root_collection.objects.unlink(bpy.data.objects[o.name])
					bpy.data.collections[hierarchy[len(hierarchy)-1]].objects.link(bpy.data.objects[o.name])
'''
# 			# Link Dependencies in New Collection
# 			elif self.export_in_new_collection and not self.create_collection_hierarchy:
# 				command += f'''\nif {len(self.selected_objects)} < len(bpy.data.objects) - initial_count:
# 	for o in imported_objects:
# 		if o.name in {self.get_object_list_name(self.selected_objects)}:
# 			continue
# 		bpy.context.collection.objects.unlink(bpy.data.objects[o.name])
# 		root_collection.objects.link(bpy.data.objects[o.name])
# '''
		if self.pack_external_data and self.mode == 'APPEND':
			command += '''\ntry:
	bpy.ops.file.pack_all()
except RuntimeError as e:
	print("Cannot pack data or data does not exist on drive.  " + e)'''
		command += f"\nbpy.ops.wm.save_as_mainfile('EXEC_DEFAULT',filepath=r'{self.filepath}')"
		return command

	def get_object_list_name(self, object_list):
		string_names = '['
		for i, o in enumerate(object_list):
			string_names += f'"{o.name}"'
			if i < len(object_list)-1:
				string_names += f', '

		string_names += ']'
		return string_names

	def get_list_as_string(self, l):
		string_names = '['
		for i, o in enumerate(l):
			if isinstance(o, list):
				string_names += self.get_list_as_string(o)
			elif isinstance(o, str):
				string_names += f'"{o}"'
				if i < len(l)-1:
					string_names += f', '

		string_names += ']'
		return string_names

	def get_dict_as_string(self, d):
		string_dict = '{'
		i = 0
		parent = ''
		for o, p in d.items():
			string_dict += f'"{o}":{self.get_list_as_string(p)}'
			if i < len(d.keys())-1:
				string_dict += f', '

			i += 1
		string_dict += '}'
		return string_dict

	def get_all_objects_collection_hierarchy_as_string(self):
		string_dict = '{'
		i = 0
		for o, p in self.all_objects_collection_hierarchy.items():
			parent = '['
			for j, pp in enumerate(p):
				parent += self.get_list_as_string(pp)
				# parent += f'"{pp}"'
				if j < len(p) - 1:
					parent += ','
			parent += ']'

			string_dict += f'"{o}":{parent}'
			if i < len(self.all_objects_collection_hierarchy.keys())-1:
				string_dict += f', '

			i += 1
		string_dict += '}'
		return string_dict

	def link_blend_file(self, file_path, datablock_dir, data_name):
		filepath = path.join(file_path, datablock_dir, data_name)
		directory = path.join(file_path, datablock_dir)
		bpy.ops.wm.link(filepath=filepath, directory=directory,
						filename=data_name, link=True)

	
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

	def get_parent_collection_names(self, collection, parent_names):
		if collection.name not in parent_names:
			parent_names.append(collection.name)
		for parent_collection in bpy.data.collections:
			if collection.name in parent_collection.children.keys():
				if parent_collection.name not in parent_names:
					parent_names.append(parent_collection.name)
				self.get_parent_collection_names(
					parent_collection, parent_names)
				return

	def get_objects_collection_hierarchy(self, objs):
		collection_hierarchy = {}
		for obj in objs:
			parent_collection = []
			for coll in obj.users_collection:
				if coll.name not in self.collections_in_scene:
					continue
				self.get_parent_collection_names(coll, parent_collection)
				collection_hierarchy.setdefault(obj.name, parent_collection)
		return collection_hierarchy

	def clean_scene(self):
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

def delete_folder_if_exist(p):
	if path.exists(p):
		shutil.rmtree(p, onerror=file_acces_handler)


def file_acces_handler(func, path, exc_info):
	print('Handling Error for file ', path)
	print(exc_info)
	# Check if file access issue
	if not os.access(path, os.W_OK):
		# Try to change the permision of file
		os.chmod(path, stat.S_IWUSR)
		# call the calling function again
		func(path)


def menu_func_export(self, context):
	self.layout.operator(TILA_OP_ExportAsBlend.bl_idname,
						 text="Export as Blend (.blend)")


classes = (TILA_OP_ExportAsBlend,)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)

	bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

	bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
	register()
