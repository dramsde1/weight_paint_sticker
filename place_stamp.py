import bpy
import bmesh
import mathutils

def get_mouse_raycast(context, event):
    """Raycast to get the hit location on the object based on mouse position."""
    # Get the region, region data, and view vector
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y

    # Cast the ray
    view_vector = bpy.context.region_data.view_rotation @ mathutils.Vector((0.0, 0.0, -1.0))
    ray_origin = context.region_data.view_location

    # Get the active object and cast the ray
    result, location, normal, face_index = context.object.ray_cast(ray_origin, view_vector)

    if result:
        return location, face_index
    return None, None

def project_uv_to_location(obj, location, face_index):
    """Get the UV coordinates from the 3D location on the object"""
    mesh = obj.data
    uv_layer = mesh.uv_layers.active.data

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()

    face = bm.faces[face_index]

    # Loop through the face's loops to find UV coordinates
    for loop in face.loops:
        loop_vert = loop.vert
        vert_location = obj.matrix_world @ loop_vert.co

        if (vert_location - location).length < 0.001:
            uv_coords = loop[uv_layer].uv
            return uv_coords
    return None

class ModalTexturePlacer(bpy.types.Operator):
    """Modal operator to place a texture based on mouse click"""
    bl_idname = "object.texture_place_modal"
    bl_label = "Texture Place Modal"
    bl_options = {'REGISTER', 'UNDO'}

    def __init__(self):
        self.obj = None
        self.image_texture_node = None
        self.material = None
        self.image = None

    # Define properties that can be passed as parameters
    object_name: bpy.props.StringProperty(name="My String", default="Hello")
    image_name: bpy.props.StringProperty(name="My String", default="Hello")

    def modal(self, context, event):
        if event.type == 'LEFTMOUSE':  # Mouse left-click
            location, face_index = get_mouse_raycast(context, event)
            if location:
                # Get UV coordinates for the location
                uv_coords = project_uv_to_location(self.obj, location, face_index)
                
                if uv_coords:
                    print(f"Projected UV coordinates: {uv_coords}")
                    # Here you can move or adjust the image texture based on UV coordinates
                    self.image_texture_node.texture_mapping.translation = uv_coords

            return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:  # Cancel
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

def invoke(self, context, event):
    self.obj = bpy.data.objects.get(self.object_name)
    
    #add material and move to the top
    self.material = bpy.data.materials.new(name="PlaceStampMaterial")
    self.obj.data.materials.append(self.material)

    #move material to the top
    mat_slots = self.obj.material_slots
    for _ in range(len(mat_slots) - 1):
        bpy.ops.object.material_slot_move(direction='UP')



    self.material.use_nodes = True
    nodes = self.material.node_tree.nodes
    links = self.material.node_tree.links

    # Create an Image Texture node
    self.image_texture_node = nodes.new(type="ShaderNodeTexImage")
    self.image_texture_node.image = bpy.data.images.load(self.image_name)
    
    #remove bsdf in place for diffuse 
    bsdf_node = nodes.get("Principled BSDF")
    if bsdf_node:
        nodes.remove(bsdf_node)


    # Create new nodes for baking
    output_node = nodes.new(type="ShaderNodeOutputMaterial")
    diffuse_node = nodes.new(type="ShaderNodeBsdfDiffuse")

    # Set up the node tree, connect the nodes
    self.material.node_tree.links.new(self.image_texture_node.outputs['Color'], diffuse_node.inputs['Color'])
    self.material.node_tree.links.new(diffuse_node.outputs['BSDF'], output_node.inputs['Surface'])

    context.window_manager.modal_handler_add(self)
    return {'RUNNING_MODAL'}

# Register and start the operator
bpy.utils.register_class(ModalTexturePlacer)
bpy.ops.object.texture_place_modal('INVOKE_DEFAULT')
