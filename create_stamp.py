"""
The assumption is that you are creating a stamp for the same bone on a duplicate of the same armature that is the parent of a different mesh. So the bone your transfering the stamp to should have the same name

SETUP
0) Pick the source and target armatures
1) Assume the target armature is already parented to the target mesh

GET WEIGHTS
1) get the weights for each vertex in a vertex groups for a single bone 
2) pick a central vertex in the vertex group to which all other vertices will translate/rotate in relation to 

TRANSFER TO NEW ARMATURE
3) move weights all at the same time to the target bone (retarget)
4) allow on mouse movement to translate the whole weight painting map for a bone

"""
"""
    May want to cache all of the weights somehow, then have a while loop run while you use mouse events to decide where to translate the weights stamp and then have a 

    key to both place the map and jump out of the while loop


    Need to store two things:
        weight of original source vertex within original vertex group
        the position of the vertex 

    What data structure to store is best?
        for fast look up perhaps create a hash from the positional coordinates and use that as an id in a dictionary
        {"hash": weight}

        then once you store all of the non zero vertices in the vertex group into the dictionary, that will make up the weight island. 
        the next thing you have to do is find the center of the island
        then once you find the center you need to convert the key for each element to be the distance hash from the center point so that it becomes

        {distance_from_center: weight}

        then once you have that information stored you can use an empty_object to move the whole island on the target mesh and then calculate where the verteices should map to

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



#1) get the weights for each vertex in a vertex groups for a single bone 
def estimate_target_island(distance_dict, target_mesh, target_vertex_group_center, vertex_group_name):
    target_mesh_data = target_mesh.data
    vertex_group = target_mesh.vertex_groups.get(vertex_group_name)
    # Loop through all vertices
    for d in distance_dict:
        #get the true location of the matching target vertex
        #center - v = dist
        #center - dist = v
        target_estimate = target_vertex_group_center - d
        min_distance = mathutils.Vector((float('inf'), float('inf'), float('inf')))
        min_vertex = mathutils.Vector()

        for v in target_mesh_data.vertices:
            #what is the closest vertex to the target estimate
            dist = v.co - target_estimate 
            
            abs_dist = mathutils.Vector((abs(dist[0]), abs(dist[1]), abs(dist[2])))

            if abs_dist < min_distance:
                min_distance = abs_dist
                min_vertex = v

        weight = distance_dict[d]

        vertex_group.add([min_vertex.index], weight, 'REPLACE')
         

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


# this function is meant to be used in a for loop, looping through all of the bones/vertex groups on an armature/meshG
# for mods, the bone names should be the same for both armatures
def remap_vertex_group(source_vertex_group, source_armature_name, source_mesh_name, target_armature_name, target_mesh_name):
    vertex_island = {} 


    # Switch to object mode NOTE: need to figure out why I need to do this
    bpy.ops.object.mode_set(mode='OBJECT')
    
    source_armature = bpy.data.objects[source_armature_name]

    source_bone = source_armature.pose.bones.get(source_vertex_group.name)

    target_armature = bpy.data.objects[target_armature_name]
    #target vertex group is the same name as the source vertex group
    target_bone = target_armature.pose.bones.get(source_vertex_group.name)

    #loop through source bones / target ones will be the same names
    # make sure vertex group name is in mesh list of vertex groups

    mesh_data = bpy.data.objects[source_mesh_name].data
    target_mesh = bpy.data.objects[target_mesh_name]


    if source_vertex_group.name in bpy.data.objects[source_mesh_name].vertex_groups:

        #first check if target_vertex_group already exists
        target_vertex_group = target_mesh.vertex_groups.get(source_vertex_group.name)


        if target_vertex_group is None:
            target_vertex_group = target_mesh.vertex_groups.new(name=source_vertex_group.name)
        
        #go through source mesh vertices to get weights for each vertex in source vertex group


        # Loop through all vertices to get all non zero weights and their vertex coordinates
        for v in mesh_data.vertices:
            # Get the weight of the vertex in the source group
            try:
                #check if the vertex is in the source vertex group
                # a single vertex can belong to multiple vertex groups
                if is_in_vertex_group(v.index, source_vertex_group):

                    # Assign the weight to the target group
                    weight = source_vertex_group.weight(v.index)
                    vertex_island[v] = weight

            except RuntimeError as e:
                #Error: Vertex not in group
                continue

        center_point = find_center(vertex_island)

        #distance between source bone and center of vertex group
        distance_from_bone = distance_between_center_and_bone(source_bone, center_point)
        
        #get the location of the center of the supposed target vertex group using the above distance from bone
        target_vertex_group_center = find_target_vertex_group_center(distance_from_bone, target_bone)


        #convert all vertex keys to distance from center point
        distance_dict = distance_from_center(center_point, vertex_island)
       
        #for now just make sure the faces are oriented in the same way and dont worry about rotating the target island based off the empty object

        #this will estiamte the target island and change the weights of them
        estimate_target_island(distance_dict, target_mesh, target_vertex_group_center, source_vertex_group.name)


        print(f"source vertex group transferred to tareget mesh")
    else:
        print(f"Vertex group '{source_vertex_group}' not found.")

def get_vertex_groups(mesh_name):

    vertex_groups = bpy.data.objects[mesh_name].vertex_groups

    return vertex_groups

def check_empty_groups(mesh_name):
    vertex_groups = bpy.data.objects[mesh_name].vertex_groups

source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
target_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head.001"
source_armature = "Root.002"
target_armature = "Root.001"
vertex_groups = get_vertex_groups(source_mesh_name)
for vg in vertex_groups:
    remap_vertex_group(vg, source_armature, source_mesh_name, target_armature, target_mesh_name)



