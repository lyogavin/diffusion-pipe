#!/usr/bin/env python3
"""
Test script to demonstrate the video scaling feature.
Shows how different scale ratios affect the output video dimensions.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess

def create_scaling_test_image():
    """Create a test image with dimension markers to show scaling effects."""
    
    # Create a 320x240 image (classic resolution)
    width, height = 320, 240
    img = Image.new('RGB', (width, height), (100, 150, 200))
    draw = ImageDraw.Draw(img)
    
    # Draw a grid to show scaling effects
    grid_size = 40
    for x in range(0, width, grid_size):
        draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
    for y in range(0, height, grid_size):
        draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)
    
    # Draw a character in the center
    center_x, center_y = width // 2, height // 2
    
    # Head
    head_radius = 30
    draw.ellipse([
        center_x - head_radius, center_y - 60 - head_radius,
        center_x + head_radius, center_y - 60 + head_radius
    ], fill=(255, 220, 180), outline=(0, 0, 0), width=2)
    
    # Body
    draw.rectangle([
        center_x - 20, center_y - 30,
        center_x + 20, center_y + 40
    ], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    
    # Arms
    draw.line([center_x - 20, center_y - 10, center_x - 50, center_y + 10], fill=(0, 0, 0), width=3)
    draw.line([center_x + 20, center_y - 10, center_x + 50, center_y + 10], fill=(0, 0, 0), width=3)
    
    # Legs
    draw.line([center_x - 10, center_y + 40, center_x - 25, center_y + 80], fill=(0, 0, 0), width=3)
    draw.line([center_x + 10, center_y + 40, center_x + 25, center_y + 80], fill=(0, 0, 0), width=3)
    
    # Add dimension text
    try:
        draw.text((10, 10), f"{width}x{height}", fill=(255, 255, 255))
        draw.text((10, height - 30), "Original Size", fill=(255, 255, 255))
    except:
        pass  # Skip text if font loading fails
    
    # Save image
    filename = "scaling_test.png"
    img.save(filename)
    print(f"Created scaling test image: {filename} ({width}x{height})")

def create_scaling_config():
    """Create a config file for scaling tests."""
    config_content = """# Scaling test configuration
# Single animation to test different scale ratios

anim scale_test
    offset 160 192  # Center of 320x240 image
    delay 25
    frame scaling_test.png

anim idle
    offset 160 192
    delay 30
    frame scaling_test.png
"""
    
    with open("scaling_config.txt", "w") as f:
        f.write(config_content)
    print("Created scaling_config.txt")

def run_scaling_tests():
    """Run tests with different scale ratios."""
    
    print("Video Scaling Feature Test")
    print("=" * 40)
    print("Original image: 320x240 pixels")
    print()
    
    # Create test assets
    create_scaling_test_image()
    create_scaling_config()
    
    # Test different scale ratios
    scale_tests = [
        {
            "ratio": 0.5,
            "expected": "160x120",
            "description": "Half size (downscaling)"
        },
        {
            "ratio": 1.0,
            "expected": "320x240", 
            "description": "Original size (no scaling)"
        },
        {
            "ratio": 1.5,
            "expected": "480x360",
            "description": "1.5x size (moderate upscaling)"
        },
        {
            "ratio": 2.0,
            "expected": "640x480",
            "description": "Double size (2x upscaling)"
        },
        {
            "ratio": 3.0,
            "expected": "960x720",
            "description": "Triple size (3x upscaling)"
        }
    ]
    
    for i, test in enumerate(scale_tests):
        print(f"\n{i+1}. Testing scale ratio {test['ratio']} - {test['description']}")
        print(f"Expected output: {test['expected']}")
        print("-" * 50)
        
        # Build command
        cmd = [
            "python", "process_obor_assets.py", "scaling_config.txt",
            "--scale-ratio", str(test['ratio']),
            "--canvas-color", "#2E4057"  # Nice blue-gray background
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        try:
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Success!")
                
                # Rename output files to avoid conflicts
                output_files = ["scale_test.mp4", "scaling_config_animations.json"]
                
                for file in output_files:
                    if os.path.exists(file):
                        new_name = f"scale_{test['ratio']}x_{file}"
                        os.rename(file, new_name)
                        print(f"Generated: {new_name}")
                        
                        # Try to get video info if it's an mp4
                        if file.endswith('.mp4'):
                            try:
                                # Use ffprobe to get video dimensions if available
                                probe_cmd = [
                                    "ffprobe", "-v", "quiet", "-print_format", "json",
                                    "-show_streams", new_name
                                ]
                                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                                if probe_result.returncode == 0:
                                    import json
                                    data = json.loads(probe_result.stdout)
                                    for stream in data.get('streams', []):
                                        if stream.get('codec_type') == 'video':
                                            actual_width = stream.get('width')
                                            actual_height = stream.get('height')
                                            print(f"  Actual dimensions: {actual_width}x{actual_height}")
                                            break
                            except:
                                pass  # Skip dimension check if ffprobe not available
                        
            else:
                print("✗ Failed!")
                print(result.stderr)
                
        except Exception as e:
            print(f"✗ Error running test: {e}")

def main():
    """Main test function."""
    print("This test demonstrates the video scaling feature:")
    print("- Creates a 320x240 test image with grid lines")
    print("- Tests various scale ratios (0.5x to 3.0x)")
    print("- Shows how dimensions change proportionally")
    print("- Uses high-quality LANCZOS resampling")
    print()
    
    # Check if the main script exists
    if not os.path.exists("process_obor_assets.py"):
        print("Error: process_obor_assets.py not found in current directory")
        print("Please run this test from the same directory as the main script")
        return
    
    run_scaling_tests()
    
    print("\nScaling test completed!")
    print("\nGenerated videos show:")
    print("- Different video dimensions based on scale ratio")
    print("- High-quality scaling with preserved image quality")
    print("- Consistent character positioning at all scales")
    print("\nCompare the generated MP4 files to see the scaling effects!")

if __name__ == "__main__":
    main() 