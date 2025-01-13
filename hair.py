import bpy
import bmesh

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
