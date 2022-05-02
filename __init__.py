import bpy, subprocess
from os import path
from bpy_extras.io_utils import ImportHelper

bl_info = {
	"name" : "Export as Blend",
	"author" : "Tilapiatsu",
	"description" : "This addon allow you to export data to a new blend file, from selected Objects or a comlplete Scene.",
	"version": (1, 0, 0, 0),
	"blender" : (3, 1, 0),
	"location" : "",
	"warning" : "",
	"category" : "Import-Export"
}

# Todo : 
#	- Need to check the shared Data before importing, and relink and clean if shared
class TILA_OP_ExportAsBlend(bpy.types.Operator, ImportHelper):
	bl_idname = "export_scene.tila_blend"
	bl_label = "Export as Blend"
	bl_options = {'REGISTER', 'INTERNAL'}
	bl_region_type = "UI"
 
	filter_glob: bpy.props.StringProperty(default="*.blend", options={'HIDDEN'})
	
	files : bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
	source : bpy.props.EnumProperty(items=[("SELECTED_OBJECTS", "Selected Objects", ""), ("CURRENT_SCENE", "Current Scene", "")])
	
	mode : bpy.props.EnumProperty(items=[("APPEND", "Append", ""), ("LINK", "Link", "")])

	create_collection_hierarchy : bpy.props.BoolProperty(name='Create Collection Hierarchy',
                                                      	description='Each Objects will be exported in its respective collection hierarchy from the source Blend file. Otherwise all Objects will be exported in the default collection',
                                                       default=True)
	export_to_clean_scene : bpy.props.BoolProperty(	name='Export To Clean File',
                                                	description='If enable the startup file will be skipped and the data will be exported in a clean empty file',
                                                 	default=True)
	export_dependencies_in_dedicated_collection : bpy.props.BoolProperty(name='Export dependencies in dedicated collection',
                                            	description='Each object dependencies are put in a dedicated collection named "Dependencies". If unchecked, each dependencies will be placed their respective collection from the source blend file',
                                             	default=False)
	pack_external_data : bpy.props.BoolProperty(	name='Pack External Data',
                                            	description='All data exported will be packed into the blend file, to avoid external files dependencies. It would increase drastically the size of the exported file and saving time',
                                             	default=False)
	open_exported_blend : bpy.props.BoolProperty(	name='Open Exported Blend',
                                            	description='The Exported blend file will be opened after export',
                                             	default=False)
	# relink_as_library : bpy.props.BoolProperty(	name='Relink as Library',
    #                                         	description='After export, the file is relink as a library in the current Scene',
    #                                          	default=False)

	def draw(self, context):
		layout = self.layout
		col = layout.column()
		col.label(text='Export Settings')
		col.prop(self, 'source')
		col.prop(self, 'mode')
		if self.mode == "APPEND":
			col.prop(self, 'pack_external_data')
		col.prop(self, 'export_to_clean_file')
  
		if self.source == "SELECTED_OBJECTS":
			col.prop(self, 'create_collection_hierarchy')

		if self.source == "SELECTED_OBJECTS":
			col.prop(self, 'export_dependencies_in_dedicated_collection')

		col.prop(self, 'open_exported_blend')
		# col.prop(self, 'relink_as_library')
	
	@property
	def is_linked(self):
		return self.mode == "LINK"
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
		# print(command)
		if self.export_to_clean_file:
			subprocess.check_call([bpy.app.binary_path,
			'--background',
			path.join(path.dirname(path.realpath(__file__)), 'StartupClean', "StartupClean.blend"),
			'--factory-startup',
			'--python-expr', command,
			])
		else:
			subprocess.check_call([bpy.app.binary_path,
			'--background',
			'--factory-startup',
			'--python-expr', command,
			])
	

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
		return {'FINISHED'}
	
	def generate_command(self, context):
		# Base Command and define the link function
		command = '''import bpy, os
initial_count = len(bpy.data.objects)
'''		
		if self.source == 'CURRENT_SCENE':
			command += f'\nprint("Importing Scene {context.scene.name}")'
			command += f'''\nfilepath = os.path.join(r'{bpy.data.filepath}', 'Scene', '{context.scene.name}')
directory = os.path.join(r'{bpy.data.filepath}', 'Scene')
bpy.ops.wm.append(filepath = filepath, directory = directory, filename = "{context.scene.name}"'''
		elif self.source == 'SELECTED_OBJECTS':
			# Import Objects
			command += f'\nprint("Importing Objects")'
			command += f'''\nfilepath = os.path.join(r'{bpy.data.filepath}', 'Object', '{self.selected_objects[0].name}')
directory = os.path.join(r'{bpy.data.filepath}', 'Object')
bpy.ops.wm.link(filepath = filepath, directory = directory, filename = "{self.selected_objects[0].name}", link = {self.is_linked}'''
			if len(self.selected_objects) > 1:
				command += f', files=['
				for i,o in enumerate(self.selected_objects):
					command += '{'
					command += f'"name":"{o.name}", "name":"{o.name}"'
					if i < len(self.selected_objects)-1:
						command += '},'
					else:
						command += '}]'
				command += ')'	
			else:
				command += ')'	
   
			# Create Collection Hierarchy
			if self.create_collection_hierarchy:
				for o in self.selected_objects:
					command += f'''\nbpy.context.collection.objects.unlink(bpy.data.objects["{o.name}"])'''
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

    		# Link Dependencies in a dedicated collection
			if self.export_dependencies_in_dedicated_collection and self.mode != "LINK":
				command += f'''\nif {len(self.selected_objects)} < len(bpy.data.objects) - initial_count:
	bpy.data.collections.new('Dependencies')
	bpy.context.scene.collection.children.link(bpy.data.collections["Dependencies"])
	for o in bpy.data.objects:
		if o.name in {self.get_object_list_name(self.selected_objects)}:
			continue
		if o.name not in bpy.context.collection.objects:
			continue
   
		print("Linking Object" + o.name + "to Dependencies Collection ")
		bpy.context.collection.objects.unlink(bpy.data.objects[o.name])
		bpy.data.collections["Dependencies"].objects.link(bpy.data.objects[o.name])
'''			
			# Link Dependencies in its respective collection from source blend file
			elif not self.export_dependencies_in_dedicated_collection and self.create_collection_hierarchy:
				command += f'''\nif {len(self.selected_objects)} < len(bpy.data.objects) - initial_count:
	for o in bpy.data.objects:
		if o.name in {self.get_object_list_name(self.selected_objects)}:
			continue
		
		all_collection_hierarchy = {self.get_all_objects_collection_hierarchy_as_string()}

		for obj,h in all_collection_hierarchy.items():
			if obj != o.name:
				continue
			if obj not in bpy.context.collection.objects:
				continue
    
			for hh in h:
				hierarchy = list(reversed(hh))
				for i,c in enumerate(hierarchy):
					if i == 0:
						if c not in bpy.data.collections:
							bpy.data.collections.new(c)
							bpy.context.scene.collection.children.link(bpy.data.collections[c])
						if c not in bpy.context.collection.children:
							bpy.context.scene.collection.children.link(bpy.data.collections[c])
					else:
						if c not in bpy.data.collections:
							bpy.data.collections.new(c)
						
						if c not in bpy.data.collections[hierarchy[i-1]].children:
							bpy.data.collections[hierarchy[i-1]].children.link(bpy.data.collections[c])
				else:
					print("Linking dependency Object " + o.name + " to Collection " +  c)
					bpy.context.collection.objects.unlink(bpy.data.objects[o.name])
					bpy.data.collections[hierarchy[len(hierarchy)-1]].objects.link(bpy.data.objects[o.name])
'''		
		if self.pack_external_data and self.mode == 'APPEND':
			command += '''\ntry:
	bpy.ops.file.pack_all()
except RuntimeError as e:
	print("Cannot pack data or data does not exist on drive.  " + e)'''
		command += f"\nbpy.ops.wm.save_as_mainfile('EXEC_DEFAULT',filepath=r'{self.filepath}')"
		return command
	
	def get_object_list_name(self, object_list):
		string_names = '['
		for i,o in enumerate(object_list):
			string_names += f'"{o.name}"'
			if i < len(object_list)-1:
				string_names += f', '
    
		string_names += ']'
		return string_names

	def get_list_as_string(self, l):
		string_names = '['
		for i,o in enumerate(l):
			string_names += f'"{o}"'
			if i < len(l)-1:
				string_names += f', '
    
		string_names += ']'
		return string_names

	def get_all_objects_collection_hierarchy_as_string(self):
		string_dict = '{'
		i = 0
		for o,p in self.all_objects_collection_hierarchy.items():
			parent = '['
			for j,pp in enumerate(p):
				parent += self.get_list_as_string(pp)
				# parent += f'"{pp}"'
				if j < len(p) -1:
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
		bpy.ops.wm.link(filepath = filepath, directory = directory, filename = data_name, link = True)
  
	def feed_collection_hierarchy_from_selected_objects(self):
		self.objects_collection_hierarchy = self.get_objects_collection_hierarchy(self.selected_objects)
		self.objects_collection_list = [bpy.context.scene.collection.name]
		for c in self.objects_collection_hierarchy.values():
			for cc in c:
				if cc not in self.objects_collection_list:
					self.objects_collection_list.append(cc)
		
		self.object_data_dependencies = {}
		for o in self.selected_objects:
			if o.data is None:
				continue
			if o.data.name not in self.object_data_dependencies.keys():
				self.object_data_dependencies[o.data.name] = [o.name]
			else:
				self.object_data_dependencies[o.data.name].append(o.name)
    
		self.all_objects_collection_hierarchy = {}
		for o in bpy.data.objects:
			hierarchies = []
			for c in o.users_collection:
				coll = []
				self.get_parent_collection_names(c, coll)
				hierarchies.append(coll)
			self.all_objects_collection_hierarchy[o.name] = hierarchies
    	
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