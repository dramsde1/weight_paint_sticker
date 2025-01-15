import bpy
import bmesh
import mathutils
import math

def paint_hair_top(object_name):

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
        
        #each hair strand all have the same uvs so you should be able to do the next few lines once and apply it to all parts

        uv_height, min_v, max_v = get_uv_height(obj)

        #get X percent down the uv map and return those uv points

        closest_uv, closest_index = closest_uv = get_closest_uv(obj, target_uv)


        for part in loose_parts:

            bpy.ops.object.mode_set(mode='OBJECT')
            part.select_set(True)
            bpy.context.view_layer.objects.active = part


            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')


            world_coords = get_hair_root_position(part)
            xstart = world_coords[0]
            ystart = world_coords[1]

            bpy.ops.paint.weight_gradient(xstart=xstart, xend=957, ystart=ystart, yend=359, flip=False)

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



def get_hair_root_position(obj):
    # Get the active UV map
    uv_layer = obj.data.uv_layers.active.data

    # Initialize variables to track the maximum V value and its corresponding UV coordinates
    max_v = float('-inf')
    max_uv_coords = None
    max_loop_index = None

    # Iterate through all UV coordinates
    for loop_index, uv in enumerate(uv_layer):
        uv_coords = uv.uv
        if uv_coords[1] > max_v:  # Compare the V (y) value
            max_v = uv_coords[1]
            max_uv_coords = uv_coords
            max_loop_index = loop_index

    loop = obj.data.loops[max_loop_index]
    vertex_index = loop.vertex_index
    vertex = obj.data.vertices[vertex_index]
    world_coords = obj.matrix_world @ vertex.co

    return world_coords



paint_hair_top("LOD_1_Group_0_Sub_1__esf_Hair00")



def apply_weight_gradient(obj_name, start, end, vertex_group_name):
    """
    Mimics the weight gradient operator by applying weights directly.
    
    Parameters:
    - obj_name: The name of the object.
    - start: The start point of the gradient (world coordinates).
    - end: The end point of the gradient (world coordinates).
    - vertex_group_name: The name of the vertex group to modify.
    """
    # Get the object
    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != 'MESH':
        raise ValueError(f"Object '{obj_name}' not found or is not a mesh.")

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

    print(f"Weight gradient applied to '{vertex_group_name}' in object '{obj_name}'.")

# Example Usage
#apply_weight_gradient(
#    obj_name="YourObjectNameHere",
#    start=(0, 0, 0),       # Start of the gradient (world coordinates)
#    end=(1, 0, 0),         # End of the gradient (world coordinates)
#    vertex_group_name="GradientWeights"
#)

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

    # Iterate through UV coordinates to find min and max V
    for uv_loop in uv_layer.data:
        v = uv_loop.uv[1]  # Get the V (y) coordinate
        if v < min_v:
            min_v = v
        if v > max_v:
            max_v = v

    # Calculate the height
    uv_height = max_v - min_v
    return uv_height, min_v, max_v


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

    return closest_uv, closest_index

# Example usage
#obj = bpy.context.object  # Use the active object
#if obj:
#    try:
#        target_uv = (0.5, 0.5)  # Example target UV location
#        closest_uv, closest_index = get_closest_uv(obj, target_uv)
#        print(f"Closest UV: {closest_uv}")
#        print(f"Closest Index: {closest_index}")
#    except ValueError as e:
#        print(e)
#else:
#    print("No active object selected.")

