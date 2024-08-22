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
    for source_vertex_group_name in vertex_group_dictionaries:
        if source_vertex_group_name != "L_Ear":
            #vertex_island = vertex_group_dictionaries[source_vertex_group_name] 
            vertex_island = get_connected_components_indices(source_mesh, vertex_group_dictionaries, source_vertex_group_name)
            source_armature = bpy.data.objects[source_armature_name]
            source_bone = source_armature.pose.bones.get(source_vertex_group_name)
            target_armature = bpy.data.objects[target_armature_name]
            target_bone = target_armature.pose.bones.get(source_vertex_group_name)
            center_point = find_center(vertex_island[0])
            #distance between source bone and center of vertex group
            distance_from_bone = distance_between_center_and_bone(source_bone, center_point)
            #get the location of the center of the supposed target vertex group using the above distance from bone
            target_vertex_group_center = find_target_vertex_group_center(distance_from_bone, target_bone)

            #TEST
            #mark_location(target_vertex_group_center)
            #source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
            #mesh = bpy.data.objects[source_mesh_name]
            #distance_threshold = 20
            #select_vertex_group(bpy.data.objects[source_mesh_name], source_vertex_group_name, vertex_group_dictionaries)
            #components = get_connected_components_indices(mesh, vertex_group_dictionaries, source_vertex_group_name)
            #in_range_components = get_components_in_range(mesh, components, distance_threshold)
            #select_component(mesh, [mesh.data.vertices[idx] for c in components[:2] for idx in c])
            #breakpoint()
            #TEST
            #convert all vertex keys to distance from center point
            distance_dict = distance_from_center(center_point, vertex_island[0])
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

def select_vertex_group(mesh, group_name, vertex_group_dict):
    # Deselect all objects and select mesh
     # Select the object
    mesh.select_set(True)
    # Optionally, make the object the active object
    bpy.context.view_layer.objects.active = mesh

    # Ensure we're in Edit Mode
    if bpy.context.object.mode != 'EDIT':
        #bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.editmode_toggle()

    # Switch to Vertex Selection Mode
    bpy.ops.mesh.select_mode(type='VERT')
    group_verts = list(vertex_group_dict[group_name].keys())
    bpy.ops.object.mode_set(mode = 'OBJECT')
    mesh = bpy.context.active_object
    bpy.ops.object.mode_set(mode = 'EDIT') 
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.select_all(action = 'DESELECT')
    bpy.ops.object.mode_set(mode = 'OBJECT')
    for v in group_verts:
        v.select = True
    bpy.ops.object.mode_set(mode = 'EDIT') 


def select_component(mesh, component):
    # Deselect all objects and select mesh
     # Select the object
    mesh.select_set(True)
    # Optionally, make the object the active object
    bpy.context.view_layer.objects.active = mesh
    # Ensure we're in Edit Mode
    if bpy.context.object.mode != 'EDIT':
        #bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.editmode_toggle()
    # Switch to Vertex Selection Mode
    bpy.ops.mesh.select_mode(type='VERT')
    bpy.ops.object.mode_set(mode = 'OBJECT')
    mesh = bpy.context.active_object
    bpy.ops.object.mode_set(mode = 'EDIT') 
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.select_all(action = 'DESELECT')
    bpy.ops.object.mode_set(mode = 'OBJECT')

    for vertex in component:
        #vertex = mesh.data.vertices[i]
        vertex.select = True

    bpy.ops.object.mode_set(mode = 'EDIT') 

def bfs(start_vertex, visited, adjacency_list):
    queue = deque([start_vertex])
    connected_component = []
    while queue:
        current_vertex = queue.popleft()
        if current_vertex not in visited:
            visited.add(current_vertex)
            connected_component.append(current_vertex)
            queue.extend(adjacency_list[current_vertex])
    return connected_component, visited

def get_connected_components_indices(mesh, vertex_group_dict, group_name, selected_only=False):
    group_verts = list(vertex_group_dict[group_name].keys())
    vertex_indices = [v.index for v in group_verts]
    adjacency_list = defaultdict(list)
    for edge in mesh.data.edges:
        v1, v2 = edge.vertices
        if v1 in vertex_indices and v2 in vertex_indices:
            adjacency_list[v1].append(v2)
            adjacency_list[v2].append(v1)

    # Find all connected components
    visited = set()
    connected_components = []
    for vertex_index in vertex_indices:
        if vertex_index not in visited:
            component, visited = bfs(vertex_index, visited, adjacency_list)
            connected_components.append(component)
    return connected_components

def get_components_in_range(mesh, connected_components, distance_threshold):
    # Precompute coordinates for all components
    coordinates = [[mesh.data.vertices[a].co for a in component] for component in connected_components]
    coordinates_mesh_vertices = [[mesh.data.vertices[a] for a in component] for component in connected_components]

    # Create KDTree for each component
    kdtree_list = []
    for component in coordinates:
        kd = mathutils.kdtree.KDTree(len(component))
        for i, point in enumerate(component):
            kd.insert(point, i)
        kd.balance()
        kdtree_list.append(kd)

    in_range_components = []
    
    # Compare each pair of components
    for i, tree_a in enumerate(kdtree_list):
        for j in range(i + 1, len(kdtree_list)):
            tree_b = kdtree_list[j]
            min_distance = float('inf')  # Initialize with a large value
            # Iterate through all points in tree_a and find the closest point in tree_b
            for point in coordinates[i]:
                co, index, dist = tree_b.find(point)  # Find nearest point in tree_b
                if dist < min_distance:
                    min_distance = dist
            if min_distance < distance_threshold:
                in_range_components.append(coordinates_mesh_vertices[i])

    return in_range_components



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




