import bpy, re
from .logger import Logger

class Manager:
	def __init__(self, name, bpy_data, element_class, print_message=False):
		self.log = Logger(addon_name=name, print=print_message)
		self.print_message = print_message
		self.element_list = []
		self.bpy_data = bpy_data
		self.element_class = element_class
		self.element_correspondance = {}

		# init incoming name
		for i, e in enumerate(bpy_data):
			if bpy_data[i].library != None and e.name in self.element_correspondance.values():
				continue
			self.unique_name(i, e.name, self.element_correspondance)

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
				self.log.error(f'Value Error : {e.strerror}')

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

	def update_element_name(self, elem, name):
		if elem in self.element_correspondance.keys():
			self.log.info(f'Updating element "{elem.name}" name to "{name}"')
			self.element_correspondance[elem] = name
		else:
			self.register_element_correspondance(elem)

	def register_element_correspondance(self, elem):
		if elem not in self.element_correspondance.keys():
			self.element_correspondance[elem] = elem.name

	# a modified version of bpy_extras.io_utils
	def unique_name(self, key, name, name_dict, name_max=-1, clean_func=None, sep=".", register=True):
		"""
		Helper function for storing unique names which may have special characters
		stripped and restricted to a maximum length.

		:arg key: unique item this name belongs to, name_dict[key] will be reused
		when available.
		This can be the object, mesh, material, etc instance itself.
		:type key: any hashable object associated with the *name*.
		:arg name: The name used to create a unique value in *name_dict*.
		:type name: string
		:arg name_dict: This is used to cache namespace to ensure no collisions
		occur, this should be an empty dict initially and only modified by this
		function.
		:type name_dict: dict
		:arg clean_func: Function to call on *name* before creating a unique value.
		:type clean_func: function
		:arg sep: Separator to use when between the name and a number when a
		duplicate name is found.
		:type sep: string
		"""
		name_new = name_dict.get(key)
		if name_new is None:
			count = 1
			has_number = False
			name_dict_values = list(name_dict.values())

			if clean_func is None:
				name_new = name_new_orig = name
			else:
				name_new, has_number = clean_func(name)
				name_new_orig = name_new
			if has_number or name_new in name_dict_values:
				if name_max == -1:
					while name_new in name_dict_values:
						name_new = "%s%s%03d" % (
							name_new_orig,
							sep,
							count,
						)
						count += 1
				else:
					name_new = name_new[:name_max]
					while name_new in name_dict_values:
						count_str = "%03d" % count
						name_new = "%.*s%s%s" % (
							name_max - (len(count_str) + 1),
							name_new_orig,
							sep,
							count_str,
						)
						count += 1

			if register:
				name_dict[key] = name_new

		return name_new


class ObjectManager(Manager):
	def __init__(self, bpy_data, element_class, print_message=False):
		super(ObjectManager, self).__init__(
			'Object Manager', bpy_data, element_class, print_message)

	def add_element(self, obj, register=False, append_to_list=True):
		if register:
			self.register_element_correspondance(obj)

		elem = self.element_class(
			manager=self, obj=obj, print_message=self.print_message)
		if append_to_list:
			if elem not in self.element_list:
				self.element_list.append(elem)

		return elem

	def parent(self, parent, child, keep_transform=False):
		self.log.info(f'Parent "{child.name}" object to "{parent.name}" object')
		child.object.parent = parent.object
		if keep_transform:
			child.object.matrix_parent_inverse = parent.object.matrix_world.inverted()

	def conform_element(self, element):
		if isinstance(element, self.element_class):
			return element
		elif isinstance(element, self.bpy_type):
			return self.element_class(manager=self, obj=element, print_message=self.print_message)
		elif isinstance(element, str):
			return self.element_class(manager=self, obj=self.bpy.data[element.name], print_message=self.print_message)
		else:
			try:
				ex = ValueError()
				ex.strerror = f"Unrecognise type for Collection {type(element)}"
				raise ex
			except ValueError as e:
				self.log.error(f'Value Error : {e.strerror}')

	def get_element(self, name):
		valid_elements = {
			e: n for e, n in self.element_correspondance.items() if not isinstance(e, int)}
		for e, n in valid_elements.items():
			if n == name and not isinstance(e, int):
				self.log.info(f'Element found : {e}')
				return self.conform_element(e)

		return self.add_element(self.bpy_data[name], register=True)


