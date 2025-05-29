#!/usr/bin/env python3
"""
Test script to demonstrate the repeat fill feature.
Shows how animations behave with different loop settings and target frame counts.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import subprocess

def create_repeat_test_images():
    """Create test images for repeat fill demonstration."""
    
    # Create a simple walking animation (3 frames)
    walk_frames = []
    for i in range(3):
        img = Image.new('RGB', (100, 150), (150, 200, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw a simple stick figure with different leg positions
        # Head
        draw.ellipse([40, 20, 60, 40], fill=(255, 220, 180), outline=(0, 0, 0), width=2)
        
        # Body
        draw.line([50, 40, 50, 90], fill=(0, 0, 0), width=3)
        
        # Arms
        draw.line([50, 55, 35, 70], fill=(0, 0, 0), width=2)
        draw.line([50, 55, 65, 70], fill=(0, 0, 0), width=2)
        
        # Legs - different positions for walking animation
        if i == 0:  # Left leg forward
            draw.line([50, 90, 40, 130], fill=(0, 0, 0), width=3)
            draw.line([50, 90, 60, 130], fill=(0, 0, 0), width=3)
        elif i == 1:  # Both legs center
            draw.line([50, 90, 45, 130], fill=(0, 0, 0), width=3)
            draw.line([50, 90, 55, 130], fill=(0, 0, 0), width=3)
        else:  # Right leg forward
            draw.line([50, 90, 60, 130], fill=(0, 0, 0), width=3)
            draw.line([50, 90, 40, 130], fill=(0, 0, 0), width=3)
        
        # Add frame number
        draw.text((5, 5), f"Walk {i+1}", fill=(255, 255, 255))
        
        filename = f"walk_{i+1}.png"
        img.save(filename)
        walk_frames.append(filename)
        print(f"Created: {filename}")
    
    # Create an attack animation (2 frames) - non-repeatable
    attack_frames = []
    for i in range(2):
        img = Image.new('RGB', (120, 150), (255, 150, 150))
        draw = ImageDraw.Draw(img)
        
        # Draw stick figure with attack motion
        # Head
        draw.ellipse([50, 20, 70, 40], fill=(255, 220, 180), outline=(0, 0, 0), width=2)
        
        # Body
        draw.line([60, 40, 60, 90], fill=(0, 0, 0), width=3)
        
        # Arms - different positions for attack
        if i == 0:  # Wind up
            draw.line([60, 55, 40, 50], fill=(0, 0, 0), width=2)
            draw.line([60, 55, 80, 60], fill=(0, 0, 0), width=2)
        else:  # Strike
            draw.line([60, 55, 45, 70], fill=(0, 0, 0), width=2)
            draw.line([60, 55, 100, 45], fill=(0, 0, 0), width=2)
            # Add impact effect
            draw.text((85, 35), "POW!", fill=(255, 255, 0))
        
        # Legs
        draw.line([60, 90, 50, 130], fill=(0, 0, 0), width=3)
        draw.line([60, 90, 70, 130], fill=(0, 0, 0), width=3)
        
        # Add frame number
        draw.text((5, 5), f"Attack {i+1}", fill=(255, 255, 255))
        
        filename = f"attack_{i+1}.png"
        img.save(filename)
        attack_frames.append(filename)
        print(f"Created: {filename}")
    
    # Create idle frame
    img = Image.new('RGB', (100, 150), (200, 200, 200))
    draw = ImageDraw.Draw(img)
    
    # Draw simple standing figure
    # Head
    draw.ellipse([40, 20, 60, 40], fill=(255, 220, 180), outline=(0, 0, 0), width=2)
    
    # Body
    draw.line([50, 40, 50, 90], fill=(0, 0, 0), width=3)
    
    # Arms
    draw.line([50, 55, 35, 75], fill=(0, 0, 0), width=2)
    draw.line([50, 55, 65, 75], fill=(0, 0, 0), width=2)
    
    # Legs
    draw.line([50, 90, 45, 130], fill=(0, 0, 0), width=3)
    draw.line([50, 90, 55, 130], fill=(0, 0, 0), width=3)
    
    # Add label
    draw.text((5, 5), "Idle", fill=(0, 0, 0))
    
    filename = "idle.png"
    img.save(filename)
    print(f"Created: {filename}")
    
    return walk_frames, attack_frames, filename

def create_repeat_config():
    """Create a config file with different loop settings."""
    config_content = """# Repeat fill test configuration
