import bpy
import bmesh
from mathutils import Vector, kdtree

def rgb_to_weight(rgb):
    """
    Converts an RGB value back to a weight (0.0 - 1.0) based on the Blender-like color gradient.
    
    :param rgb: A tuple of (r, g, b) with values between 0.0 and 1.0.
    :return: A float weight between 0.0 (blue) and 1.0 (red).
    """
    r, g, b = rgb

    # Colors at key points in the gradient
    blue = (0.0, 0.0, 1.0)   # Weight 0.0
    green = (0.0, 1.0, 0.0)  # Weight 0.5
    red = (1.0, 0.0, 0.0)    # Weight 1.0
    
    # Determine which segment of the gradient we are in
    if b > 0 and g == 0 and r == 0:
        # Blue to Green segment
        weight = b * 0.5
    elif g > 0 and b == 0:
        # Green to Red segment
        weight = 0.5 + g * 0.5
    else:
        weight = r  # If only red remains, weight is 1.0

    # Clamp the weight between 0.0 and 1.0
    return max(0.0, min(weight, 1.0))

def sample_texture_at_uv(obj, uv):
    """
    Sample the texture color at given UV coordinates for the object's image texture node.
    
    :param obj: The object to sample the texture from.
    :param uv: The UV coordinates at which to sample the texture.
    :return: An (r, g, b, a) tuple with values between 0.0 and 1.0.
    """
    material = obj.active_material
    if not material or not material.use_nodes:
        raise Exception("Object must have a material with nodes!")

    # Find the Image Texture node in the material
    image_texture_node = None
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            image_texture_node = node
            break

    if not image_texture_node or not image_texture_node.image:
        raise Exception("No image texture found in the material!")

    image = image_texture_node.image
    width, height = image.size

    x_pixel = int(uv.x * width) % width
    y_pixel = int(uv.y * height) % height

    pixel_index = (y_pixel * width + x_pixel) * 4
    red, green, blue, alpha = image.pixels[pixel_index:pixel_index + 4]

    return red, green, blue, alpha


def project_texture_to_weights(obj, group_name):
    """
    Project the image texture from the object's material onto itself, converting RGB values to bone weights.
    
    :param obj: The target object with an image texture and armature.
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Ensure the object has a UV map
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        raise Exception("No UV map found on the object!")

    # Create or find a vertex group for storing weights
    vertex_group = obj.vertex_groups.get(group_name)

    # Iterate through the vertices and map UV to weights
    for face in bm.faces:
        for loop in face.loops:
            vert = loop.vert
            uv = loop[uv_layer].uv  # Get the UV coordinates for this vertex

            # Sample the texture color at the UV coordinates
            red, green, blue, alpha = sample_texture_at_uv(obj, uv)

            # Convert the RGB color to a weight value
            weight_value = rgb_to_weight((red, green, blue))

            # Assign the weight to the vertex
            vertex_group.add([vert.index], weight_value, 'REPLACE')

    # Update the mesh with the new vertex weights
    bm.to_mesh(mesh)
    bm.free()

# Example usage:
obj = bpy.context.active_object  # The object with the texture to project
vertex_group_name = "C_nose_Top"
project_texture_to_weights(obj, vertex_group_name)

