import bpy, subprocess
from os import path
from bpy_extras.io_utils import ImportHelper

bl_info = {
	"name" : "Export as Blend",
	"author" : "Tilapiatsu",
	"description" : "This addon allow you to export data to a new blend file, From selected Objects or a comlplete Scene.",
	"version": (1, 0, 0, 0),
	"blender" : (3, 1, 0),
	"location" : "",
	"warning" : "",
	"category" : "Import-Export"
}

class TILA_OP_ExportAsBlend(bpy.types.Operator, ImportHelper):
	bl_idname = "export_scene.tila_blend"
	bl_label = "Export as Blend"
	bl_options = {'REGISTER', 'INTERNAL'}
	bl_region_type = "UI"
 
	filter_glob: bpy.props.StringProperty(default="*.blend", options={'HIDDEN'})
	
	files : bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
	source : bpy.props.EnumProperty(items=[("SELECTED_OBJECTS", "Selected Objects", ""), ("CURRENT_SCENE", "Current Scene", "")])

	create_collection_hierarchy : bpy.props.BoolProperty(name='Create Collection Hierarchy',
                                                      	description='Each Objects will be exported in its collection hierarchy',
                                                       default=True)
	export_to_clean_scene : bpy.props.BoolProperty(	name='Export To Clean Scene',
                                                	description='If Enable the startup scene will be skipped and the data will be exported in a clean empty scene',
                                                 	default=True)
	relink_as_library : bpy.props.BoolProperty(	name='Relink as Library',
                                            	description='After export, the file is relink as a library in the current Scene',
                                             	default=False)

	def draw(self, context):
		layout = self.layout
		col = layout.column()
		col.label(text='Export Settings')
		col.prop(self, 'source')
		col.prop(self, 'export_to_clean_scene')
		col = layout.column()
		col.prop(self, 'create_collection_hierarchy')
		if self.source != "SELECTED_OBJECTS":
			col.enabled = False
		col = layout.column()
		# col.prop(self, 'relink_as_library')
	
	def execute(self,context):
		ext = path.splitext(self.filepath)[1].lower()
		if ext != '.blend':
			self.filepath += '.blend'
		
		self.selected_objects = context.selected_objects
		self.parent_collections = self.parent_lookup(context.scene.collection)
		self.root_collection = context.scene.collection
		self.collections_in_scene = [c.name for c in bpy.data.collections if bpy.context.scene.user_of_id(c)]
		self.feed_collection_hierarchy_from_selected_objects()
		# self.current_collection = context.collection

		command = self.generate_command(context)

		if self.export_to_clean_scene:
			subprocess.check_call([bpy.app.binary_path,
			'--background',
			path.join(path.dirname(path.realpath(__file__)), 'StartupClean', "StartupClean.blend"),
			'--debug-handlers',
			'--factory-startup',
			'--python-expr', command,
			])
		else:
			subprocess.check_call([bpy.app.binary_path,
			'--background',
			'--debug-handlers',
			'--factory-startup',
			'--python-expr', command,
			])

		#   Not Working Yet
		if self.relink_as_library:
			for o in self.selected_objects:
				for c in o.users_collection:
					if c.name in self.objects_collection_list:
						c.objects.unlink(bpy.data.objects[o.name])
      
				self.link_blend_file(self.filepath, 'Object', o.name)
			
				for c in self.objects_collection_hierarchy.values():
					for cc in c:
						bpy.data.collections[cc].objects.link(bpy.data.objects[o.name])
     
		return {'FINISHED'}
	
	def generate_command(self, context):
		# Base Command + define the link function
		command = '''import bpy, os
def link_blend_file(file_path, datablock_dir, data_name):
	filepath = os.path.join(file_path, datablock_dir, data_name)
	directory = os.path.join(file_path, datablock_dir)
	bpy.ops.wm.link(filepath = filepath, directory = directory, filename = data_name, link = False)
'''		
		if self.source == 'CURRENT_SCENE':
			command += f'''\nprint("Importing Scene {bpy.context.scene.name}")'''
			command += f'''\nlink_blend_file(file_path='{bpy.data.filepath}', datablock_dir = 'Scene', data_name='{bpy.context.scene.name}')'''
		elif self.source == 'SELECTED_OBJECTS':
			# Import Objects
			for o in self.selected_objects:
				command += f'''\nprint("Importing Object {o.name}")'''
				command += f'''\nlink_blend_file(file_path='{bpy.data.filepath}', datablock_dir = 'Object', data_name='{o.name}')'''
				if self.create_collection_hierarchy:
					command += f'''\nbpy.context.collection.objects.unlink(bpy.data.objects["{o.name}"])'''
		
			if self.create_collection_hierarchy:
			# Create Collection Hierarchy
				for c,p in self.parent_collections.items():
					if c not in self.objects_collection_list:
						continue
					for i,pp in enumerate(p):
						if pp not in self.objects_collection_list:
							continue
						
						command += f'''\nprint("Linking Collection {c} to {pp}")'''
						if i == 0:
							command += f'''\ncol = bpy.data.collections.new('{c}')'''

						if pp == self.root_collection.name:
							command += f'''\nbpy.context.scene.collection.children.link(bpy.data.collections["{c}"])'''
						else:
							command += f'''\nif "{pp}" not in bpy.data.collections:
	bpy.data.collections.new('{pp}')
bpy.data.collections["{pp}"].children.link(bpy.data.collections["{c}"])'''

				# Link Object to collections
				for o in self.selected_objects:
					for c in o.users_collection:
						if c.name in self.parent_collections.keys():
							command += f'''\nprint("Linking Object {o.name} to Collection {c.name}")'''
							command += f'''\nbpy.data.collections["{c.name}"].objects.link(bpy.data.objects["{o.name}"])'''
       
		command += f"\nbpy.ops.wm.save_as_mainfile('EXEC_DEFAULT',filepath='{self.filepath}')"
		return command
	
	def link_blend_file(self, file_path, datablock_dir, data_name):
		filepath = path.join(file_path, datablock_dir, data_name)
		directory = path.join(file_path, datablock_dir)
		bpy.ops.wm.link(filepath = filepath, directory = directory, filename = data_name, link = True)
  
	def feed_collection_hierarchy_from_selected_objects(self):
		'''Return all the necessary collection needed to create one item'''
		self.objects_collection_hierarchy = self.get_objects_collection_hierarchy(self.selected_objects)
		self.objects_collection_list = [bpy.context.scene.collection.name]
		for c in self.objects_collection_hierarchy.values():
			for cc in c:
				if cc not in self.objects_collection_list:
					self.objects_collection_list.append(cc)
	
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
				self.get_parent_collection_names(parent_collection, parent_names)
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
 



def menu_func_export(self, context):
	self.layout.operator(TILA_OP_ExportAsBlend.bl_idname, text="Export as Blend (.blend)")
	
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