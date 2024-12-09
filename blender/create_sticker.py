import bpy
from pathlib import Path
import bmesh
import time
import sys
from mathutils import kdtree, Euler
import heapq
from mathutils import Vector


def progress_bar(iteration, total, length=50):
    percent = 100 * (iteration / float(total))
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '-' * (length - filled_length) 
    # '\r' returns the cursor to the start of the line so we overwrite previous output
    sys.stdout.write(f'\r|{bar}| {percent:.2f}% Complete')
    sys.stdout.flush()  # Ensure the output is printed immediately
    if iteration == total:
        print()  # Move to the next line after completion


def is_in_vertex_group(vert_index, vert_group):
      return vert_group.weight(vert_index) > 0

def arrange_all_groups(source_mesh_name, bm):
    vertex_groups = get_vertex_groups(source_mesh_name)
    vertex_group_dict = {}
    source_obj = bpy.data.objects[source_mesh_name]

    bpy.context.view_layer.objects.active = source_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=True)
    bpy.ops.object.mode_set(mode='OBJECT')

    bm.from_mesh(source_obj.data)
    for v in bm.verts:
        for vertex_group in vertex_groups:
            vertex_group_name = vertex_group.name
            try:
                if is_in_vertex_group(v.index, vertex_group):
                    # Assign the weight to the target group
                    weight = vertex_group.weight(v.index)
                    v_world = source_obj.matrix_world @ v.co
                    if vertex_group_name in vertex_group_dict:
                        vertex_group_dict[vertex_group_name][v.index] = {"weight": weight, "world": v_world, "vertex": v}
                    else:
                        vertex_group_dict[vertex_group_name] = {}
                        vertex_group_dict[vertex_group_name][v.index] = {"weight": weight, "world": v_world, "vertex": v}
            except RuntimeError as e:
                #Error: Vertex not in group
                continue
    return vertex_group_dict

def arrange_vertex_group(source_mesh_name, bm, vertex_group_name):
    source_obj = bpy.data.objects[source_mesh_name]

    vertex_group = source_obj.vertex_groups.get(vertex_group_name)
    vertex_group_dict = {}
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
    for v in bm.verts:
        try:
            if is_in_vertex_group(v.index, vertex_group):
                # Assign the weight to the target group
                weight = vertex_group.weight(v.index)
                v_world = source_obj.matrix_world @ v.co
                if vertex_group_name in vertex_group_dict:
                    vertex_group_dict[vertex_group_name][v.index] = {"weight": weight, "world": v_world, "vertex": v}
                else:
                    vertex_group_dict[vertex_group_name] = {}
                    vertex_group_dict[vertex_group_name][v.index] = {"weight": weight, "world": v_world, "vertex": v}
        except RuntimeError as e:
            #Error: Vertex not in group
            continue
    return vertex_group_dict

# this function is meant to be used in a for loop, looping through all of the bones/vertex groups on an armature/meshG
# for mods, the bone names should be the same for both armatures
def create_weight_sticker(vertex_group_dictionaries, source_mesh_name, source_vertex_group_name, output_path):
    source_mesh = bpy.data.objects[source_mesh_name]
    # 1) create list of all non zero vertices for a vertex group
    source_selected_vertices = vertex_group_dictionaries[source_vertex_group_name]
    # create color attribute for mesh
    create_color_attribute(source_selected_vertices, source_mesh)
    #bake attributes to an image
    selected_verts_indices = [i for i in source_selected_vertices]
    
    bpy.context.view_layer.objects.active = source_mesh
    source_mesh.select_set(True)

    bpy.ops.object.duplicate_move(
        OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'}, 
        TRANSFORM_OT_translate={"value": (0, 0, 0)}
    )

    # Get the new active object, which is the duplicated one
    duplicated_object = bpy.context.active_object

    delete_unwanted_vertices(duplicated_object, selected_verts_indices)

    #redo UV maps
    bpy.context.view_layer.objects.active = duplicated_object
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0)
    bpy.ops.object.mode_set(mode='OBJECT')

    bake_weights(source_vertex_group_name, duplicated_object, output_path)
    
    #delete new object
    bpy.context.view_layer.objects.active = duplicated_object
    duplicated_object.select_set(True)
    bpy.ops.object.delete()


def delete_unwanted_vertices(obj, vertices_to_keep):
    # Set the object as active and switch to edit mode
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')

    # Get the BMesh representation of the object in edit mode
    bm = bmesh.from_edit_mesh(obj.data)

    # Deselect all vertices
    bpy.ops.mesh.select_all(action='DESELECT')

    # Loop through all vertices in the mesh
    for v in bm.verts:
        if v.index not in vertices_to_keep:
            # Select the vertices not in the list of vertices to keep
            v.select = True
        else:
            v.select = False  # Deselect vertices that are to be kept

    # Update the mesh to reflect the selections
    bmesh.update_edit_mesh(obj.data)

    # Delete the selected vertices
    bpy.ops.mesh.delete(type='VERT')

    # Switch back to object mode
    bpy.ops.object.mode_set(mode='OBJECT')



