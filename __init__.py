import bpy
import bpy_extras
import textwrap
import subprocess
import tempfile
import shutil
import os
import stat
import sys
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


class TILA_OP_ExportAsBlendSaveCurrentFile(bpy.types.Operator):
	bl_idname = "wm.tila_export_as_blend_save_current_file"
	bl_label = r"Save Current file ?"
	bl_options = {'REGISTER', 'INTERNAL'}

	@classmethod
	def poll (cls, context):
		return bpy.data.is_dirty

	def execute(self, context):
		self.report({'INFO'}, "Saving current blend file.")
		if bpy.data.filepath == '':
			bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')
		else:
			bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT', filepath=bpy.data.filepath)
		return {'FINISHED'}

	def invoke(self, context, event):
		return context.window_manager.invoke_confirm(self, event)


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
	 				items=[("OBJECTS", "Selected Objects", ""),
							("SCENE", "Current Scene", "")])

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
	print_debug: bpy.props.BoolProperty( name='Print debug messages',
											  description='Print debug message in console',
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
		col.label(text='fiel override')
		col.label(text='export mode')

		col = row.column()
		col.alignment = 'EXPAND'
		r = col.row()
		r.prop(self, 'source', expand=True)
		r = col.row()
		r.prop(self, 'file_override', expand=True)
		r = col.row()
		r.prop(self, 'export_mode', expand=True)

		if bpy.data.is_dirty and self.export_mode == 'LINK':
			box2 = box.box()
			text='You are about to link data from an unsaved file which might not work properly. It is recommended to save before exporting.'
			_label_multiline(context=context, text=text, parent=box2)
			box2.operator('wm.tila_export_as_blend_save_current_file',
			              text="Save current file", icon='FILE_BLEND')
  
		if self.export_mode == "APPEND":
			box.prop(self, 'pack_external_data')

		if self.file_override == 'OVERRIDE':
			box.prop(self, 'export_to_clean_file')

		if self.source == "OBJECTS":
			box.prop(self, 'create_collection_hierarchy')
			box.prop(self, 'dependencies_in_dedicated_collection')
			col = box.row()
			col.prop(self, 'export_in_new_collection')
			col = box.row()
			col.alignment = 'EXPAND'
			col.prop(self, 'new_collection_name', text='Name')
			col.enabled = self.export_in_new_collection

		box.prop(self, 'open_exported_blend')
		box.prop(self, 'print_debug')
		# col.prop(self, 'relink_as_library')

		# Operation Description
		box = layout.box()
		source = 'Selected objects' if self.source == 'OBJECTS' else 'The current scene'
		file_override = 'overriding' if self.file_override == 'OVERRIDE' else 'appending/linking in'
		export_mode = 'appended' if self.export_mode ==  'APPEND' else 'linked'
		if self.file_override == 'OVERRIDE':
			export_to_clean_file = ' Data will be exported to a clean file.' if self.export_to_clean_file else ' Data will be exported to your startup file.'
			
		else:
			export_to_clean_file = ''

		if self.source == 'OBJECTS':
			create_collection_hierarchy = ' The collection hierarchy of selected objects will be preserved.' if self.create_collection_hierarchy else f' Selected objects will be exported without its collection hierarchy.'
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
		_label_multiline(context=context, text=text, parent=box)

		if len(pack_external_data) or len(open_exported_blend):
			text = f'''Once exported, {pack_external_data} {open_exported_blend}'''
			_label_multiline(context=context, text=text, parent=box)

	def execute(self, context):
		ext = path.splitext(self.filepath)[1].lower()
		if ext != '.blend':
			self.filepath += '.blend'

		# Save to a temp folder if currnt file is dirty. Otherwise some objects will not be visible from the target file.
		if bpy.data.is_dirty:		
			self.tmpdir = tempfile.mkdtemp()
			self.current_file = path.join(
				self.tmpdir, path.basename(self.filepath))
			bpy.ops.wm.save_as_mainfile(
				'EXEC_DEFAULT', filepath=self.current_file, copy=True)
			saved_to_temp_folder = True
		else:
			self.current_file = bpy.data.filepath
			saved_to_temp_folder = False

		if not path.exists(self.filepath):
			self.file_override == 'OVERRIDE'

		if os.path.normpath(self.filepath) == os.path.normpath(self.current_file):
			self.report({'ERROR'}, "Destination file have to be different then source file")
			return {'CANCELLED'}


		self.selected_objects = [o.name for o in bpy.context.selected_objects]

		import_parameters = [	'--source_file', self.current_file,
								'--destination_file', self.filepath,
								'--source_data', self.source,
								'--file_override', self.file_override,
								'--export_mode', self.export_mode,
								'--export_to_clean_file', str(self.export_to_clean_file),
								'--pack_external_data', str(self.pack_external_data),
								'--source_scene_name', context.scene.name,
								'--source_object_list', *self.selected_objects,
								'--create_collection_hierarchy', str(self.create_collection_hierarchy),
								'--export_in_new_collection', str(self.export_in_new_collection),
								'--new_collection_name', self.new_collection_name,
								'--dependencies_in_dedicated_collection', str(self.dependencies_in_dedicated_collection),
								'--print_debug', str(self.print_debug)
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

		return {'FINISHED'}


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


classes = (TILA_OP_ExportAsBlend, TILA_OP_ExportAsBlendSaveCurrentFile)


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
