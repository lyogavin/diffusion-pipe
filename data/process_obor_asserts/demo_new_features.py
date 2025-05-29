#!/usr/bin/env python3
"""
Demo script for new OpenBor Animation Generator features:
1. Canvas color customization
2. Ratio-based offset positioning
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import subprocess

def create_demo_images():
    """Create demo images with different sizes to show ratio-based positioning."""
    
    # Create images of different sizes
    sizes = [
        (100, 150, "small"),
        (200, 300, "medium"), 
        (300, 450, "large")
    ]
    
    colors = [(255, 100, 100), (100, 255, 100), (100, 100, 255)]
    
    for i, (width, height, size_name) in enumerate(sizes):
        color = colors[i]
        
        # Create image
        img = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(img)
        
        # Draw a simple character
        # Head
        head_center = (width // 2, height // 4)
        head_radius = min(width, height) // 10
        draw.ellipse([
            head_center[0] - head_radius, head_center[1] - head_radius,
            head_center[0] + head_radius, head_center[1] + head_radius
        ], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        
        # Body
        body_top = head_center[1] + head_radius
        body_bottom = height - height // 4
        body_width = width // 8
        draw.rectangle([
            width // 2 - body_width, body_top,
            width // 2 + body_width, body_bottom
        ], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        
        # Add size label
        draw.text((10, 10), f"{size_name}_{i}", fill=(0, 0, 0))
        
        # Save image
        filename = f"demo_{size_name}_{i}.png"
        img.save(filename)
        print(f"Created demo image: {filename}")

def create_demo_config():
    """Create a demo config file with different sized images."""
    config_content = """# Demo OpenBor Configuration
# Shows ratio-based positioning with different image sizes

anim demo_small
    offset 50 120  # Different absolute offsets
    delay 15
    frame demo_small_0.png

anim demo_medium  
    offset 100 240  # Different absolute offsets
    delay 12
    frame demo_medium_1.png

anim demo_large
    offset 150 360  # Different absolute offsets  
    delay 10
    frame demo_large_2.png

anim idle
    offset 100 200
    delay 20
    frame demo_medium_1.png
"""
    
    with open("demo_config.txt", "w") as f:
        f.write(config_content)
    print("Created demo_config.txt")

def run_demo():
    """Run the demo with different settings."""
    
    print("OpenBor Animation Generator - New Features Demo")
    print("=" * 50)
    
    # Create demo assets
    create_demo_images()
    create_demo_config()
    
    # Test different configurations
    test_configs = [
        {
            "name": "Default (Black canvas, center positioning)",
            "args": ["python", "process_obor_assets.py", "demo_config.txt"]
        },
        {
            "name": "Red canvas, top-left positioning", 
            "args": ["python", "process_obor_assets.py", "demo_config.txt", 
                    "--canvas-color", "#FF0000", "--offset-x-ratio", "0.2", "--offset-y-ratio", "0.3"]
        },
        {
            "name": "Blue canvas, bottom-right positioning",
            "args": ["python", "process_obor_assets.py", "demo_config.txt",
                    "--canvas-color", "#0000FF", "--offset-x-ratio", "0.8", "--offset-y-ratio", "0.9"]
        },
        {
            "name": "Green canvas, center positioning, high FPS",
            "args": ["python", "process_obor_assets.py", "demo_config.txt",
                    "--canvas-color", "#00FF00", "--offset-x-ratio", "0.5", "--offset-y-ratio", "0.5", "--fps", "30"]
        }
    ]
    
    for i, config in enumerate(test_configs):
        print(f"\n{i+1}. {config['name']}")
        print(f"Command: {' '.join(config['args'])}")
        print("-" * 40)
        
        try:
            # Run the command
            result = subprocess.run(config['args'], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Success!")
                print(result.stdout)
            else:
                print("✗ Failed!")
                print(result.stderr)
                
        except Exception as e:
            print(f"✗ Error running demo: {e}")
        
        # Rename output files to avoid conflicts
        output_files = ["demo_small.mp4", "demo_medium.mp4", "demo_large.mp4", "demo_config_animations.json"]
        for file in output_files:
            if os.path.exists(file):
                new_name = f"demo_{i+1}_{file}"
                os.rename(file, new_name)
                print(f"Renamed {file} to {new_name}")

def main():
    """Main demo function."""
    print("This demo shows the new features:")
    print("1. Canvas color customization (hex colors)")
    print("2. Ratio-based offset positioning (0.0 to 1.0)")
    print()
    
    # Check if the main script exists
    if not os.path.exists("process_obor_assets.py"):
        print("Error: process_obor_assets.py not found in current directory")
        print("Please run this demo from the same directory as the main script")
        return
    
    run_demo()
    
    print("\nDemo completed!")
    print("Check the generated videos to see how:")
    print("- Different canvas colors affect the background")
    print("- Ratio-based positioning works consistently across different image sizes")

if __name__ == "__main__":
    main() 