def create_color_attribute(selected_vertices, mesh):
    # Iterate over and remove all color attributes
    while len(mesh.data.color_attributes) > 0:
        mesh.data.color_attributes.remove(mesh.data.color_attributes[0])

    color_layer = mesh.data.color_attributes.get("WeightColor")
    if not color_layer:
        color_layer = mesh.data.color_attributes.new(name="WeightColor", type='FLOAT_COLOR', domain='POINT')

    for idx in selected_vertices:
        weight = selected_vertices[idx]["weight"]
        color_layer.data[idx].color = weight_to_rgb(weight)

    # Update the mesh to reflect the changes
    mesh.data.update()

def weight_to_rgb(weight):
    """
    Converts a weight (0.0 - 1.0) to an RGB value using Blender's weight paint color gradient.
    
    :param weight: A float value between 0.0 (blue) and 1.0 (red).
    :return: An (r, g, b) tuple with values between 0.0 and 1.0.
    """
    # Clamp weight between 0.0 and 1.0 to avoid out-of-bounds issues
    weight = max(0.0, min(weight, 1.0))
    
    # Create a temporary material to access the color ramp node
    temp_material = bpy.data.materials.new(name="TempMaterial")
    temp_material.use_nodes = True
    nodes = temp_material.node_tree.nodes
    links = temp_material.node_tree.links
    
    # Create a ColorRamp node
    color_ramp_node = nodes.new(type="ShaderNodeValToRGB")
    color_ramp_node.location = (0, 0)
    
    # Set up a color ramp with Blender-like weight colors
    color_ramp_node.color_ramp.interpolation = 'LINEAR'

    # Define the color stops
    # Add Blue at position 0.0
    blue_element = color_ramp_node.color_ramp.elements[0]
    blue_element.color = (0.0, 0.0, 1.0, 1.0)  # Blue (RGBA)

    # Add Red at position 1.0
    red_element = color_ramp_node.color_ramp.elements[1]
    red_element.color = (1.0, 0.0, 0.0, 1.0)  # Red 

    # Add Green at position 0.5
    green_element = color_ramp_node.color_ramp.elements.new(0.5)
    green_element.color = (0.0, 1.0, 0.0, 1.0)  # Green (RGBA)
    
    # Evaluate the color ramp at the given weight
    rgb = color_ramp_node.color_ramp.evaluate(weight)
    
    # Clean up: remove the temporary material
    bpy.data.materials.remove(temp_material, do_unlink=True)
    
    return rgb


def create_weight_material(obj, image_path, material_name="Weights"):

    # Ensure the object has a material
    if material_name in obj.data.materials:
        index = get_material_index(obj, material_name)
        mat = obj.data.materials[index]
    else:
        mat = bpy.data.materials.new(name=material_name)
        obj.data.materials.append(mat)

    # Enable 'Use Nodes'
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear existing nodes
    for node in nodes:
        nodes.remove(node)

    # Add required nodes
    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    principled_node = nodes.new(type="ShaderNodeBsdfPrincipled")
    image_texture_node = nodes.new(type="ShaderNodeTexImage")
    mapping_node = nodes.new(type="ShaderNodeMapping")
    texture_coord_node = nodes.new(type="ShaderNodeTexCoord")

    # Position nodes
    output_node.location = (400, 0)
    principled_node.location = (200, 0)
    image_texture_node.location = (0, 200)
    mapping_node.location = (-200, 200)
    texture_coord_node.location = (-400, 200)

    # Link nodes
    links.new(principled_node.outputs['BSDF'], output_node.inputs['Surface'])
    links.new(image_texture_node.outputs['Color'], principled_node.inputs['Base Color'])
    links.new(mapping_node.outputs['Vector'], image_texture_node.inputs['Vector'])
    links.new(texture_coord_node.outputs['UV'], mapping_node.inputs['Vector'])

    # Load an image
    image_texture_node.image = bpy.data.images.load(image_path)
    
    info = {
            "nodes": nodes,
            "links": links,
            "output_node": output_node,
            "principled_node": principled_node,
            "image_texture_node": image_texture_node,
            "mapping_node": mapping_node,
            "texture_coord_node": texture_coord_node
            }

    return info

def convert_texture_rotation(mapping_rotation):
    local_rotation = Euler(mapping_rotation, 'XYZ').to_matrix().to_4x4()
    return local_rotation

def transform_image_texture(obj, image_path, location, rotation, scale):

    info = create_weight_material(obj, image_path, material_name="Weights")
    mapping_node = info["mapping_node"]
    mapping_node.inputs['Location'].default_value = location
    mapping_node.inputs['Rotation'].default_value = rotation  
    mapping_node.inputs['Scale'].default_value = scale  
    # Adjust Mapping node
    #mapping_node.inputs['Location'].default_value = (1.0, 1.0, 0.0)  # Adjust location
    #mapping_node.inputs['Rotation'].default_value = (0.0, 0.0, 0.5)  # Adjust rotation
    #mapping_node.inputs['Scale'].default_value = (2.0, 2.0, 1.0)  # Adjust scale


