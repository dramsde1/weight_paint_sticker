from pathlib import Path
from PIL import Image
import json

directory = Path("path/to/your/images")
pixel_dict = {}

for file_path in directory.iterdir():
    if file_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif'}:
        print("Processing:", file_path)

        # Open the image
        image = Image.open(str(file_path))

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

        pixel_dict[file_path.stem()] = non_black_or_blue_coords
        file_path.unlink()


json_path = directory / "layer_pixels.json"
with open(f"{json_path}", "a+") as file:
    json.dump(pixel_dict, file, indent=4)

