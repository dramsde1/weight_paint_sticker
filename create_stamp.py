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


def get_verts_within_bounds():
    # Get the object to use as the bounding box (e.g., a rectangle or cube)
    bounding_box_obj = bpy.data.objects.get("Rectangle")  # Replace "Rectangle" with the name of your bounding box object
    
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
        
        # Get the active mesh (the object whose vertices you want to select)
        obj = bpy.context.object
        if obj and obj.type == 'MESH':
            mesh = obj.data
            
            # Switch to edit mode to manipulate vertices
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Create a BMesh instance to work with
            bm = bmesh.from_edit_mesh(mesh)
            
            # Iterate over all vertices and select those within the bounding rectangle
            for vert in bm.verts:
                # Transform the vertex coordinates to world space
                v_co_world = obj.matrix_world @ vert.co
                
                # Check if the vertex is within the bounds of the bounding box
                if (min_x <= v_co_world.x <= max_x and
                    min_y <= v_co_world.y <= max_y and
                    min_z <= v_co_world.z <= max_z):
                    vert.select = True  # Select the vertex
                else:
                    vert.select = False  # Deselect the vertex
            
            # Update the mesh to reflect changes
            bmesh.update_edit_mesh(mesh)
        
        # Switch back to object mode if needed
        bpy.ops.object.mode_set(mode='OBJECT')
    else:
        print("Bounding box object not found or not a mesh.")






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


def organize_vertex_groups(source_mesh_name, bm):
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

    for vertex in distance_dict:
        #get new positions based on distance_dict
        metadata = distance_dict[vertex]
        distance = metadata["distance"]
        weight = metadata["weight"]
        target_estimate = empty_world_coords + distance
        co, index, dist = kd.find(target_estimate)
        #location = (co.x, co.y, co.z)
        #bpy.ops.object.empty_add(type='PLAIN_AXES', location=location)
        #get the center of the connected component cluster in order to weight paint groups
        group = select_connected_vertices(target_mesh, index, 5)
        for idx in group:
            target_vertex_group.add([idx], weight,'REPLACE')

    target_bm.free()

def select_connected_vertices(obj, start_vertex_index, max_depth):
    if obj.type != 'MESH':
        print("Active object is not a mesh.")
        return
    
    # Access the mesh data directly
    mesh = obj.data
    
    # Initialize BFS
    queue = deque([(start_vertex_index, 0)])
    visited = {start_vertex_index}
    
    # Pre-build adjacency list using edges
    adjacency_list = [[] for _ in range(len(mesh.vertices))]
    for edge in mesh.edges:
        v1, v2 = edge.vertices
        adjacency_list[v1].append(v2)
        adjacency_list[v2].append(v1)
    
    # Perform BFS
    while queue:
        vertex_index, depth = queue.popleft()
        
        if depth >= max_depth:
            continue
        
        for neighbor_index in adjacency_list[vertex_index]:
            if neighbor_index not in visited:
                visited.add(neighbor_index)
                queue.append((neighbor_index, depth + 1))
    
    return visited

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
vertex_group_dictionaries = organize_vertex_groups(source_mesh_name, bm)
remap_vertex_groups(vertex_group_dictionaries, source_armature_name, target_armature_name, source_mesh_name, target_mesh_name, source_vertex_group_name, empty_name)


