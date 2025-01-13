import bpy
import bmesh

def paint_hair_top(object_name):

    # Ensure you're in Object Mode
    if bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Example usage:
    obj = bpy.data.objects.get(object_name)

    if not obj or obj.type != 'MESH':
        print("Please select a mesh object.")
    else:
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        # Select the active object
        obj.select_set(True)

        # Separate the object by loose parts
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')

        # Get the new objects (all loose parts)
        loose_parts = bpy.context.selected_objects


        
        for part in loose_parts:

            bpy.context.view_layer.objects.active = part
            bpy.ops.paint.weight_gradient(xstart=151, xend=957, ystart=617, yend=359, flip=False)

            # Get mesh data
            mesh = part.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            
            bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
            # Ensure the UV map is active
            if not bm.loops.layers.uv:
                print(f"No UV map for object: {obj.name}")
                continue
            
            uv_layer = bm.loops.layers.uv.active
            
            # Find the top (highest v) vertices in the UV map
            uv_coords = [(loop[uv_layer].uv, vert) for face in bm.faces for loop, vert in zip(face.loops, face.verts)]
            max_v = max(uv_coords, key=lambda uv_vert: uv_vert[0].y)[0].y
            min_v = max_v - 0.2  # 20% down
            # Paint gradient
            for uv, vert in uv_coords:
                # Calculate weight based on gradient
                if uv.y >= max_v:
                    weight = 1.0  # Fully weighted
                elif uv.y < min_v:
                    weight = 0.0  # No weight
                else:
                    weight = (uv.y - min_v) / (max_v - min_v)
                
                # Set weight for the vertex
                for vg in obj.vertex_groups:
                    vg.add([vert.index], weight, 'REPLACE')
            
            # Update the mesh
            bm.to_mesh(mesh)
            bm.free()
            
            # Set the mode back to Object after painting
            bpy.ops.object.mode_set(mode='OBJECT')


        # Select all the loose parts
        for obj in loose_parts:
            obj.select_set(True)

        # Set the first loose part as active for joining
        bpy.context.view_layer.objects.active = loose_parts[0]

        # Join the loose parts back into one object
        bpy.ops.object.join()

        # Print the new object's name
        print("New Object Name:", bpy.context.object.name)


paint_hair_top("LOD_1_Group_0_Sub_1__esf_Hair00")
