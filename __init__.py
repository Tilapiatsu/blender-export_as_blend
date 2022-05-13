import bpy
import bpy_extras
import textwrap
import subprocess
import tempfile
import shutil
import os
import stat
from os import path

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

def _label_multiline(context, text, parent):
	chars = int(context.region.width / 7)   # 7 pix on 1 character
	wrapper = textwrap.TextWrapper(width=chars)
	text_lines = wrapper.wrap(text=text)
	for text_line in text_lines:
		parent.label(text=text_line)

class TILA_OP_ExportAsBlend(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
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

	file_override :bpy.props.EnumProperty(
		items=[("OVERRIDE", "Override", ""), ("APPEND_LINK", "Append/Link", "")],
		name='File Override',
  		description = ' Choose what behaviour you want if you have choosen an existing file')
 
	export_mode: bpy.props.EnumProperty(
		items=[("APPEND", "Append", ""), ("LINK", "Link", "")],
		name='Export Mode',
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
		r.prop(self, 'file_override', expand=True)
		r = col.row()
		r.prop(self, 'export_mode', expand=True)
  
		if self.export_mode == "APPEND":
			box.prop(self, 'pack_external_data')

		if self.file_override == 'OVERRIDE':
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

		box = col.box()
		source = 'Selected objects' if self.source == 'SELECTED_OBJECTS' else 'The current scene'
		file_override = 'overriding' if self.file_override == 'OVERRIDE' else 'appending/linking in'
		export_mode = 'appended' if self.export_mode ==  'APPEND' else 'linked'
		if self.file_override == 'OVERRIDE':
			export_to_clean_file = ' Data will be exported to a clean file.' if self.export_to_clean_file else ' Data will be exported to your startup file.'
			
		else:
			export_to_clean_file = ''

		if self.source == 'SELECTED_OBJECTS':
			create_collection_hierarchy = ' The collection hierarchy of selected objects will be preserved.' if self.create_collection_hierarchy else f' Selected objects will be exported without its collections.'
			dependencies_in_dedicated_collection = ' All objects will be placed under a "Dependencies" collection.' if self.dependencies_in_dedicated_collection else ' Each object dependencies will be exported into its dedicated collection.'
			export_in_new_collection = f' All Objects and Dependencies will be exported in a root collection called "{self.new_collection_name}".' if self.export_in_new_collection else ''
		else:
			create_collection_hierarchy = ''
			dependencies_in_dedicated_collection = ''
			export_in_new_collection = ''

		pack_external_data = 'all external data will be packed into blend file' if self.pack_external_data else ''
		open_exported_blend = 'the exported file will be opened.' if self.open_exported_blend else ''

		if len(pack_external_data) and len(open_exported_blend):
			open_exported_blend = 'and ' + open_exported_blend

		text = f'''{source} will be {export_mode} from current file, {file_override} selected file.{export_to_clean_file}{create_collection_hierarchy}{dependencies_in_dedicated_collection}{export_in_new_collection}'''
		_label_multiline(context=context, text=text, parent=layout)
		text = f'''Once exported, {pack_external_data} {open_exported_blend}'''
		_label_multiline(context=context, text=text, parent=layout)

	def __init__(self):
		self.objects_dict = {}
		self._selected_objects = None
		self._parent_collections = None
		self._objects_collection_hierarchy = None
		self._selected_objects_parent_collection = None
		self._all_objects_collection_hierarchy = None
		self._all_objects = None
		self._all_collections = None

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
			self.file_override == 'OVERRIDE'

		self.feed_scene_list(context)

		import_parameters = [	'-f', self.curent_file,
								'-s', self.source,
								'-o', self.file_override,
								'-m', self.export_mode,
								'-X', str(self.export_to_clean_file),
								'-c', str(self.create_collection_hierarchy),
								'-d', self.filepath,
								'-N', str(self.export_in_new_collection),
								'-n', self.new_collection_name,
								'-D', str(self.dependencies_in_dedicated_collection),
								'-p', str(self.pack_external_data),
								'-S', context.scene.name,
								'-O', str(self.selected_objects),
								'-P', self.parent_collections,
								'-C', self.selected_objects_parent_collections,
								'-r', self.root_collection_name,
								'-l', self.objects_collection_list,
								'-H', self.all_objects_collection_hierarchy
							]

		if self.file_override == 'OVERRIDE':
			subprocess.check_call([bpy.app.binary_path,
						'--background',
						'--factory-startup',
						'--python', path.join(path.dirname(path.realpath(__file__)), 'import_command.py'), '--'] + import_parameters)
		elif self.file_override == 'APPEND_LINK':
			subprocess.check_call([bpy.app.binary_path,
						'--background',
						self.filepath,
						'--factory-startup',
						'--python', path.join(path.dirname(path.realpath(__file__)), 'import_command.py'), '--'] + import_parameters)

				

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

		self.__init__()
		return {'FINISHED'}

	def feed_scene_list(self, context):
		self.selected_objects = self.get_object_list_name(context.selected_objects)
		parent_collections = self.parent_lookup(context.scene.collection)
		self.root_collection_name = context.scene.collection.name
		self.parent_collections = self.get_dict_as_string(parent_collections)
		self.root_collection_name = context.scene.collection.name
		self.collections_in_scene = [c.name for c in bpy.data.collections if bpy.context.scene.user_of_id(c)]
		self.objects_collection_hierarchy = self.get_objects_collection_hierarchy(context.selected_objects)
  
		self.objects_collection_list = [bpy.context.scene.collection.name]
		for c in self.objects_collection_hierarchy.values():
			for cc in c:
				if cc not in self.objects_collection_list:
					self.objects_collection_list.append(cc)

		self.objects_collection_list = self.get_list_as_string(self.objects_collection_list)
  
		self.selected_objects_parent_collection = {}
		for o in context.selected_objects:
			self.selected_objects_parent_collection[o.name] = [c.name for c in o.users_collection]

		self.selected_objects_parent_collections = self.get_dict_as_string(self.selected_objects_parent_collection)

		self.all_objects_collection_hierarchy = {}
		for o in bpy.data.objects:
			hierarchies = []
			for c in o.users_collection:
				coll = []
				self.get_parent_collection_names(c, coll)
				hierarchies.append(coll)
			self.all_objects_collection_hierarchy[o.name] = hierarchies

		self.all_objects_collection_hierarchy = self.get_dict_as_string(self.all_objects_collection_hierarchy)

	def get_object_list_name(self, object_list):
		string_names = '['
		for i, o in enumerate(object_list):
			string_names += f'"{o.name}"'
			if i < len(object_list)-1:
				string_names += ', '

		string_names += ']'
		return string_names

	def get_list_as_string(self, l):
		string_names = '['
		for i, o in enumerate(l):
			if isinstance(o, list):
				string_names += self.get_list_as_string(o)
				if i < len(l)-1:
					string_names += ', '
			elif isinstance(o, str):
				string_names += f'"{o}"'
				if i < len(l)-1:
					string_names += ', '

		string_names += ']'
		return string_names

	def get_dict_as_string(self, d):
		string_dict = '{'
		i = 0
		parent = ''
		for o, p in d.items():
			string_dict += f'"{o}":{self.get_list_as_string(p)}'
			if i < len(d.keys())-1:
				string_dict += ', '

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
