import bpy
import bmesh
from mathutils import Vector, Matrix

# Function to create a transformation matrix (translation, scale, rotation)
def create_transformation_matrix(translation=(0, 0, 0), scale=(1, 1, 1), rotation=(0, 0, 0)):
    # Create individual translation, rotation, and scale matrices
    translation_matrix = Matrix.Translation(Vector(translation))
    rotation_matrix_x = Matrix.Rotation(rotation[0], 4, 'X')
    rotation_matrix_y = Matrix.Rotation(rotation[1], 4, 'Y')
    rotation_matrix_z = Matrix.Rotation(rotation[2], 4, 'Z')
    scale_matrix = Matrix.Diagonal(Vector(scale + (1,)))
    
    # Combine them into a single transformation matrix
    transformation_matrix = translation_matrix @ rotation_matrix_x @ rotation_matrix_y @ rotation_matrix_z @ scale_matrix
    return transformation_matrix

# Function to get UV coordinates of a 3D point projected onto the mesh
def get_uv_from_3d_point(obj, point):
    # Ensure the object is in object mode and has UVs
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get the mesh and create a BMesh for it
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        raise Exception("No UV map found on mesh!")

    # Cast a ray to project the 3D point onto the surface of the mesh
    ray_origin = point
    ray_direction = Vector((0, 0, -1))  # Assuming the ray is cast downwards
    
    # Perform ray casting
    result, location, normal, index, obj, matrix = obj.ray_cast(ray_origin, ray_direction)
    
    if result:
        # Get the face hit by the ray
        face = bm.faces[index]
        
        # Find the UV coordinate on the face using barycentric interpolation
        for loop in face.loops:
            uv = loop[uv_layer].uv
            return uv
    else:
        return None

# Function to find the closest vertex on the object to a 3D point
def find_closest_vertex(bm, point):
    closest_vert = None
    min_dist = float('inf')

    for vert in bm.verts:
        dist = (vert.co - point).length
        if dist < min_dist:
            min_dist = dist
            closest_vert = vert

    return closest_vert

# Main function to project image pixels as vertex weights
def project_image_weights(image_path: str, translation=(0, 0, 0), scale=(1, 1, 1), rotation=(0, 0, 0)):
    # Load the image
    image = bpy.data.images.load(image_path)
    width, height = image.size

    # Create the transformation matrix for the image's placement in 3D space
    transformation_matrix = create_transformation_matrix(translation, scale, rotation)

    # Select the object and ensure it has a UV map
    obj = bpy.context.object
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        raise Exception("No UV map found on mesh!")

    # Create a new vertex group for weight painting
    vertex_group = obj.vertex_groups.new(name="WeightPaint")

    # Loop through each pixel in the image
    for y in range(height):
        for x in range(width):
            # Sample the pixel color from the image
            pixel_index = (y * width + x) * 4
            red, green, blue, alpha = image.pixels[pixel_index:pixel_index + 4]
            
            # Use the red channel (or other channels) as the weight value
            weight_value = red

            # Convert pixel coordinates to normalized UV space
            uv = Vector((x / width, y / height))

            # Convert UV space to 3D space using the transformation matrix
            point_in_3d_space = Vector((uv.x, uv.y, 0)) @ transformation_matrix
            
            # Find the closest vertex to the projected pixel
            closest_vertex = find_closest_vertex(bm, point_in_3d_space)
            if closest_vertex:
                # Assign the weight to the closest vertex
                vertex_group.add([closest_vertex.index], weight_value, 'REPLACE')

    # Update the mesh and free the BMesh
    bm.to_mesh(mesh)
    bm.free()

# Example usage
project_image_weights("/path/to/your/image.png", translation=(0.1, 0.2, 0.3), scale=(1.2, 1.2, 1.2), rotation=(0.1, 0.2, 0.3))

