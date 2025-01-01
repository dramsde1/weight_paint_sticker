import bpy
from pathlib import Path
import json

def compare_vertex_groups(source, target):
    # Ensure both objects are valid meshes
    if source.type != 'MESH' or target.type != 'MESH':
        print("Both objects must be meshes.")
        return None

    # Get the vertex group names for each object
    vertex_groups_source = sorted([vg.name for vg in source.vertex_groups])
    vertex_groups_target = sorted([vg.name for vg in target.vertex_groups])
    source_list = len(vertex_groups_source)
    target_list = len(vertex_groups_target)

    left_overs = []
    for i in vertex_groups_source:
        if i not in vertex_groups_target:
            left_overs.append(i)

    path = "E:\MODS\scripts\compare_vertex_groups.txt"

    with open(path, "w") as file:
        for item in left_overs:
            file.write(item + "\n")

    return left_overs 


def delete_vertex_groups_from_file():
    object_name = "low_head"
    obj = bpy.data.objects.get(object_name)

    folder_path = "E:\MODS\scripts\slickback_weight_textures"
    directory = Path(folder_path)

    for file_path in directory.glob("*.exr"):  
        group_name = Path(file_path).stem
        # Ensure the active object is a mesh
        obj = bpy.context.object
        if obj and obj.type == 'MESH':
            vertex_group = obj.vertex_groups.get(group_name)
            if vertex_group:
                # Remove the vertex group
                obj.vertex_groups.remove(vertex_group)
        else:
            print("Active object is not a mesh.")



def ensure_mirrored_vertex_groups(obj):
    # Ensure the object is a mesh
    if obj.type != 'MESH':
        print("Object is not a mesh.")
        return
    
    # Get the list of existing vertex group names
    existing_groups = {vg.name for vg in obj.vertex_groups}
    
    # Iterate over vertex groups that start with "L_"
    for vg_name in existing_groups:
        if vg_name.startswith("L_"):
            # Create the mirrored group name
            mirrored_name = vg_name.replace("L_", "R_", 1)  # Replace only the first occurrence
            
            # Check if the mirrored group exists
            if mirrored_name not in existing_groups:
                # Add the mirrored vertex group
                obj.vertex_groups.new(name=mirrored_name)
                print(f"Added mirrored vertex group: {mirrored_name}")


# Example usage
source = bpy.data.objects.get("LOD_1_Group_0_Sub_3__esf_Head00")  # Replace with your object name
target = bpy.data.objects.get("low_head")  # Replace with your object name

if source and target:
    unique_vertex_groups = compare_vertex_groups(source, target)
else:
    print("One or both objects not found.")
