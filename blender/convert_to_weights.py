import bpy
import bmesh
from mathutils import Vector, kdtree
import math

def create_rgb_to_weight_map():
    # Create a temporary material to access the color ramp node
    temp_material = bpy.data.materials.new(name="TempMaterial")
    temp_material.use_nodes = True
    nodes = temp_material.node_tree.nodes
    color_ramp_node = nodes.new(type="ShaderNodeValToRGB")
    
    # Set up a color ramp with Blender-like weight colors
    color_ramp_node.color_ramp.interpolation = 'LINEAR'
    color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 1.0, 1.0)  # Blue at weight 0.0
    color_ramp_node.color_ramp.elements[1].color = (1.0, 0.0, 0.0, 1.0)  # Red at weight 1.0
    color_ramp_node.color_ramp.elements.new(0.5).color = (0.0, 1.0, 0.0, 1.0)  # Green at weight 0.5

    rgb_to_weight_map = {}
    
    increments = 500
    for i in range(increments + 1):
        weight = i / increments
        sampled_rgb = color_ramp_node.color_ramp.evaluate(weight)[:3]
        rgb_to_weight_map[sampled_rgb] = weight

    # Clean up: remove the temporary material
    bpy.data.materials.remove(temp_material, do_unlink=True)

    #kind of hacky but if the rgb value is black, give it the same value as if it were blue
    #adding black (for the background) to a number system that really spans between blue, red, green
    rgb_to_weight_map[(0.0, 0.0, 0.0)] = 0.0

    return rgb_to_weight_map

def rgb_to_weight(rgb, rgb_to_weight_map):
    """
    Converts an RGB color to a weight value (0.0 - 1.0) by approximating Blender's weight paint color gradient.
    :param rgb: An (r, g, b) tuple with values between 0.0 and 1.0.
    :return: A float value representing the weight (0.0 for blue to 1.0 for red).
    """
    rgb_values = list(rgb_to_weight_map.keys()) 
    closest_rgb = min(rgb_values, key=lambda x: math.sqrt(sum((x[j] - rgb[j]) ** 2 for j in range(3))))
    closest_weight = rgb_to_weight_map[closest_rgb]

    return closest_weight



def sample_texture_at_uv(obj, uv, image):
    # Convert UV coordinates to image pixel space
    uv_x = int(uv.x * image.size[0])
    uv_y = int(uv.y * image.size[1])

    # Sample the color from the image pixels
    pixel_index = (uv_y * image.size[0] + uv_x) * 4
    r, g, b, a = image.pixels[pixel_index:pixel_index + 4]
    return (r, g, b, a)



def project_texture_to_weights(obj, group_name, image_name):
    # Get the vertex group to apply weights
    vertex_group = obj.vertex_groups.get(group_name)

    image = get_image_from_image_editor()

    rgb_to_weight_map = create_rgb_to_weight_map()

    # Ensure the object is a mesh
    if obj and obj.type == 'MESH':
        # Ensure we're in Edit Mode to access bmesh
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Create a BMesh from the object mesh data
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Get the active UV layer
        uv_layer = bm.loops.layers.uv.active
        if not uv_layer:
            print("No active UV layer found.")
            return
        
        # Dictionary to store weights for vertices
        vertex_dict = {}

        # Loop through each face
        for face in bm.faces:
            # Only process selected faces (or vertices)
            for loop in face.loops:
                vertex = loop.vert  # Get the vertex from the loop
                if vertex.select:
                    uv = loop[uv_layer].uv  # Access the UV from the loop
                    # Sample color from the texture at the UV coordinate
                    red, green, blue, alpha = sample_texture_at_uv(obj, uv, image)
                    # Convert the RGB color to a weight value
                    weight_value = rgb_to_weight((red, green, blue), rgb_to_weight_map)

                    # Store the weight value in the dictionary
                    vertex_dict[vertex.index] = weight_value

        # Set to Object Mode to apply vertex weights
        bpy.ops.object.mode_set(mode='OBJECT')

        # Apply the vertex weights to the vertex group
        for idx, weight_value in vertex_dict.items():
            vertex_group.add([idx], weight_value, 'REPLACE')

        # Free the BMesh after we're done
        bm.free()

    else:
        print("Selected object is not a mesh.")



def get_image_from_image_editor():
    # Check if a UV Editor is already open
    uv_editor_found = any(area.type == 'IMAGE_EDITOR' for area in bpy.context.screen.areas)

    # If UV Editor is found, access the active image in the UV Editor
    if uv_editor_found:
        for area in bpy.context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                image = area.spaces.active.image
                if image:
                    print(f"Active image in UV Editor: {image.name}")
                    return image
                else:
                    print("No active image in the UV Editor.")
    else:
        # Split an existing area vertically to create a new UV Editor
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':  # Choose an area type to split (e.g., 'VIEW_3D')
                override = bpy.context.copy()
                override["area"] = area
                
                # Split the area vertically
                bpy.ops.screen.area_split(override, direction='VERTICAL', factor=0.5)
                
                # The new area will be the last area in bpy.context.screen.areas
                new_area = bpy.context.screen.areas[-1]
                new_area.type = 'IMAGE_EDITOR'

                image = new_area.spaces.active.image
                if image:
                    print(f"Active image in UV Editor: {image.name}")
                    return image
                else:
                    print("No active image in the UV Editor.")


# Example usage:
object_name = "LOD_1_Group_0_Sub_3__esf_Head.001"
obj = bpy.data.objects.get(object_name)
vertex_group_name = "C_nose_Top"
image_name = "example.png"
project_texture_to_weights(obj, vertex_group_name, image_name)
