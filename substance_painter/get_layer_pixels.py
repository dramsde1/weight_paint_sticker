import os
import json
# Substance 3D Painter modules
import substance_painter
from PIL import Image
import substance_painter.export
import substance_painter.project 
import substance_painter.textureset
from pathlib import Path

from PySide2 import QtWidgets

plugin_widgets = []


def get_all_layers(base_output_path: Path):
    """Gets all layers in the current Substance Painter document."""

    if not substance_painter.project.is_open() :
        print("project is not open")
        return None

    root_layer = substance_painter.textureset.get_root_layer()
    layers = [root_layer]

    def traverse_layers(layer):
        for child in layer.children():
            layers.append(child)
            traverse_layers(child)

    traverse_layers(root_layer)
    
    #create dict to store pixel coordinates per image
    pixel_dict = {}

    for layer in layers:

        # Export the layer as a texture
        export_path = str(base_output_path / f"{layer.name()}.png")
        substance_painter.export.export_textures([layer], export_path)
        # Read the exported image
        image = Image.open(export_path)

        from PIL import Image

        # Open the image
        image = Image.open(export_path)

        # Convert the image to RGB if it's not already
        image = image.convert("RGB")

        # Get image dimensions
        width, height = image.size

        # Initialize list for coordinates
        non_black_or_blue_coords = []

        # Iterate through each pixel
        for y in range(height):
            for x in range(width):
                pixel = image.getpixel((x, y))
                # Check if pixel is not black or blue
                if pixel != (0, 0, 0) and pixel != (0, 0, 255):
                    non_black_or_blue_coords.append((x, y))

        pixel_dict[layer.name()] = non_black_or_blue_coords
        #THE LAYER NAMES SHOULD BE THE SAME NAME AS THE VERTEX GROUP
        print(f"Coordinates of non-black/non-blue pixels: {non_black_or_blue_coords}")
    
    json_path = base_output_path / "layer_pixels.json"
    with open(f"{json_path}", "w") as file:
        json.dump(pixel_dict, file, indent=4)
    return layers









# Get the desired layer (e.g., by name)
#layer_name = "MyLayer"
#layer = doc.get_layer(layer_name)

#layers = get_all_layers()

#for layer in layers:
    #print(layer.name())

if __name__ == "__main__":
    start_plugin()

