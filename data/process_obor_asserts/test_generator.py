#!/usr/bin/env python3
"""
Test script for the OpenBor Animation Generator

This script demonstrates how to use the animation generator programmatically
and creates some sample images for testing.
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def create_sample_images():
    """Create sample images for testing the animation generator."""
    
    # Define colors for different animation types
    colors = {
        'idle': [(100, 150, 200), (120, 170, 220), (140, 190, 240)],
        'walk': [(200, 100, 100), (220, 120, 120), (240, 140, 140), (220, 120, 120)],
        'attack': [(100, 200, 100), (120, 220, 120), (140, 240, 140), (160, 255, 160)],
        'jump': [(200, 200, 100), (220, 220, 120), (240, 240, 140)]
    }
    
    # Image dimensions
    width, height = 150, 200
    
    for anim_type, color_list in colors.items():
        for i, color in enumerate(color_list):
            # Create image
            img = Image.new('RGB', (width, height), color)
            draw = ImageDraw.Draw(img)
            
            # Draw a simple character representation
            # Head
            head_center = (width // 2, height // 4)
            head_radius = 20
            draw.ellipse([
                head_center[0] - head_radius, head_center[1] - head_radius,
                head_center[0] + head_radius, head_center[1] + head_radius
            ], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
            
            # Body
            body_top = head_center[1] + head_radius
            body_bottom = height - 60
            body_width = 30
            draw.rectangle([
                width // 2 - body_width // 2, body_top,
                width // 2 + body_width // 2, body_bottom
            ], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
            
            # Arms (vary position slightly for animation effect)
            arm_offset = (i % 2) * 10 - 5
            # Left arm
            draw.line([
                width // 2 - body_width // 2, body_top + 20,
                width // 2 - body_width // 2 - 25, body_top + 40 + arm_offset
            ], fill=(0, 0, 0), width=3)
            # Right arm
            draw.line([
                width // 2 + body_width // 2, body_top + 20,
                width // 2 + body_width // 2 + 25, body_top + 40 - arm_offset
            ], fill=(0, 0, 0), width=3)
            
            # Legs (vary position for walk animation)
            leg_offset = (i % 2) * 15 - 7 if anim_type == 'walk' else 0
            # Left leg
            draw.line([
                width // 2 - 10, body_bottom,
                width // 2 - 20 + leg_offset, height - 10
            ], fill=(0, 0, 0), width=3)
            # Right leg
            draw.line([
                width // 2 + 10, body_bottom,
                width // 2 + 20 - leg_offset, height - 10
            ], fill=(0, 0, 0), width=3)
            
            # Add frame number text
            try:
                draw.text((10, 10), f"{anim_type}_{i}", fill=(0, 0, 0))
            except:
                # If font loading fails, skip text
                pass
            
            # Save image
            filename = f"{anim_type}_{i}.png"
            img.save(filename)
            print(f"Created sample image: {filename}")

def test_animation_generator():
    """Test the animation generator with sample data."""
    
    # Import the animation generator
    try:
        from process_obor_assets import AnimationGenerator
    except ImportError:
        print("Error: Could not import AnimationGenerator. Make sure process_obor_assets.py is in the same directory.")
        return False
    
    # Check if example config exists
    config_file = "example_config.txt"
    if not os.path.exists(config_file):
        print(f"Error: {config_file} not found. Please make sure it exists in the current directory.")
        return False
    
    # Create sample images
    print("Creating sample images...")
    create_sample_images()
    
    # Test the generator
    print("\nTesting animation generator...")
    try:
        generator = AnimationGenerator(
            config_path=config_file,
            target_offset_ratio=(0.5, 0.8),  # Center horizontally, 80% down vertically
            fps=16,
            canvas_color="#222222"  # Dark gray canvas
        )
        
        # Generate animations
        json_file = generator.generate_all_animations()
        
        if json_file:
            print(f"\nTest completed successfully!")
            print(f"Generated videos and summary: {json_file}")
            return True
        else:
            print("Test failed: No animations were generated.")
            return False
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False

def main():
    """Main test function."""
    print("OpenBor Animation Generator Test")
    print("=" * 40)
    
    # Check dependencies
    try:
        import cv2
        import numpy as np
        from PIL import Image
        print("✓ All dependencies are available")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return
    
    # Run test
    success = test_animation_generator()
    
    if success:
        print("\n✓ All tests passed!")
        print("\nGenerated files:")
        for file in os.listdir('.'):
            if file.endswith('.mp4') or file.endswith('.json') or file.endswith('.png'):
                print(f"  - {file}")
    else:
        print("\n✗ Tests failed!")

if __name__ == "__main__":
    main() 