import bpy
import bmesh
import mathutils
import math

def paint_hair_top(object_name, vertex_group_name, percent_changed):

    # Ensure you're in Object Mode
    if bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Example usage:
    obj = bpy.data.objects.get(object_name)

    if not obj or obj.type != 'MESH':
        print("Please select a mesh object.")
    else:
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        # Select the active object
        obj.select_set(True)

        # Separate the object by loose parts
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')

        # Get the new objects (all loose parts)
        loose_parts = bpy.context.selected_objects
        
        strand = loose_parts[0]
        uv_height, min_point, max_point = get_uv_height(strand)
        v_end = max_point[1] - (uv_height * percent_changed) 
        end_point = [min_point[0], v_end]
        start_closest_uv = get_closest_uv(strand, max_point)
        end_closest_uv = get_closest_uv(strand, end_point)


        for part in loose_parts:

            part_root = uv_to_3d(part, start_closest_uv)
            part_end = uv_to_3d(part, end_closest_uv)
            apply_weight_gradient(part, part_root, part_end, vertex_group_name)

        bpy.ops.object.mode_set(mode='OBJECT')
        #join them all back again 
        # Select all the loose parts
        for obj in loose_parts:
            obj.select_set(True)
        # Set the first loose part as active for joining
        bpy.context.view_layer.objects.active = loose_parts[0]

        # Join the loose parts back into one object
        bpy.ops.object.join()
        # Print the new objeworld_coords
        #print("New Object Name:", bpy.context.object.name)
        print("DONE")



def apply_weight_gradient(obj, start, end, vertex_group_name):
    """
    Mimics the weight gradient operator by applying weights directly.
    
    Parameters:
    - obj_name: The name of the object.
    - start: The start point of the gradient (world coordinates).
    - end: The end point of the gradient (world coordinates).
    - vertex_group_name: The name of the vertex group to modify.
    """
    # Ensure the object has a vertex group
    if vertex_group_name not in obj.vertex_groups:
        obj.vertex_groups.new(name=vertex_group_name)
    vertex_group = obj.vertex_groups[vertex_group_name]

    # Convert start and end points to local space
    start_local = obj.matrix_world.inverted() @ mathutils.Vector(start)
    end_local = obj.matrix_world.inverted() @ mathutils.Vector(end)

    # Calculate the gradient direction vector
    gradient_vec = end_local - start_local
    gradient_length = gradient_vec.length

    if gradient_length == 0:
        raise ValueError("Start and end points of the gradient are the same.")

    gradient_vec.normalize()

    # Loop through vertices and assign weights
    mesh = obj.data
    for vertex in mesh.vertices:
        # Project vertex position onto the gradient line
        vertex_pos = vertex.co - start_local
        projection_length = vertex_pos.dot(gradient_vec)

        # Calculate weight (clamp between 0 and 1)
        weight = max(0, min(1, projection_length / gradient_length))

        # Assign the weight to the vertex group
        vertex_group.add([vertex.index], weight, 'REPLACE')

    print(f"Weight gradient applied to '{vertex_group_name}' in object '{obj.name}'.")


def get_uv_height(obj):
    if obj.type != 'MESH':
        raise ValueError(f"Object '{obj.name}' is not a mesh.")
    
    # Ensure the object has UV layers
    uv_layer = obj.data.uv_layers.active
    if not uv_layer:
        raise ValueError(f"Object '{obj.name}' does not have an active UV layer.")

    # Initialize variables for min and max V values
    min_v = float('inf')
    max_v = float('-inf')

    min_point = [None, None]
    max_point = [None, None]

    # Iterate through UV coordinates to find min and max V
    for uv_loop in uv_layer.data:
        v = uv_loop.uv[1]  # Get the V (y) coordinate
        u = uv_loop.uv[0]  # Get the V (y) coordinate
        if v < min_v:
            min_v = v
            min_point[0] = u
            min_point[1] = v
        if v > max_v:
            max_v = v
            max_point[0] = u
            max_point[1] = v

    # Calculate the height
    uv_height = max_v - min_v
    return uv_height, min_point, max_point


def get_closest_uv(obj, target_uv):
    """
    Finds the closest UV coordinate to the given target UV location.
    
    Args:
        obj: The mesh object containing the UV map.
        target_uv: A tuple (u, v) specifying the target UV location.
    
    Returns:
        The closest UV coordinate as a tuple (u, v) and its index in the UV loop.
    """
    if obj.type != 'MESH':
        raise ValueError(f"Object '{obj.name}' is not a mesh.")

    # Ensure the object has UV layers
    uv_layer = obj.data.uv_layers.active
    if not uv_layer:
        raise ValueError(f"Object '{obj.name}' does not have an active UV layer.")
    
    closest_uv = None
    closest_distance = float('inf')
    closest_index = None

    # Iterate through UV coordinates to find the closest one
    for index, uv_loop in enumerate(uv_layer.data):
        uv = uv_loop.uv
        distance = math.sqrt((uv[0] - target_uv[0])**2 + (uv[1] - target_uv[1])**2)
        if distance < closest_distance:
            closest_distance = distance
            closest_uv = uv
            closest_index = index

    return closest_uv


def uv_to_3d(obj, uv_coords):
    # Ensure the object is in object mode and has a UV map
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Make sure the object has at least one UV map
    if len(obj.data.uv_layers) == 0:
        raise ValueError(f"The object {obj.name} has no UV map.")
    
    # Get the active UV layer (default is usually the first one)
    uv_layer = obj.data.uv_layers.active.data
    
    # Loop through the faces of the object
    for poly in obj.data.polygons:
        # For each face, loop through the vertices and check if the UV coordinates match
        for loop_idx in poly.loop_indices:
            uv = uv_layer[loop_idx].uv
            # Check if the UV coordinates match the given UV (use a small threshold for comparison)
            if (abs(uv_coords[0] - uv[0]) < 0.001 and abs(uv_coords[1] - uv[1]) < 0.001):
                # Return the corresponding 3D vertex
                vertex = obj.data.vertices[poly.vertices[loop_idx]]
                return obj.matrix_world @ vertex.co  # Convert local vertex to world space
    
    # If no match is found
    #raise ValueError("No corresponding vertex found for the UV coordinates.")
    return None

if __name__ == "__main__":
    paint_hair_top("plane", "hair", 0.20)
