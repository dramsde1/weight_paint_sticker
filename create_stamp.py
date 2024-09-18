import bpy
import mathutils
import site
import pip

#pip.main(['install', 'dask', '--target', site.USER_SITE])
import bpy
import bmesh
import sys
from mathutils import Vector
from mathutils.kdtree import KDTree
from collections import deque
from concurrent.futures import ThreadPoolExecutor


def get_bounds(bounding_box_obj):
    # Ensure the bounding box object exists
    if bounding_box_obj and bounding_box_obj.type == 'MESH':
        # Calculate the world-space bounding box of the object
        bbox_corners = [bounding_box_obj.matrix_world @ Vector(corner) for corner in bounding_box_obj.bound_box]
        
        # Get the min and max points of the bounding box
        min_x = min([v.x for v in bbox_corners])
        max_x = max([v.x for v in bbox_corners])
        min_y = min([v.y for v in bbox_corners])
        max_y = max([v.y for v in bbox_corners])
        min_z = min([v.z for v in bbox_corners])
        max_z = max([v.z for v in bbox_corners])

        bounding_dict = {"min_x":min_x,
                        "max_x":max_x,
                        "min_y":min_y,
                        "max_y":max_y,
                        "min_z":min_z,
                        "max_z":max_z}
        return bounding_dict
    else:
        return None 


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


def arrange_all_groups(source_mesh_name, bm):
    vertex_groups = get_vertex_groups(source_mesh_name)
    vertex_group_dict = {}
    source_obj = bpy.data.objects[source_mesh_name]
    #flip normals
#    source_obj = bpy.context.active_object
    bpy.context.view_layer.objects.active = source_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=True)
    bpy.ops.object.mode_set(mode='OBJECT')

    #copy vertices
    bm.from_mesh(source_obj.data)
    # Loop through all vertices to get all non zero weights and their vertex coordinates
    #for v in mesh_data.vertices:
    for v in bm.verts:
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

def arrange_vertex_group(source_mesh_name, bm, vertex_group_name):
    source_obj = bpy.data.objects[source_mesh_name]
    vertex_group = source_obj.vertex_groups.get(vertex_group_name)
    vertex_group_dict = {}
    #flip normals
#    source_obj = bpy.context.active_object
    bpy.context.view_layer.objects.active = source_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=True)
    bpy.ops.object.mode_set(mode='OBJECT')

    #copy vertices
    bm.from_mesh(source_obj.data)
    # Loop through all vertices to get all non zero weights and their vertex coordinates
    #for v in mesh_data.vertices:
    for v in bm.verts:
        try:
            if is_in_vertex_group(v.index, vertex_group):
                # Assign the weight to the target group
                weight = vertex_group.weight(v.index)
                if vertex_group_name in vertex_group_dict:
                    vertex_group_dict[vertex_group_name][v] = weight
                else:
                    vertex_group_dict[vertex_group_name] = {}
                    vertex_group_dict[vertex_group_name][v] = weight
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
    # Get the world coordinates of the empty object
    empty_world_coords = empty_obj.matrix_world.translation

    #for source_vertex_group_name in vertex_group_dictionaries:
    center_point = find_center(source_vertex_group_name, source_mesh)

    source_selected_vertices = vertex_group_dictionaries[source_vertex_group_name]

    distance_dict = distance_from_center(center_point, source_selected_vertices, source_mesh)
    #now you can make the newly created empty as your center and base everything off of that 
   
    if not source_mesh or not target_mesh:
        print("Source or target object not found.")
        sys.exit()

    target_bm = bmesh.new()
    target_bm.from_mesh(target_mesh.data)
    boundary_verts = []

    for f in target_bm.faces:
        face_normal = f.normal
        for v in f.verts:
            # Compare vertex normal with face normal
            if v.normal.dot(face_normal) > 0:
                world_vertex_location = target_mesh.matrix_world @ v.co
                boundary_verts.append((world_vertex_location, v.index))

    #create kd tree for easier vertex index location targeting based on the hit location
    # Create a KDTree with the number of vertices
    size = len(boundary_verts)
    kd = KDTree(size)
    # Insert all vertices into the KDTree
    for tup in boundary_verts:
        vert = tup[0]
        index = tup[1]
        kd.insert(vert, index)
    # Balance the KDTree after insertion
    kd.balance()

    selected_vertex_group = vertex_group_dictionaries[source_vertex_group_name]
    target_vertex_group = target_mesh.vertex_groups.get(source_vertex_group_name)
    found_target_vertices = []
    for vertex in distance_dict:
        #get new positions based on distance_dict
        metadata = distance_dict[vertex]
        distance = metadata["distance"]
        weight = metadata["weight"]
        target_estimate = empty_world_coords + distance
        co, index, dist = kd.find(target_estimate)
        found_target_vertices.append({"index": index, "weight": weight})
    
    max_depth = 5

    # Pre-build adjacency list using edges
    adjacency_list = [[] for _ in range(len(target_mesh.data.vertices))]
    for edge in target_mesh.data.edges:
        v1, v2 = edge.vertices
        adjacency_list[v1].append(v2)
        adjacency_list[v2].append(v1)

    connected_components = run_parallel_bfs(target_vertex_group, found_target_vertices, max_depth, adjacency_list)

    target_bm.free()

