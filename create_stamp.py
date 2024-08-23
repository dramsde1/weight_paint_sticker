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


#1) get the weights for each vertex in a vertex groups for a single bone 
def estimate_target_island(distance_dict, target_mesh, target_vertex_group_center, vertex_group_name):
    target_mesh_data = target_mesh.data
    vertex_group = target_mesh.vertex_groups.get(vertex_group_name)
   
    size = len(target_mesh_data.vertices)
    kd = mathutils.kdtree.KDTree(size)
    for i, v in enumerate(target_mesh_data.vertices):
        kd.insert(v.co, i)
    kd.balance()

    # Loop through all vertices
    for d in distance_dict:
        #initialize min distance and min vertex
        #get the true location of the matching target vertex
        #center - v = dist
        #center - dist = v
        target_estimate = target_vertex_group_center - d
        # Find the closest point to the center
        co, index, dist = kd.find(target_estimate)
        weight = distance_dict[d]
        vertex_group.add([index], weight, 'REPLACE')
         

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


def distance_from_center(center, vertex_island_dict):
    distance_dict = {}
    for v in vertex_island_dict:
        dist = center - v.co
        weight = vertex_island_dict[v]
        distance_dict[dist.freeze()] = weight
    return distance_dict

def distance_between_center_and_bone(source_bone, source_armature, center_point):
    world_head_location = source_armature.matrix_world @ source_bone.head
    vector = (world_head_location - center_point)
    distance = vector.length
    direction = vector.normalized()
    return distance, direction

def find_target_vertex_group_center(distance, direction, target_armature, target_bone, target_mesh):
    min_distance = float('inf')
    nearest_vertex = None
    world_head_location = target_armature.matrix_world @ target_bone.head
  
    size = len(target_mesh.data.vertices)
    kd = mathutils.kdtree.KDTree(size)
    for i, v in enumerate(target_mesh.data.vertices):
        kd.insert(v.co, i)
    kd.balance()

    estimated_vertex = world_head_location - (direction * distance)

    co, index, dist = kd.find(estimated_vertex)
    nearest_vertex = target_mesh.data.vertices[index] 
   
    return nearest_vertex


def organize_vertex_groups(source_mesh_name):
    vertex_groups = get_vertex_groups(source_mesh_name)
    vertex_group_dict = {}
    mesh_data = bpy.data.objects[source_mesh_name].data
    # Loop through all vertices to get all non zero weights and their vertex coordinates
    for v in mesh_data.vertices:
        for vg in vertex_groups:
            source_vertex_group = vg
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
def remap_vertex_groups(vertex_group_dictionaries, source_armature_name, target_armature_name, source_mesh_name, target_mesh_name):

    target_mesh = bpy.data.objects[target_mesh_name]
    source_mesh = bpy.data.objects[source_mesh_name]
    source_armature = bpy.data.objects[source_armature_name]
    target_armature = bpy.data.objects[target_armature_name]

    for source_vertex_group_name in vertex_group_dictionaries:
        source_bone = source_armature.pose.bones.get(source_vertex_group_name)
        target_bone = target_armature.pose.bones.get(source_vertex_group_name)
        center_point = find_center(source_vertex_group_name, source_mesh)
        #distance between source bone and center of vertex group
        distance_from_bone, direction_to_target_center = distance_between_center_and_bone(source_bone, source_armature, center_point)
        #get the location of the center of the supposed target vertex group using the above distance from bone
        target_vertex_group_center = find_target_vertex_group_center(distance_from_bone, direction_to_target_center, target_armature, target_bone, target_mesh)
        vertex_island = vertex_group_dictionaries[source_vertex_group_name]

        distance_dict = distance_from_center(center_point, vertex_island)
        estimate_target_island(distance_dict, target_mesh, target_vertex_group_center, source_vertex_group_name)
        print(f"source vertex group transferred to target mesh")

    print(f"All source vertex groups transferred to target mesh")


def get_vertex_groups(mesh_name):
    vertex_groups = bpy.data.objects[mesh_name].vertex_groups
    return vertex_groups

def check_empty_groups(mesh_name):
    vertex_groups = bpy.data.objects[mesh_name].vertex_groups

#source_mesh_name = "source"
#target_mesh_name = "target"
#source_armature_name = "source_arm"
#target_armature_name = "target_arm"

#source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
#target_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head.001"
#source_armature_name = "Root.002"
#target_armature_name = "Root.001"

source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
target_mesh_name = "Cube"
source_armature_name = "Root.002"
target_armature_name = "Root.001"


vertex_group_dictionaries = organize_vertex_groups(source_mesh_name)
remap_vertex_groups(vertex_group_dictionaries, source_armature_name, target_armature_name, source_mesh_name, target_mesh_name)




