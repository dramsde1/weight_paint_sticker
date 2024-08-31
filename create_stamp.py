import bpy
import mathutils
import site
import pip

#pip.main(['install', 'dask', '--target', site.USER_SITE])
import bpy
import bmesh
from mathutils.bvhtree import BVHTree
from mathutils import Vector
from collections import defaultdict, deque
import sys

def organize_vertex_groups(source_mesh_name):
    vertex_groups = get_vertex_groups(source_mesh_name)
    vertex_group_dict = {}
    mesh_data = bpy.data.objects[source_mesh_name].data
    # Loop through all vertices to get all non zero weights and their vertex coordinates
    for v in mesh_data.vertices:
        for vg in vertex_groups:
            source_vertex_group = vg
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


def mark_location(vertex):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=vertex)

def get_vertex_groups(mesh_name):
    vertex_groups = bpy.data.objects[mesh_name].vertex_groups
    return vertex_groups

#source_mesh_name = "source"
#target_mesh_name = "target"
#source_armature_name = "source_arm"
#target_armature_name = "target_arm"

#source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
#target_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head.001"
#source_armature_name = "Root.002"
#target_armature_name = "Root.001"

#get the source and target 
source_mesh_name = "LOD_1_Group_0_Sub_3__esf_Head00"
target_mesh_name = "Cube"
source_armature_name = "Root.002"
target_armature_name = "Root.001"
source_vertex_group_name = ""

source_obj = bpy.data.objects.get(source_mesh_name)
target_obj = bpy.data.objects.get(target_mesh_name)
source_armature = bpy.data.objects[source_armature_name]
target_armature = bpy.data.objects[target_armature_name]

if not source_obj or not target_obj:
    print("Source or target object not found.")
    sys.exit()

# Switch to object mode to avoid issues
bpy.ops.object.mode_set(mode='OBJECT')

# Get the mesh data
source_mesh = source_obj.data
target_mesh = target_obj.data

# Create a KDTree for the target mesh (faster ray casting)
bm = bpy.context.evaluated_depsgraph_get()
kd_tree = mathutils.bvhtree.BVHTree.FromObject(target_obj, bm)

vertex_group_dictionaries = organize_vertex_groups(source_mesh_name)

#for source_vertex_group_name in vertex_group_dictionaries:
source_bone = source_armature.pose.bones.get(source_vertex_group_name)
target_bone = target_armature.pose.bones.get(source_vertex_group_name)

selected_vertex_group = vertex_group_dictionaries[source_vertex_group_name]


# Loop through each vertex in the source mesh
for vertex in selected_vertex_group:
    # Transform the vertex position to world coordinates
    world_vertex_position = source_obj.matrix_world @ vertex.co
    
    # Calculate the direction from the vertex to the object's origin
    to_origin = (source_obj.location - source_obj.matrix_world @ vertex.co).normalized()

    if vertex.normal.dot(to_origin) > 0:  # The dot product > 0 means the normal is pointing outward
        # Flip the normal by reversing the face normals associated with the vertex
        for face in vertex.link_faces:
            face.normal_flip()

    # Update the mesh
    bmesh.update_edit_mesh(source_obj.data)

    # Ray cast to find the intersection point on the target mesh
    hit_location, hit_normal, face_index, distance = kd_tree.ray_cast(world_vertex_position, vertex.normal)
    
    if hit_location:
        # you want to get the closest 
        world_hit_location = target_obj.matrix_world.inverted() @ hit_location
        #world_hit_location = target_obj.matrix_world @ hit_location
        nearest = kd_tree.find_nearest(world_hit_location)

        target_vertex_group = target_obj.vertex_groups.get(source_vertex_group_name)
        weight = selected_vertex_group[vertex]
        target_vertex_group.add([nearest.index], weight,'REPLACE')

    #Update the mesh
    #source_mesh.update()
