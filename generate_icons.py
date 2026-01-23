#!/usr/bin/env python3

import os
from PIL import Image

def generate_bundles(source_png):
    if not os.path.exists(source_png):
        print(f"Error: {source_png} not found.")
        return

    img = Image.open(source_png)
    
    # Define standard icon sizes
    sizes = [16, 32, 48, 64, 128, 256, 512]
    
    # 1. Generate Windows .ico
    # Pillow handles the multi-resolution packing automatically
    ico_path = "assets/images/app_icon.ico"
    img.save(ico_path, format='ICO', sizes=[(s, s) for s in sizes if s <= 256])
    print(f"Created: {ico_path}")

    # 2. Generate macOS .icns
    # Pillow supports ICNS format directly
    icns_path = "assets/images/app_icon.icns"
    img.save(icns_path, format='ICNS', sizes=[(s, s) for s in sizes + [1024]])
    print(f"Created: {icns_path}")

if __name__ == "__main__":
    # Ensure folder exists
    os.makedirs("assets/images", exist_ok=True)
    # Point this to your master PNG
    generate_bundles("assets/images/icon-1024x1024.png")