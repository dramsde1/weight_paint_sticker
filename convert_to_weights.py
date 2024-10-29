import bpy
import bmesh
from mathutils import Vector, kdtree
import math

def rgb_to_weight(rgb):
    """
    Converts an RGB value to a weight (0.0 - 1.0) using Blender's weight paint color gradient.
    
    :param rgb: An (r, g, b) tuple with values between 0.0 and 1.0.
    :return: A float value between 0.0 (blue) and 1.0 (red) representing the weight.
    """
    r, g, b = rgb
    
    # Check if color is close to blue (0.0 weight)
    if math.isclose(r, 0.0, abs_tol=0.1) and math.isclose(g, 0.0, abs_tol=0.1) and math.isclose(b, 1.0, abs_tol=0.1):
        return 0.0  # Blue, corresponding to weight 0.0
    
    # Check if color is close to green (0.5 weight)
    elif math.isclose(r, 0.0, abs_tol=0.1) and math.isclose(g, 1.0, abs_tol=0.1) and math.isclose(b, 0.0, abs_tol=0.1):
        return 0.5  # Green, corresponding to weight 0.5
    
    # Check if color is close to red (1.0 weight)
    elif math.isclose(r, 1.0, abs_tol=0.1) and math.isclose(g, 0.0, abs_tol=0.1) and math.isclose(b, 0.0, abs_tol=0.1):
        return 1.0  # Red, corresponding to weight 1.0
    
    # Otherwise, interpolate between colors
    if b > 0 and g == 0 and r == 0:
        # Interpolate between blue (0.0) and green (0.5)
        weight = b * 0.5
    elif r > 0 and g > 0 and b == 0:
        # Interpolate between green (0.5) and red (1.0)
        weight = 0.5 + (r * 0.5)
    else:
        # Default to 0 if color does not match known points
        weight = 0.0

    return weight


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
                    weight_value = rgb_to_weight((red, green, blue))

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

