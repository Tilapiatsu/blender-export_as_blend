import argparse, sys, bpy


class RenameObjects():
	def __init__(self, argv):
		self.parse_argsv(argv[argv.index("--") + 1:])

	def parse_argsv(self, argv):
		parser = argparse.ArgumentParser(description='This command allow you rename in a blend file.')

		name_collision_group = parser.add_argument_group('Name Collsion')
		name_collision_group.add_argument('-i', '--original_names', nargs='+',
                                    help='Each object matching "original_names" names will be renamed to "new_name". the index of each list will be used to match element together so both list need to have the same length',
                                    required=True)
		name_collision_group.add_argument('-x', '--new_names', nargs='+',
                                    help='Each object matching "original_names" names will be renamed to "new_name". the index of each list will be used to match element together so both list need to have the same length',
                                    required=True)

		args = parser.parse_args(argv)

		original_names = args.original_names
		new_names = args.new_names

		if len(original_names) != len(new_names):
			print('original_names and new_names need to have the same length')
			print(f'new_names = {new_names}')
			print(f'original_names = {original_names}')
			sys.exit()
		else:
			self.name_correspondance = {original_names[i]: new_names[i] for i in range(len(original_names))}

	def rename_objects(self):
		for name, new_name in self.name_correspondance.items():
			if name not in bpy.data.objects:
				print(f'Object "{name}" doesn\'t exist in current file. Skipping renaming')
				continue
			
			print(f'Renaming object "{name}" to "{new_name}"')
			bpy.data.objects[name].name = new_name
		
		# Save File
		bpy.ops.wm.save_as_mainfile('EXEC_DEFAULT')
		

if __name__ == "__main__":
	RO = RenameObjects(sys.argv)
	RO.rename_objects()
