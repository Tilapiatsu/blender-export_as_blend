import bpy
from .logger import Logger


class ObjectDependencies():
	compatible_modifier_type = (bpy.types.Object,)

	def __init__(self, obj, print_message=False):
		self.log = Logger(addon_name='Object Dependencies', print=print_message)
		self.object = obj
		self._dependencies = None
		self.dependency_objects = []

	@property
	def data_type(self):
		return {'modifiers': self.object.modifiers}

	@property
	def dependencies(self):
		if self._dependencies is None:
			self._dependencies = {'modifiers': {}}
			for m in self.object.modifiers:
				for p in dir(m):
					a = getattr(m, p)
					if isinstance(a, self.compatible_modifier_type):
						if m.name not in self._dependencies['modifiers'].keys():
							self._dependencies['modifiers'][m.name] = {p: a.name}
						else:
							self._dependencies['modifiers'][m.name][p] = a.name

						if a.name not in self.dependency_objects:
							self.dependency_objects.append(a.name)

		return self._dependencies

	@dependencies.setter
	def depenencies(self, value):
		self._dependencies = value

	def resolve_dependencies(self, object_manager):
		for t in self.dependencies.keys():
			for n in self.dependencies[t].keys():
				tt = self.data_type[t]
				m = self.data_type[t][n]
				if m is None:
					continue
				for p in self.dependencies[t][n].keys():
					obj = object_manager.get_element_by_incoming_name(
						self.dependencies[t][n][p])
					obj2 = object_manager.get_element(self.dependencies[t][n][p])
					self.log.info(
						f'Resolving dependencies, setting attr of {m.name}.{p} to {obj.name} {obj2.name}')
					setattr(m, p, object_manager.get_element_by_incoming_name(
						self.dependencies[t][n][p]).object)
