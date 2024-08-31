import bpy
import mathutils
import site
import pip

#pip.main(['install', 'dask', '--target', site.USER_SITE])
import bpy
import bmesh
from mathutils.bvhtree import BVHTree
from mathutils import Vector
from collections import defaultdict, deque
import sys


#1) get the weights for each vertex in a vertex groups for a single bone 
def is_in_vertex_group(vert_index, vert_group):
      return vert_group.weight(vert_index) > 0

def find_center(vertex_group_name, mesh):
    context = bpy.context
    ob = mesh
    bpy.ops.object.empty_add(location=(0, 0, 0))
    mt = context.object
    mt.name = f"{ob.name}_{vertex_group_name}"
    cl = mt.constraints.new('COPY_LOCATION')
    cl.target = ob
    cl.subtarget = vertex_group_name
    #To go to any next step that requires the empties to be at the constrained locations throw in a scene update to ensure matrices etc are up to date.
    dg = context.evaluated_depsgraph_get()
    dg.update()
    #get global location
    loc = mt.matrix_world.translation # global location of emtpy
    # remove the mt
    bpy.data.objects.remove(mt)
    return loc


def distance_from_center(center, vertex_island_dict, source_mesh):
    distance_dict = {}
    for v in vertex_island_dict:
        vector = (source_mesh.matrix_world @ v.co - center)
        #distance = vector.length
        distance = vector
        weight = vertex_island_dict[v]
        distance_dict[v] = {"distance": distance, "weight": weight}
    return distance_dict


def organize_vertex_groups(source_mesh_name):
    vertex_groups = get_vertex_groups(source_mesh_name)
    vertex_group_dict = {}
    source_obj = bpy.data.objects[source_mesh_name]
    mesh_data = bpy.data.objects[source_mesh_name].data

    #copy vertices
    bm = bmesh.new()
    bm.from_mesh(mesh_data)

    # Loop through all vertices to get all non zero weights and their vertex coordinates
    #for v in mesh_data.vertices:
    for v in bm.verts:
        v.co = source_obj.matrix_world @ v.co

        # Calculate the direction from the vertex to the object's origin
        to_origin = (source_obj.location - source_obj.matrix_world @ v.co).normalized()

        if v.normal.dot(to_origin) > 0:  # The dot product > 0 means the normal is pointing outward
            # Flip the normal by reversing the face normals associated with the vertex
            for face in v.link_faces:
                face.normal_flip()

        for source_vertex_group in vertex_groups:
            try:
                if is_in_vertex_group(v.index, source_vertex_group):
                    # Assign the weight to the target group
                    weight = source_vertex_group.weight(v.index)
                    if source_vertex_group.name in vertex_group_dict:
                        vertex_group_dict[source_vertex_group.name][v] = weight
                    else:
                        vertex_group_dict[source_vertex_group.name] = {}
                        vertex_group_dict[source_vertex_group.name][v] = weight
            except RuntimeError as e:
                #Error: Vertex not in group
                continue
    return vertex_group_dict

# this function is meant to be used in a for loop, looping through all of the bones/vertex groups on an armature/meshG
# for mods, the bone names should be the same for both armatures
def remap_vertex_groups(vertex_group_dictionaries, source_armature_name, target_armature_name, source_mesh_name, target_mesh_name, source_vertex_group_name, empty_name):
    target_mesh = bpy.data.objects[target_mesh_name]
    source_mesh = bpy.data.objects[source_mesh_name]
    empty_obj = bpy.data.objects[empty_name]

    #for source_vertex_group_name in vertex_group_dictionaries:
    center_point = find_center(source_vertex_group_name, source_mesh)

    source_selected_vertices = vertex_group_dictionaries[source_vertex_group_name]
    distance_dict = distance_from_center(center_point, source_selected_vertices, source_mesh)
    #now you can make the newly created empty as your center and base everything off of that 
   
    if not source_mesh or not target_mesh:
        print("Source or target object not found.")
        sys.exit()

    # Switch to object mode to avoid issues
    bpy.ops.object.mode_set(mode='OBJECT')

    # Create a KDTree for the target mesh (faster ray casting)
    bm = bpy.context.evaluated_depsgraph_get()
    kd_tree = mathutils.bvhtree.BVHTree.FromObject(target_mesh, bm)

    vertex_group_dictionaries = organize_vertex_groups(source_mesh_name)

    selected_vertex_group = vertex_group_dictionaries[source_vertex_group_name]

    # Loop through each vertex in the source mesh
    for vertex in selected_vertex_group:

        #get new positions based on distance_dict
        metadata = distance_dict[vertex]
        distance = metadata["distance"]
        weight = metadata["weight"]
        target_estimate = empty_obj.location + distance

        # Ray cast to find the intersection point on the target mesh
        hit_location, hit_normal, face_index, distance = kd_tree.ray_cast(target_estimate, vertex.normal)
        
        if hit_location:
            # you want to get the closest 
            #world_hit_location = target_obj.matrix_world.inverted() @ hit_location
            world_hit_location = target_mesh.matrix_world @ hit_location
            nearest = kd_tree.find_nearest(world_hit_location)

            target_vertex_group = target_mesh.vertex_groups.get(source_vertex_group_name)
            target_vertex_group.add([nearest.index], weight,'REPLACE')


def mark_location(vertex):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=vertex)

def get_vertex_groups(mesh_name):
    vertex_groups = bpy.data.objects[mesh_name].vertex_groups
    return vertex_groups

#source_mesh_name = "source"
#target_mesh_name = "target"
#source_armature_name = "source_arm"
#target_armature_name = "target_arm"

#source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
#target_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head.001"
#source_armature_name = "Root.002"
#target_armature_name = "Root.001"

#get the source and target 
source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
target_mesh_name = "Cube"
source_armature_name = "Root.002"
target_armature_name = "Root.001"
source_vertex_group_name = "C_nose_Top"
empty_name = "Empty"

vertex_group_dictionaries = organize_vertex_groups(source_mesh_name)
remap_vertex_groups(vertex_group_dictionaries, source_armature_name, target_armature_name, source_mesh_name, target_mesh_name, source_vertex_group_name, empty_name)
