import bpy
import mathutils
import site
import pip
from mathutils import Color
from pathlib import Path
from collections import defaultdict
pip.main(['install', 'numpy', '--target', site.USER_SITE])
import bpy
import bmesh
import sys
from mathutils import Vector
from mathutils.kdtree import KDTree
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import numpy as np


from PIL import Image
import numpy as np
from scipy.ndimage import gaussian_filter

def gaussian_sampler(low_res_image_path, upscale_factor=2, sigma=1.0):
    # Open the low-res image
    low_res_img = Image.open(low_res_image_path)
    
    # Convert image to numpy array
    img_np = np.array(low_res_img)
    
    # Apply Gaussian filter to smooth the image
    blurred_img_np = gaussian_filter(img_np, sigma=sigma)
    
    # Convert back to an image
    blurred_img = Image.fromarray(np.uint8(blurred_img_np))
    
    # Calculate new size (upscale)
    new_size = (low_res_img.size[0] * upscale_factor, low_res_img.size[1] * upscale_factor)
    
    # Upscale the image using bicubic interpolation
    high_res_img = blurred_img.resize(new_size, Image.BICUBIC)
    
    return high_res_img

# Example usage:
high_res_image = gaussian_sampler('low_res_image.png', upscale_factor=4, sigma=1.5)
high_res_image.show()  # To display the image
high_res_image.save('high_res_image.png')  # Save the upscaled image

#START



#1) get the weights for each vertex in a vertex groups for a single bone 
def is_in_vertex_group(vert_index, vert_group):
      return vert_group.weight(vert_index) > 0

def find_center(vertex_group_name, mesh):
    context = bpy.context
    ob = mesh
    bpy.ops.object.empty_add(location=(0, 0, 0))
    mt = context.object
    mt.name = f"{ob.name}_{vertex_group_name}"
    cl = mt.constraints.new('COPY_LOCATION')
    cl.target = ob
    cl.subtarget = vertex_group_name
    #To go to any next step that requires the empties to be at the constrained locations throw in a scene update to ensure matrices etc are up to date.
    dg = context.evaluated_depsgraph_get()
    dg.update()
    #get global location
    loc = mt.matrix_world.translation # global location of emtpy
    # remove the mt
    bpy.data.objects.remove(mt)
    return loc


def distance_from_center(center, vertex_island_dict, source_mesh):
    distance_dict = {}
    for v in vertex_island_dict:
        vector = (source_mesh.matrix_world @ v.co - center)
        #distance = vector.length
        distance = vector
        weight = vertex_island_dict[v]
        distance_dict[v] = {"distance": distance, "weight": weight}
    return distance_dict


def arrange_all_groups(source_mesh_name, bm):
    vertex_groups = get_vertex_groups(source_mesh_name)
    vertex_group_dict = {}
    source_obj = bpy.data.objects[source_mesh_name]
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
    #for v in mesh_data.vertices:
    for v in bm.verts:
        for source_vertex_group in vertex_groups:
            try:
                if is_in_vertex_group(v.index, source_vertex_group):
                    # Assign the weight to the target group
                    weight = source_vertex_group.weight(v.index)
                    if source_vertex_group.name in vertex_group_dict:
                        vertex_group_dict[source_vertex_group.name][v] = weight
                    else:
                        vertex_group_dict[source_vertex_group.name] = {}
                        vertex_group_dict[source_vertex_group.name][v] = weight
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
def remap_vertex_groups(vertex_group_dictionaries, source_armature_name, target_armature_name, source_mesh_name, target_mesh_name, source_vertex_group_name, empty_name):
    target_mesh = bpy.data.objects[target_mesh_name]
    source_mesh = bpy.data.objects[source_mesh_name]
    empty_obj = bpy.data.objects[empty_name]
    # Get the world coordinates of the empty object
    empty_world_coords = empty_obj.matrix_world.translation
    #for source_vertex_group_name in vertex_group_dictionaries:
    center_point = find_center(source_vertex_group_name, source_mesh)

    # 1) create list of all non zero vertices for a vertex group
    source_selected_vertices = vertex_group_dictionaries[source_vertex_group_name]


    # 2) get the smallest rectangle that encompases those vertices 



