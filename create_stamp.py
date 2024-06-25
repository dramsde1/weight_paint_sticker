import bpy
import mathutils
import site
import pip

#pip.main(['install', 'dask', '--target', site.USER_SITE])
import bpy
import bmesh
from mathutils.bvhtree import BVHTree
from mathutils import Vector


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


def find_center(vertex_island_dict):
    vertex_island = [v for v in vertex_island_dict]
    center_point = mathutils.Vector()
    for vertex in vertex_island:
        center_point += vertex.co
    center_point /= len(vertex_island)
    return center_point


def distance_from_center(center, vertex_island_dict):
    distance_dict = {}
    for v in vertex_island_dict:
        dist = center - v.co
        weight = vertex_island_dict[v]
        distance_dict[dist.freeze()] = weight
    return distance_dict


#first get source bones distance from center of vertex group
def distance_between_center_and_bone(source_bone, vertex_center):
    if source_bone:
        head_location = source_bone.head
        distance = head_location - vertex_center
        return distance
    else:
        return None
        
#then find that same location for the target mesh
def find_target_vertex_group_center(distance_from_bone, target_bone):
    if target_bone:
        head_location = target_bone.head
        vertex_group_center = head_location - distance_from_bone
        return vertex_group_center
    else:
        print("target bone is none")
        return None

def organize_vertex_groups(source_mesh_name):
    
    vertex_groups = get_vertex_groups(source_mesh_name)
    vertex_group_dict = {}

    # Switch to object mode NOTE: need to figure out why I need to do this
    bpy.ops.object.mode_set(mode='OBJECT')

    mesh_data = bpy.data.objects[source_mesh_name].data


    # Loop through all vertices to get all non zero weights and their vertex coordinates
    for v in mesh_data.vertices:
        # Get the weight of the vertex in the source group
        for vg in vertex_groups:

            source_vertex_group = vg

            try:

                if is_in_vertex_group(v.index, source_vertex_group):

                    # Assign the weight to the target group
                    weight = source_vertex_group.weight(v.index)
                    #check if thats the name
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
def remap_vertex_groups(vertex_group_dictionaries, source_armature_name, target_armature_name, target_mesh_name):

    # Switch to object mode NOTE: need to figure out why I need to do this
    bpy.ops.object.mode_set(mode='OBJECT')

    target_mesh = bpy.data.objects[target_mesh_name]

    for source_vertex_group_name in vertex_group_dictionaries:
        if source_vertex_group_name != "L_Ear":
            vertex_island = vertex_group_dictionaries[source_vertex_group_name] 
            source_armature = bpy.data.objects[source_armature_name]
            source_bone = source_armature.pose.bones.get(source_vertex_group_name)
            target_armature = bpy.data.objects[target_armature_name]
            target_bone = target_armature.pose.bones.get(source_vertex_group_name)
            center_point = find_center(vertex_island)
            #distance between source bone and center of vertex group
            distance_from_bone = distance_between_center_and_bone(source_bone, center_point)
            #get the location of the center of the supposed target vertex group using the above distance from bone
            target_vertex_group_center = find_target_vertex_group_center(distance_from_bone, target_bone)

            #TEST
            mark_location(target_vertex_group_center)
            breakpoint()
            #TEST

            #convert all vertex keys to distance from center point
            distance_dict = distance_from_center(center_point, vertex_island)
            #for now just make sure the faces are oriented in the same way and dont worry about rotating the target island based off the empty object
            #this will estiamte the target island and change the weights of them
            estimate_target_island(distance_dict, target_mesh, target_vertex_group_center, source_vertex_group_name)

            print(f"source vertex group transferred to target mesh")

    print(f"All source vertex groups transferred to target mesh")


#testing function to select vertices
def mark_location(vertex):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=vertex)



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
remap_vertex_groups(vertex_group_dictionaries, source_armature_name, target_armature_name, target_mesh_name)




