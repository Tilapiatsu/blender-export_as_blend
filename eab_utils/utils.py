import bpy

def get_object_children(obj):
	children = []
	parents = [o for o in bpy.data.objects]
	for ob in parents:
		if ob.parent == obj:
			children.append(ob.name)
	
	return children