def create_color_attribute(selected_vertices, mesh):
    color_layer = mesh.color_attributes.get("WeightColor")
    if not color_layer:
        color_layer = mesh.color_attributes.new(name="WeightColor", type='FLOAT_COLOR', domain='POINT')

    for idx in selected_vertices:
        weight = selected_vertices[idx]["weight"]
        color_layer.data[idx].color = weight_to_rgb(weight)

    # Update the mesh to reflect the changes
    mesh.update()


def weight_to_rgb(weight):
    """
    Converts a weight (0.0 - 1.0) to an RGB value using Blender's weight paint color gradient.
    
    :param weight: A float value between 0.0 (blue) and 1.0 (red).
    :return: An (r, g, b) tuple with values between 0.0 and 1.0.
    """
    # Clamp weight between 0.0 and 1.0 to avoid out-of-bounds issues
    weight = max(0.0, min(weight, 1.0))
    
    # Create a color object from Blender's default weight color ramp
    color_ramp = bpy.data.node_groups['Shader Nodetree'].nodes.new('ShaderNodeValToRGB')
    
    # Set up a color ramp with Blender-like weight colors
    color_ramp.color_ramp.interpolation = 'LINEAR'
    
    # Define colors (Blender weight paint standard)
    color_ramp.color_ramp.elements.new(0.0)
    color_ramp.color_ramp.elements.new(1.0)
    
    # Assign weight colors (blue -> green -> red)
    color_ramp.color_ramp.elements[0].color = (0.0, 0.0, 1.0, 1.0)  # Blue (weight 0)
    color_ramp.color_ramp.elements[1].color = (1.0, 0.0, 0.0, 1.0)  # Red (weight 1)
    
    # Evaluate color ramp at the given weight
    rgb = color_ramp.color_ramp.evaluate(weight)
    
    # Cleanup created nodes
    bpy.data.node_groups.remove(color_ramp.id_data)
    
    return rgb  # Return RGB values 



 # Saving user settings
def bake_weights(vertex_group_name, obj):
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
    vc_node = nodes.new(type="ShaderNodeVertexColor")
    texture_node = nodes.new(type="ShaderNodeTexImage")

    # Set up the node tree, connect the nodes
    mat.node_tree.links.new(vc_node.outputs['Color'], diffuse_node.inputs['Color'])
    mat.node_tree.links.new(diffuse_node.outputs['BSDF'], output_node.inputs['Surface'])
    mat.node_tree.links.new(texture_node.outputs['Color'], diffuse_node.inputs['Color'])


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
        output_path = Path().cwd() / f"{vertex_group_name}.exr"
        texture_image = bpy.data.images.new(
            name=vertex_group_name, width=render_resolution, height=render_resolution, alpha=False, float_buffer=True
        )

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
        bpy.ops.object.bake(type='EMIT')
        # save as render so we have more control over compression settings
        texture_image.save_render(
            filepath=bpy.path.abspath(output_path), scene=scene, quality=0
        )
        # Removes the dirty flag, so the image doesn't have to be saved again by the user.
        texture_image.pack()
        texture_image.unpack(method='REMOVE')

    except BaseException as Err:
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





def mark_location(vertex):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=vertex)

def get_vertex_groups(mesh_name):
    vertex_groups = bpy.data.objects[mesh_name].vertex_groups
    return vertex_groups

#source_mesh_name = "source"
#target_mesh_name = "target"
#source_armature_name = "source_arm"
#target_armature_name = "target_arm"

source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
target_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head.001"
source_armature_name = "Root.002"
target_armature_name = "Root.001"

#get the source and target 
#source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
#target_mesh_name = "Cube"
#source_armature_name = "Root.002"
#target_armature_name = "Root.001"
source_vertex_group_name = "C_nose_Top"
empty_name = "Empty"
bm = bmesh.new() #bmesh where you will put copy of source vertex
#vertex_group_dictionaries = arrange_all_groups(source_mesh_name, bm)
vertex_group_dictionary = arrange_vertex_group(source_mesh_name, bm, source_vertex_group_name)
remap_vertex_groups(vertex_group_dictionary, source_armature_name, target_armature_name, source_mesh_name, target_mesh_name, source_vertex_group_name, empty_name)


