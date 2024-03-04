"""
The assumption is that you are creating a stamp for the same bone on a duplicate of the same armature that is the parent of a different mesh. So the bone your transfering the stamp to should have the same name

SETUP
0) Pick the source and target armatures

GET WEIGHTS
1) get the weights for each vertex in a vertex groups for a single bone 
2) pick a central vertex in the vertex group to which all other vertices will translate/rotate in relation to 

TRANSFER TO NEW ARMATURE
3) estimate where the vertex group weights should go on the new mesh
4) create the ability to move weights all at the same time on the new mesh

"""
import bpy
import mathutils

#get mesh from armature
def get_mesh_from_armature(armature_name):
    armature = bpy.data.objects[armature_name]
    modifiers = [modifier for modifier in armature.modifiers if modifier.type == "ARMATURE"]
    mesh_object = modifiers[0].object
    if mesh_object and mesh_object.type == 'MESH':
        print("Mesh object associated with the armature:", mesh_object.name)
        return mesh_object


def get_3d_center(source_object):
    vertex_dict = {}
    # Get the mesh data
    mesh = source_object.data

    total = mathutils.Vector((0, 0, 0))
    count = 0
    # Iterate through all vertices
    for vertex in mesh.vertices:
        total += vertex.co
        count += 1

    center = total / count
    return center

def find_nearest_vertex(center, source_object)
    mesh = source_object.data
    min_distance = 1000000
    min_vertex = None
    for vertex in mesh.vertices:
        distance = calculate_distance(center, vertex.co)
        if distance < min_distance:
            min_distance = distance
            min_vertex = vertex
    return min_vertex


def calculate_distance(vertex1, vertex2):
    # Calculate the distance between the two points
    return (vertex2 - vertex1).length


def organize_vertex_group_info(mesh_object):
    vertex_group_dict = {}
    mesh = mesh_object.data
    #Iterate through all vertices
    for vertex in mesh.vertices:
        for group_index, weight in vertex.groups:
            vertex_group_dict[group_index] = vertex

    return vertex_group_dict

def estimate_target_vertex_group(source_armature_name):
    #void return, just transfer weights to target vertex group

    #source_armature = bpy.data.objects[source_armature_name]
    #vertex_groups = source_armature.vertex_groups

    source_object = get_mesh_from_armature(source_armature_name)
    vertex_group_dict = organize_vertex_group_info(source_object)
    center = get_3d_center(source_object)
    #this center vertex is going to move with your mouse
    center_vertex = find_nearest_vertex(center, source_object)
    #now you need to estimate where this center vertex would be on the target mesh
    #get bone name
    #get 3d cor of bone center
    # calculate distance between bone and center vertex
    # find the vertex on the target mesh that best matches up with that distance
    # map the source weights to the target mesh, centering on that newfound center vertex







            










