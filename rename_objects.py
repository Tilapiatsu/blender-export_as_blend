import argparse, sys, bpy, os


SCRIPT_DIR = os.path.join(os.path.dirname(
	os.path.abspath(__file__)), "eab_utils")
sys.path.append(os.path.dirname(SCRIPT_DIR))

from eab_utils.logger import Logger


class RenameObjects():
	def __init__(self, argv):
		self.parse_argsv(argv[argv.index("--") + 1:])
		self.log = Logger(addon_name='Rename Objects', print=self.print_debug)

	def parse_argsv(self, argv):
		parser = argparse.ArgumentParser(description='This command allow you rename in a blend file.')

		name_collision_group = parser.add_argument_group('Name Collsion')
		name_collision_group.add_argument('-i', '--original_names', nargs='+',
                                    help='Each object matching "original_names" names will be renamed to "new_name". the index of each list will be used to match element together so both list need to have the same length',
                                    required=True)
		name_collision_group.add_argument('-x', '--new_names', nargs='+',
                                    help='Each object matching "original_names" names will be renamed to "new_name". the index of each list will be used to match element together so both list need to have the same length',
                                    required=True)

		debug_group = parser.add_argument_group('Collection Hierarchy')
		debug_group.add_argument('-P', '--print_debug', default=False,
                           help='Print debug message in console',
                           required=False)

		args = parser.parse_args(argv)

		original_names = args.original_names
		new_names = args.new_names

		if len(original_names) != len(new_names):
			self.log.info('original_names and new_names need to have the same length')
			self.log.info(f'new_names = {new_names}')
			self.log.info(f'original_names = {original_names}')
			sys.exit()

		self.name_correspondance = {original_names[i]: new_names[i] for i in range(len(original_names))}
		self.print_debug = eval(args.print_debug)

	def rename_objects(self):
		for name, new_name in self.name_correspondance.items():
			if name not in bpy.data.objects:
				self.log.info(f'Object "{name}" doesn\'t exist in current file. Skipping renaming')
				continue
			
			self.log.info(f'Renaming object "{name}" to "{new_name}"')
			bpy.data.objects[name].name = new_name
		
		# Save File
		bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT')
		

if __name__ == "__main__":
	RO = RenameObjects(sys.argv)
	RO.rename_objects()
