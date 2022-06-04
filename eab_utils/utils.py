import bpy
import shutil
import os
import stat
from os import path

def get_object_children(obj):
	children = []
	parents = [o for o in bpy.data.objects]
	for ob in parents:
		if ob.parent == obj:
			children.append(ob.name)
	
	return children


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
