import bpy
import bmesh
from mathutils import Vector, Matrix

# Function to create a transformation matrix (translation, scale, rotation)
def create_transformation_matrix(location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
    translation_matrix = Matrix.Translation(Vector(location))
    rotation_matrix_x = Matrix.Rotation(rotation[0], 4, 'X')
    rotation_matrix_y = Matrix.Rotation(rotation[1], 4, 'Y')
    rotation_matrix_z = Matrix.Rotation(rotation[2], 4, 'Z')
    scale_matrix = Matrix.Diagonal(Vector((scale[0], scale[1], scale[2], 1)))

    transformation_matrix = translation_matrix @ rotation_matrix_x @ rotation_matrix_y @ rotation_matrix_z @ scale_matrix
    return transformation_matrix

# Function to project a 3D point onto the mesh and get the corresponding UV coordinate
def get_uv_from_3d_point(obj, point, ray_direction):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        raise Exception("No UV map found on mesh!")

    result, location, normal, index, obj, matrix = obj.ray_cast(point, ray_direction)
    
    if result:
        face = bm.faces[index]
        for loop in face.loops:
            uv = loop[uv_layer].uv
            return uv
    else:
        return None

# Function to sample the texture color from the UV coordinates
def sample_texture_at_uv(image_plane, uv):
    material = image_plane.active_material
    if not material or not material.use_nodes:
        raise Exception("Image plane must have a material with nodes!")
    
    image_texture_node = None
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            image_texture_node = node
            break
    
    if image_texture_node is None or not image_texture_node.image:
        raise Exception("No image texture found in the material!")
    
    image = image_texture_node.image
    width, height = image.size

    x_pixel = int(uv.x * width) % width
    y_pixel = int(uv.y * height) % height

    pixel_index = (y_pixel * width + x_pixel) * 4
    red, green, blue, alpha = image.pixels[pixel_index:pixel_index + 4]

    return red, green, blue, alpha

# Function to project each pixel of the image texture onto the target object
def project_texture_pixels_to_object(image_plane, target_object, image_plane_size=(1, 1), rotation=(0, 0, 0)):
    image_plane_location = image_plane.location
    image_plane_normal = image_plane.matrix_world.to_quaternion() @ Vector((0, 0, 1))

    plane_width, plane_height = image_plane_size

    transformation_matrix = create_transformation_matrix(location=image_plane_location, rotation=rotation, scale=(plane_width, plane_height, 1))

    obj = target_object
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        raise Exception("No UV map found on mesh!")

    vertex_group = obj.vertex_groups.new(name="WeightPaint")

    image_texture_node = image_plane.active_material.node_tree.nodes['Image Texture']
    image = image_texture_node.image
    width, height = image.size

    ray_direction = image_plane_normal.normalized()

    # Loop through each pixel in the texture
    for y in range(height):
        for x in range(width):
            # Calculate normalized UV coordinates for the current pixel
            uv = Vector((x / width, y / height))

            # Convert the UV coordinate to 3D space using the transformation matrix
            pixel_position_3d = transformation_matrix @ Vector((uv.x - 0.5, uv.y - 0.5, 0))  # Center the UV to match the image plane

            # Get the corresponding UV coordinates on the target object by raycasting from the pixel's 3D position
            uv_coord = get_uv_from_3d_point(obj, pixel_position_3d, ray_direction)
            if uv_coord is None:
                continue  # Skip if no UV was found (no intersection)

            # Sample the texture at the pixel's UV coordinates
            red, green, blue, alpha = sample_texture_at_uv(image_plane, uv)

            # Use the red channel (or others) as the weight value
            weight_value = red

            # Find the closest vertex on the target object
            closest_vertex = None
            min_distance = float('inf')
            for vertex in bm.verts:
                distance = (vertex.co - pixel_position_3d).length
                if distance < min_distance:
                    min_distance = distance
                    closest_vertex = vertex

            # Assign the weight to the closest vertex
            if closest_vertex is not None:
                vertex_group.add([closest_vertex.index], weight_value, 'REPLACE')

    # Update the mesh and free the BMesh
    bm.to_mesh(mesh)
    bm.free()

# Example usage:
image_plane = bpy.data.objects['ImagePlane']  # The object representing the image plane
target_object = bpy.data.objects['TargetObject']  # The object to project the image onto

image_plane_size = (2.0, 1.0)  # Size of the image plane in 3D space (width, height)
project_texture_pixels_to_object(image_plane, target_object, image_plane_size=image_plane_size, rotation=(0.1, 0.2, 0.3))

