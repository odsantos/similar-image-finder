#!/usr/bin/env python3
import os
from PIL import Image

def generate_bundles(source_png):
    if not os.path.exists(source_png):
        print(f"Error: {source_png} not found.")
        return
    img = Image.open(source_png)
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
    
    ico_path = "assets/images/icon.ico"
    img.save(ico_path, format='ICO', sizes=[(s, s) for s in sizes if s <= 256])
    print(f"Created: {ico_path}")

    icns_path = "assets/images/icon.icns"
    img.save(icns_path, format='ICNS')
    print(f"Created: {icns_path}")

if __name__ == "__main__":
    os.makedirs("assets/images", exist_ok=True)
    generate_bundles("assets/images/icon-1024x1024.png")