def get_material_index(obj, material_name):
    if obj and obj.data.materials:
        for i, mat in enumerate(obj.data.materials):
            if mat and mat.name == material_name:
                return i
    return -1  # Return -1 if the material is not found


# Saving user settings
def bake_weights(vertex_group_name, obj, output_path):
    # Ensure the object has a material
    if len(obj.data.materials) == 0:
        mat = bpy.data.materials.new(name="Baking_Material")
        obj.data.materials.append(mat)
    else:
        mat = obj.data.materials[0]

    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    # Clear existing nodes
    for node in nodes:
        nodes.remove(node)

    # Create new nodes for baking
    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    diffuse_node = nodes.new(type="ShaderNodeBsdfDiffuse")
    vertex_color_node = nodes.new(type="ShaderNodeVertexColor")
    texture_node = nodes.new(type="ShaderNodeTexImage")

    # Set up the node tree, connect the nodes
    mat.node_tree.links.new(vertex_color_node.outputs['Color'], diffuse_node.inputs['Color'])
    mat.node_tree.links.new(diffuse_node.outputs['BSDF'], output_node.inputs['Surface'])


    scene = bpy.context.scene
    default_render_engine = scene.render.engine
    default_view_transform = scene.view_settings.view_transform
    default_display_device = scene.display_settings.display_device
    default_file_format = scene.render.image_settings.file_format
    default_color_mode = scene.render.image_settings.color_mode
    default_codec = scene.render.image_settings.exr_codec
    default_denoise = scene.cycles.use_denoising
    default_compute_device = scene.cycles.device
    default_scene_samples = scene.cycles.samples

    render_resolution = 2048

    try:
        # Prepare baking
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 128
        scene.cycles.use_denoising = False
        scene.cycles.device = 'GPU'

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)  # Select the object to be baked
        bpy.context.view_layer.objects.active = obj  # Make it the active object
        texture_image = bpy.data.images.new(
            name=vertex_group_name, width=render_resolution, height=render_resolution, alpha=True, float_buffer=True
        )
        pixels = [0.0, 0.0, 0.0, 0.0] * render_resolution * render_resolution
        texture_image.pixels = pixels

        texture_image.filepath_raw = output_path
        scene.render.image_settings.file_format = 'OPEN_EXR'
        scene.render.image_settings.color_mode = 'RGB'
        scene.render.image_settings.exr_codec = 'NONE'

        texture_image.use_half_precision = False
        texture_image.colorspace_settings.is_data = True
        #texture_image.colorspace_settings.name = 'Non-Color'
        texture_node.image = texture_image
        texture_node.select = True
        
        # Bake
        # Set the bake type to 'DIFFUSE'
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'

        # Disable Direct and Indirect influences, only leaving Color enabled
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True

        bpy.ops.object.bake(type='DIFFUSE')
        # save as render so we have more control over compression settings
        texture_image.save_render(
            filepath=bpy.path.abspath(output_path), scene=scene, quality=0
        )
        # Removes the dirty flag, so the image doesn't have to be saved again by the user.
        texture_image.pack()
        texture_image.unpack(method='REMOVE')
        
    except BaseException as e:
        print(e)
        print("ERROR")

    finally:
        scene.render.image_settings.file_format = default_file_format
        scene.render.image_settings.color_mode = default_color_mode
        scene.render.image_settings.exr_codec = default_codec
        scene.cycles.samples = default_scene_samples
        scene.display_settings.display_device = default_display_device
        scene.view_settings.view_transform = default_view_transform
        scene.cycles.use_denoising = default_denoise
        scene.cycles.device = default_compute_device
        scene.render.engine = default_render_engine

def get_weight_area_center(vertex_group_dictionaries, source_vertex_group_name, source_obj, kdt):
    vertex_information = vertex_group_dictionaries[source_vertex_group_name]
    source_selected_vertices = [vertex_information[v_idx]["world"] for v_idx in vertex_information]
    length = len(source_selected_vertices)
    center = sum(source_selected_vertices, Vector()) / length # look up this syntas again
    #vertex_group_dict[vertex_group_name][v.index] = {"weight": weight, "world": v_world, "vertex": v}
    vertex_index = get_closest_vertex_on_mesh_with_kdtree(center, kdt)
    closest_vertex = source_obj.data.vertices[vertex_index]
    return closest_vertex


def mark_location(vertex):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=vertex)

def get_vertex_groups(mesh_name):
    vertex_groups = bpy.data.objects[mesh_name].vertex_groups
    return vertex_groups

source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"

bm = bmesh.new() #bmesh where you will put copy of source vertex
vertex_group_dictionary = arrange_all_groups(source_mesh_name, bm)
total_groups = len(vertex_group_dictionary)
for idx, source_vertex_group_name in enumerate(vertex_group_dictionary):
    image_path = str(Path("E:/MODS/scripts") / "EXAMPLE" / f"{source_vertex_group_name}.exr")
    create_weight_sticker(vertex_group_dictionary, source_mesh_name, source_vertex_group_name, image_path)
    progress_bar(idx, total_groups)

