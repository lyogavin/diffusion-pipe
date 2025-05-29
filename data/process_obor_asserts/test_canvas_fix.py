#!/usr/bin/env python3
"""
Test script to verify that canvas color is properly applied when resizing frames.
This demonstrates the fix for black strips appearing in generated videos.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import subprocess

def create_test_images():
    """Create test images of different sizes to demonstrate canvas color filling."""
    
    # Create images with different aspect ratios and sizes
    test_images = [
        (100, 200, "tall_narrow", (255, 100, 100)),    # Tall narrow image
        (300, 150, "wide_short", (100, 255, 100)),     # Wide short image  
        (150, 150, "square", (100, 100, 255)),         # Square image
        (80, 300, "very_tall", (255, 255, 100)),       # Very tall image
        (400, 100, "very_wide", (255, 100, 255)),      # Very wide image
    ]
    
    for width, height, name, color in test_images:
        # Create image
        img = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(img)
        
        # Draw a simple character to make it visible
        # Head
        head_center = (width // 2, height // 4)
        head_radius = min(width, height) // 8
        if head_radius > 5:
            draw.ellipse([
                head_center[0] - head_radius, head_center[1] - head_radius,
                head_center[0] + head_radius, head_center[1] + head_radius
            ], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        
        # Body
        body_top = head_center[1] + head_radius
        body_bottom = height - height // 4
        body_width = max(2, width // 10)
        draw.rectangle([
            width // 2 - body_width, body_top,
            width // 2 + body_width, body_bottom
        ], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
        
        # Add label
        draw.text((5, 5), name, fill=(0, 0, 0))
        
        # Save image
        filename = f"test_{name}.png"
        img.save(filename)
        print(f"Created test image: {filename} ({width}x{height})")

def create_test_config():
    """Create a test config file with different sized images."""
    config_content = """# Test configuration for canvas color fix
# Images have different aspect ratios to test canvas filling

anim tall_narrow
    offset 50 160
    delay 20
    frame test_tall_narrow.png

anim wide_short
    offset 150 120
    delay 20
    frame test_wide_short.png

anim square
    offset 75 120
    delay 20
    frame test_square.png

anim very_tall
    offset 40 240
    delay 20
    frame test_very_tall.png

anim very_wide
    offset 200 80
    delay 20
    frame test_very_wide.png

anim idle
    offset 100 120
    delay 30
    frame test_square.png
"""
    
    with open("test_canvas_config.txt", "w") as f:
        f.write(config_content)
    print("Created test_canvas_config.txt")

def run_canvas_tests():
    """Run tests with different canvas colors to verify the fix."""
    
    print("Canvas Color Fix Test")
    print("=" * 40)
    
    # Create test assets
    create_test_images()
    create_test_config()
    
    # Test different canvas colors and positioning
    test_configs = [
        {
            "name": "Red canvas, default positioning",
            "args": ["python", "process_obor_assets.py", "test_canvas_config.txt", 
                    "--canvas-color", "#FF0000"],
            "suffix": "red"
        },
        {
            "name": "Blue canvas, top-left positioning", 
            "args": ["python", "process_obor_assets.py", "test_canvas_config.txt", 
                    "--canvas-color", "#0000FF", "--offset-x-ratio", "0.2", "--offset-y-ratio", "0.2"],
            "suffix": "blue_topleft"
        },
        {
            "name": "Green canvas, bottom-right positioning",
            "args": ["python", "process_obor_assets.py", "test_canvas_config.txt",
                    "--canvas-color", "#00FF00", "--offset-x-ratio", "0.8", "--offset-y-ratio", "0.8"],
            "suffix": "green_bottomright"
        },
        {
            "name": "Yellow canvas, center positioning",
            "args": ["python", "process_obor_assets.py", "test_canvas_config.txt",
                    "--canvas-color", "#FFFF00", "--offset-x-ratio", "0.5", "--offset-y-ratio", "0.5"],
            "suffix": "yellow_center"
        },
        {
            "name": "Purple canvas, 2x scale ratio",
            "args": ["python", "process_obor_assets.py", "test_canvas_config.txt",
                    "--canvas-color", "#800080", "--scale-ratio", "2.0"],
            "suffix": "purple_2x"
        },
        {
            "name": "Orange canvas, 0.5x scale ratio",
            "args": ["python", "process_obor_assets.py", "test_canvas_config.txt",
                    "--canvas-color", "#FFA500", "--scale-ratio", "0.5"],
            "suffix": "orange_half"
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
                
                # Rename output files to avoid conflicts
                output_files = [
                    "tall_narrow.mp4", "wide_short.mp4", "square.mp4", 
                    "very_tall.mp4", "very_wide.mp4", "test_canvas_config_animations.json"
                ]
                
                for file in output_files:
                    if os.path.exists(file):
                        new_name = f"{config['suffix']}_{file}"
                        os.rename(file, new_name)
                        print(f"Generated: {new_name}")
                        
            else:
                print("✗ Failed!")
                print(result.stderr)
                
        except Exception as e:
            print(f"✗ Error running test: {e}")

def main():
    """Main test function."""
    print("This test verifies that:")
    print("1. Canvas color is properly applied to fill blank areas")
    print("2. No black strips appear when images have different aspect ratios")
    print("3. Ratio-based positioning works correctly with canvas filling")
    print("4. Scale ratio feature works for both upscaling and downscaling")
    print()
    
    # Check if the main script exists
    if not os.path.exists("process_obor_assets.py"):
        print("Error: process_obor_assets.py not found in current directory")
        print("Please run this test from the same directory as the main script")
        return
    
    run_canvas_tests()
    
    print("\nTest completed!")
    print("\nGenerated videos should show:")
    print("- Different colored backgrounds (no black strips)")
    print("- Characters positioned according to ratio settings")
    print("- Consistent canvas color filling around images")
    print("- Different video sizes based on scale ratio (2x larger, 0.5x smaller)")
    print("\nCheck the generated MP4 files to verify the fix!")

if __name__ == "__main__":
    main() 