class CollectionManager(Manager):
	def __init__(self, bpy_data, element_class, print_message=False):
		super(CollectionManager, self).__init__(
			'Collection Manager', bpy_data, element_class, print_message)

	def get_element_by_incoming_name(self, name):
		self.log.info(f'Get element by incomming name : "{name}"')
		e = [elem for elem in self.element_list if elem.incoming_name == name]
		if len(e):
			self.log.info(f'Element Found : "{e[0].name}"')
			return e[0]
		else:
			self.log.info(f'Element NOT Found : Adding new Element')
			return self.add_element(name, register=True)

	def add_element(self, name, append_to_list=True, register=False):
		new_name = self.unique_name(name, name, self.element_correspondance,
		                            clean_func=unique_name_clean_func, register=register)
		if new_name != name:
			self.log.info(f'New name for "{name}" is "{new_name}"')

		elem = self.element_class(manager=self, string=name,
		                          print_message=self.print_message)
		elem.name = new_name
		if append_to_list:
			if elem not in self.element_list:
				self.element_list.append(elem)
		return elem

	def conform_element(self, element):
		if isinstance(element, self.element_class):
			return element
		elif isinstance(element, self.bpy_type):
			return self.element_class(manager=self, string=element.name, print_message=self.print_message)
		elif isinstance(element, str):
			return self.element_class(manager=self, string=element, print_message=self.print_message)
		else:
			try:
				ex = ValueError()
				ex.strerror = f"Unrecognise type for Collection {type(element)}"
				raise ex
			except ValueError as e:
				self.log.error(f'Value Error : {e.strerror}')

	def get_element(self, name):
		valid_elements = {
			e: n for e, n in self.element_correspondance.items() if not isinstance(e, int)}
		for e, n in valid_elements.items():
			if n == name and not isinstance(e, int):
				self.log.info(f'Element found : {e}')
				return self.conform_element(e)

		return self.add_element(name, register=True)

	# Linking and Unlinking Methods
	def create_collection(self, collection_name):
		if collection_name not in self.element_correspondance.values():
			coll = self.add_element(collection_name)
		else:
			coll = self.get_element(collection_name)
		self.log.info(f'Create new collection : "{coll.name}"')
		self.bpy_data.new(coll.name)
		self.register_element_correspondance(self.bpy_data[coll.name])
		return coll

	def link_object_to_collection(self, object, collection):
		collection = self.conform_element(collection).collection
		if object.name in collection.objects:
			return
		self.log.info(
			f'Link object "{object.name}" to collection "{collection.name}"')
		collection.objects.link(object)

	def unlink_object_from_collection(self, object, collection):
		collection = self.conform_element(collection).collection
		if object.name not in collection.objects:
			return
		self.log.info(
			f'Unlink object "{object.name}" from collection "{collection.name}"')
		collection.objects.unlink(object)

	def move_object_to_collection(self, object, from_collection, to_collection):
		from_collection = self.conform_element(from_collection).collection
		to_collection = self.conform_element(to_collection).collection
		self.log.info(
			f'Move object "{object.name}" from collection "{from_collection.name}" to "{to_collection.name}"')
		from_collection.objects.unlink(object)
		to_collection.objects.link(object)

	def link_collection_to_collection(self, child_collection, parent_collection):
		child_collection = self.conform_element(child_collection).collection
		parent_collection = self.conform_element(parent_collection).collection
		self.log.info(
			f'Link Collection "{child_collection.name}" to collection "{parent_collection.name}"')
		parent_collection.children.link(child_collection)

	def unlink_collection_from_collection(self, child_collection, parent_collection):
		child_collection = self.conform_element(child_collection).collection
		parent_collection = self.conform_element(parent_collection).collection
		self.log.info(
			f'Unink Collection "{child_collection.name}" from collection "{parent_collection.name}"')
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
		layerColl = self.get_layer_collection_by_name(
			layer_collection, collection_name)
		bpy.context.view_layer.active_layer_collection = layerColl


def unique_name_clean_func(name):
	word_pattern = re.compile(r'(\.[0-9]{3})$', re.IGNORECASE)
	name_iter = word_pattern.finditer(name)
	name_iter_match = [w.group(1) for w in name_iter]

	if len(name_iter_match) and name_iter_match[0] is not None:
		return name.replace(name_iter_match[0], ''), True
	else:
		return name, False
