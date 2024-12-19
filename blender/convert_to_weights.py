import bpy
import bmesh
from mathutils import Vector, kdtree
import math
import json
from pathlib import Path

def delete_temp_material():
    temp_materials = []
    for material in bpy.data.materials:
        if "TempMaterial" in material.name:
            temp_materials.append(material)

    for temp_material in temp_materials:
        bpy.data.materials.remove(temp_material, do_unlink=True)


    
def create_rgb_to_weight_map():

    # Create a temporary material to access the color ramp node
    temp_material = bpy.data.materials.new(name="TempMaterial")
    temp_material.use_nodes = True
    nodes = temp_material.node_tree.nodes
    color_ramp_node = nodes.new(type="ShaderNodeValToRGB")
    
    # Set up a color ramp with Blender-like weight colors
    color_ramp_node.color_ramp.interpolation = 'B_SPLINE'

    color_ramp_node.color_ramp.elements[0].color = (0.0, 0.0, 1.0, 1.0)  # Blue at weight 0.0
    color_ramp_node.color_ramp.elements[1].color = (1.0, 0.0, 0.0, 1.0)  # Red at weight 1.0
    color_ramp_node.color_ramp.elements.new(0.5).color = (0.0, 1.0, 0.0, 1.0)  # Green at weight 0.5


    color_ramp_node.color_ramp.elements[1].position = 0.7

    rgb_to_weight_map = {}
    
    increments = 100
    for i in range(increments + 1):
        weight = i / increments
        sampled_rgb = color_ramp_node.color_ramp.evaluate(weight)[:3]
        rgb_to_weight_map[sampled_rgb] = weight

    # Clean up: remove the temporary material
    #bpy.data.materials.remove(temp_material, do_unlink=True)

    #kind of hacky but if the rgb value is black, give it the same value as if it were blue
    #adding black (for the background) to a number system that really spans between blue, red, green
    rgb_to_weight_map[(0.0, 0.0, 0.0)] = 0.0

    #also a hack but map grey to blue as well 
    rgb_to_weight_map[(0.50390625, 0.50390625, 0.50390625)] = 0.0

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


def get_dict_from_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def get_reverse_lookup(data):
    reverse_lookup = {}
    for key, values in data.items():
        for value in values:
            reverse_lookup[value] = key
    return reverse_lookup


def project_texture_to_weights(obj, image, vertex_group_name, rgb_to_weight_map):
    # Get the vertex group to apply weights


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
                    vertex_dict[vertex.index] = {"weight_value": weight_value, "vertex_group_name": vertex_group_name}

        # Set to Object Mode to apply vertex weights
        bpy.ops.object.mode_set(mode='OBJECT')
        # Apply the vertex weights to the vertex group
        for idx, data in vertex_dict.items():
            vertex_group_name = data["vertex_group_name"]
            weight_value = data["weight_value"]
            vertex_group = obj.vertex_groups.get(vertex_group_name)
            if not vertex_group:  # If the vertex group doesn't exist
                vertex_group = obj.vertex_groups.new(name=vertex_group_name)
            vertex_group.add([idx], weight_value, 'REPLACE')

        # Free the BMesh after we're done
        bm.free()
    else:
        print("Selected object is not a mesh.")



# Example usage:
object_name = "low_head"
obj = bpy.data.objects.get(object_name)

folder_path = "E:\MODS\scripts\slickback_weight_textures"
directory = Path(folder_path)
delete_temp_material()
rgb_to_weight_map = create_rgb_to_weight_map()

for file_path in directory.glob("*.exr"):  
    vertex_group_name = Path(file_path).stem
    img = bpy.data.images.load(str(file_path.resolve()))
    project_texture_to_weights(obj, img, vertex_group_name, rgb_to_weight_map)
    bpy.data.images.remove(img, do_unlink=True)
    breakpoint()
