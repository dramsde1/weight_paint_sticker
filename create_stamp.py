import bpy
from pathlib import Path
import bmesh


#1) get the weights for each vertex in a vertex groups for a single bone 
def is_in_vertex_group(vert_index, vert_group):
      return vert_group.weight(vert_index) > 0


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
def create_weight_stamp(vertex_group_dictionaries, source_mesh_name, source_vertex_group_name, output_path):
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
output_path = str(Path("E:/MODS/scripts") / "weight_paint_stamp" / f"{source_vertex_group_name}.exr")
#vertex_group_dictionaries = arrange_all_groups(source_mesh_name, bm)
vertex_group_dictionary = arrange_vertex_group(source_mesh_name, bm, source_vertex_group_name)
create_weight_stamp(vertex_group_dictionary, source_mesh_name, source_vertex_group_name, output_path)


