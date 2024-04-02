"""
The assumption is that you are creating a stamp for the same bone on a duplicate of the same armature that is the parent of a different mesh. So the bone your transfering the stamp to should have the same name

SETUP
0) Pick the source and target armatures
1) Assume the target armature is already parented to the target mesh

GET WEIGHTS
1) get the weights for each vertex in a vertex groups for a single bone 
2) pick a central vertex in the vertex group to which all other vertices will translate/rotate in relation to 

TRANSFER TO NEW ARMATURE
3) move weights all at the same time to the target bone (retarget)
4) allow on mouse movement to translate the whole weight painting map for a bone

"""
import bpy
import mathutils

#get mesh from armature
def get_mesh_from_armature(armature_name):
    armature = bpy.data.objects[armature_name]
    modifiers = [modifier for modifier in armature.modifiers if modifier.type == "ARMATURE"]
    mesh_object = modifiers[0].object
    if mesh_object and mesh_object.type == 'MESH':
        print("Mesh object associated with the armature:", mesh_object.name)
        return mesh_object



#1) get the weights for each vertex in a vertex groups for a single bone 
def estimate_target_vertex(source_vertex):
    



#2) pick a central vertex in the vertex group to which all other vertices will translate/rotate in relation to 
def get_center_of_surface_area():



def is_in_vertex_group(vert_index, vert_group):
      return vert_group.weight(vert_index) > 0


#4) allow on mouse movement to translate the whole weight painting map for a bone
def transfer_weights(source_armature_name, target_armature_name, source_mesh_name, target_mesh_name):

    # Switch to object mode NOTE: need to figure out why I need to do this
    bpy.ops.object.mode_set(mode='OBJECT')

    #loop through source bones / target ones will be the same names
    for source_vertex_group in bpy.data.objects[source_armature_name].pose.bones:
        # make sure vertex group name is in mesh list of vertex groups
        if source_vertex_group in bpy.data.objects[source_mesh_name].vertex_groups:

            #first check if target_vertex_group already exists
            target_vertex_group = bpy.data.objects[target_mesh_name].vertex_groups.get(source_vertex_group)

            if target_vertex_group is None:
                target_vertex_group = bpy.data.objects[target_mesh_name].vertex_groups.new(name=source_vertex_group)
            
            #go through source mesh vertices to get weights for each vertex in source vertex group
            mesh_data = bpy.data.objects[source_mesh_name].data

    
            # Loop through all vertices
            for v in mesh_data.vertices:
                # Get the weight of the vertex in the source group
                try:
                    #check if the vertex is in the source vertex group
                    # a single vertex can belong to multiple vertex groups
                    if is_in_vertex_group(v.index, source_vertex_group):
                        # Assign the weight to the target group
                        weight = source_vertex_group.weight(v.index)

                        """
                            May want to cache all of the weights somehow, then have a while loop run while you use mouse events to decide where to translate the weights stamp and then have a 
                            key to both place the map and jump out of the while loop
                        """




                        target_vertex = estimate_target_vertex(v)
                        if target_vertex:
                            target_vertex_group.add([target_vertex.index], weight, 'REPLACE')
                except RuntimeError as e:
                    print(e)

            print(f"Vertex group weights transferred from {source_bone_name} to {target_bone_name}")
        else:
            print(f"Vertex group '{source_bone_name}' not found.")
    else:
        print("Source or target bone not found.")



# use an empty object to rotate and translate weight paint stamp




def rotate_weights():

