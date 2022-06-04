import bpy
from .logger import Logger

class Element:
	def __init__(self, manager, string):
		self._string = {'incoming': string, 'local': string}
		self.manager = manager

	@property
	def incoming_name(self):
		return self._string['incoming']

	@property
	def name(self):
		# self.fix_local_element_name()
		return self._string['local']

	@name.setter
	def name(self, value):
		print(f'Setting local name from "{self._string["local"]}" to "{value}"')
		self._string['local'] = value


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
				self.log.error(f'Value Error : {e.strerror}')
		else:
			return self.manager.bpy_data[self.name]


class Object(Element):
	def __init__(self, manager, obj, print_message=False):
		super(Object, self).__init__(manager, obj.name)
		self.log = Logger(addon_name='Object', print=print_message)
		self._object = obj

	@property
	def object(self):
		if self._object is None or self.name not in self.manager.bpy_data:
			self.log.error(f'"{self.name}" Object not in current file')
			try:
				ex = ValueError()
				ex.strerror = f'object "{self.name}" not in {self.manager.bpy_data}'
				raise ex
			except ValueError as e:
				self.log.error(f'Value Error : {e.strerror}')
		elif self._object is not None:
			return self._object

	@property
	def name(self):
		self.fix_local_element_name()
		return self._string['local']

	@name.setter
	def name(self, value):
		self.log.info(
			f'Setting local name from "{self._string["local"]}" to "{value}"')
		self._string['local'] = value

	def fix_local_element_name(self):
		self._string['local'] = self._object.name