def paint_connected_vertices(target_vertex_group, start_vertex_index, max_depth, weight, adjacency_list):
    # Initialize BFS
    queue = deque([(start_vertex_index, 0)])
    visited = {start_vertex_index}
    
    # Perform BFS
    while queue:
        vertex_index, depth = queue.popleft()
        
        if depth >= max_depth:
            continue
        
        for neighbor_index in adjacency_list[vertex_index]:
            if neighbor_index not in visited:
                visited.add(neighbor_index)
                queue.append((neighbor_index, depth + 1))

    for idx in visited:
        target_vertex_group.add([idx], weight,'REPLACE')
    
    return visited

# Function to handle each parallel task
def bfs_task(params):
    target_vertex_group, start_vertex_index, max_depth, weight, adjacency_list = params
    return paint_connected_vertices(target_vertex_group, start_vertex_index, max_depth, weight, adjacency_list)

# Example usage of ThreadPoolExecutor for parallel execution
def run_parallel_bfs(target_vertex_group, found_target_vertices, max_depth, adjacency_list):
    # Create a list of parameters to pass to each thread
    params_list = [(target_vertex_group, d["index"], max_depth, d["weight"], adjacency_list) for d in found_target_vertices]
    
    with ThreadPoolExecutor() as executor:
        # Run the BFS function in parallel for each start vertex
        results = list(executor.map(bfs_task, params_list))
    
    return results


def mark_location(vertex):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=vertex)

def get_vertex_groups(mesh_name):
    vertex_groups = bpy.data.objects[mesh_name].vertex_groups
    return vertex_groups

#source_mesh_name = "source"
#target_mesh_name = "target"
#source_armature_name = "source_arm"
#target_armature_name = "target_arm"

source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
target_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head.001"
source_armature_name = "Root.002"
target_armature_name = "Root.001"

#get the source and target 
#source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
#target_mesh_name = "Cube"
#source_armature_name = "Root.002"
#target_armature_name = "Root.001"
source_vertex_group_name = "C_nose_Top"
empty_name = "Empty"
bm = bmesh.new() #bmesh where you will put copy of source vertex
#vertex_group_dictionaries = arrange_all_groups(source_mesh_name, bm)
vertex_group_dictionary = arrange_vertex_group(source_mesh_name, bm, source_vertex_group_name)
remap_vertex_groups(vertex_group_dictionary, source_armature_name, target_armature_name, source_mesh_name, target_mesh_name, source_vertex_group_name, empty_name)