# Demonstrates different loop behaviors

anim walk
    loop 1          # Repeatable animation
    offset 50 120
    delay 8         # Fast walking
    frame walk_1.png
    frame walk_2.png
    frame walk_3.png

anim attack
    loop 0          # Non-repeatable animation
    offset 60 120
    delay 5         # Quick attack
    frame attack_1.png
    delay 15        # Hold strike
    frame attack_2.png

anim idle
    loop 1          # Repeatable (though usually just one frame)
    offset 50 120
    delay 20
    frame idle.png
"""
    
    with open("repeat_config.txt", "w") as f:
        f.write(config_content)
    print("Created repeat_config.txt")

def run_repeat_tests():
    """Run tests with different repeat fill settings."""
    
    print("Repeat Fill Feature Test")
    print("=" * 40)
    
    # Create test assets
    walk_frames, attack_frames, idle_frame = create_repeat_test_images()
    create_repeat_config()
    
    # Test different repeat fill scenarios
    test_configs = [
        {
            "name": "No repeat fill (original behavior)",
            "args": ["python", "process_obor_assets.py", "repeat_config.txt"],
            "suffix": "original"
        },
        {
            "name": "Repeat fill 50 frames - walk animation (loop=1)",
            "args": ["python", "process_obor_assets.py", "repeat_config.txt", 
                    "--repeat-fill", "50"],
            "suffix": "50frames"
        },
        {
            "name": "Repeat fill 100 frames - all animations",
            "args": ["python", "process_obor_assets.py", "repeat_config.txt",
                    "--repeat-fill", "100", "--canvas-color", "#2E4057"],
            "suffix": "100frames"
        },
        {
            "name": "Repeat fill 30 frames with 2x scale",
            "args": ["python", "process_obor_assets.py", "repeat_config.txt",
                    "--repeat-fill", "30", "--scale-ratio", "2.0", "--canvas-color", "#4A5D23"],
            "suffix": "30frames_2x"
        }
    ]
    
    for i, config in enumerate(test_configs):
        print(f"\n{i+1}. {config['name']}")
        print(f"Command: {' '.join(config['args'])}")
        print("-" * 50)
        
        try:
            # Run the command
            result = subprocess.run(config['args'], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Success!")
                print(result.stdout)
                
                # Rename output files to avoid conflicts
                output_files = [
                    "walk.mp4", "attack.mp4", "idle.mp4", 
                    "repeat_config_animations.json"
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
    print("This test demonstrates the repeat fill feature:")
    print("- Creates walking animation (3 frames, loop=1)")
    print("- Creates attack animation (2 frames, loop=0)")
    print("- Creates idle animation (1 frame, loop=1)")
    print("- Tests different target frame counts")
    print()
    print("Expected behavior:")
    print("- Walk animation (loop=1): Repeats walking cycle to fill target frames")
    print("- Attack animation (loop=0): Fills remaining frames with idle frames")
    print("- Idle animation (loop=1): Repeats idle frame to fill target frames")
    print()
    
    # Check if the main script exists
    if not os.path.exists("process_obor_assets.py"):
        print("Error: process_obor_assets.py not found in current directory")
        print("Please run this test from the same directory as the main script")
        return
    
    run_repeat_tests()
    
    print("\nRepeat fill test completed!")
    print("\nGenerated videos show:")
    print("- Original: Natural animation lengths")
    print("- 50 frames: Walk repeats cycling, attack fills with idle")
    print("- 100 frames: All animations extended to same length")
    print("- 30 frames: Shorter target with 2x scaling")
    print("\nCompare the generated MP4 files to see the repeat fill effects!")

if __name__ == "__main__":
    main() 