#!/usr/bin/env python3
"""
Example demonstrating both trim-to and cut-out operations.
"""

from video_trimmer import VideoTrimmer
import os

def demonstrate_operations():
    """Demonstrate both trim and cut-out operations."""
    print("Video Trimmer: Trim vs Cut-Out Operations")
    print("=" * 50)
    
    trimmer = VideoTrimmer()
    input_video = "input_video.mp4"
    
    if not os.path.exists(input_video):
        print(f"Please place your input video at: {input_video}")
        print("Then run this script again to see the demonstrations.")
        return
    
    # Get video info first
    try:
        info = trimmer.get_video_info(input_video)
        print(f"Input video: {info['duration']:.2f} seconds long")
        print()
    except Exception as e:
        print(f"Error reading video: {e}")
        return
    
    print("OPERATION 1: TRIM TO (Keep only segment)")
    print("-" * 40)
    print("This keeps ONLY the segment from 10s to 20s")
    print("Original: [0s--------10s========20s--------end]")
    print("Result:   [10s========20s] (10 seconds long)")
    
    try:
        trimmer.trim_video(
            input_video, 
            "trimmed_keep_10_to_20.mp4", 
            start_time=10.0, 
            end_time=20.0,
            cut_out=False  # Keep the segment
        )
        print("✓ Trim-to operation completed!\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    print("OPERATION 2: CUT OUT (Remove segment)")
    print("-" * 40)
    print("This REMOVES the segment from 10s to 20s")
    print("Original: [0s--------10s========20s--------end]")  
    print("Result:   [0s--------][20s--------end] (joined)")
    
    try:
        trimmer.trim_video(
            input_video, 
            "cut_out_10_to_20.mp4", 
            start_time=10.0, 
            end_time=20.0,
            cut_out=True  # Remove the segment
        )
        print("✓ Cut-out operation completed!\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    print("PRACTICAL EXAMPLES:")
    print("-" * 20)
    print("• Remove intro/outro: --start 0 --end 5 --cut-out")
    print("• Remove mid-video ads: --start 60 --end 90 --cut-out") 
    print("• Keep only highlights: --start 120 --end 180")
    print("• Remove silence/pause: --start 45.5 --end 52.3 --cut-out")

def command_line_examples():
    """Show command line examples."""
    print("\nCOMMAND LINE EXAMPLES:")
    print("=" * 50)
    
    examples = [
        {
            'operation': 'Remove first 5 seconds',
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 0 --end 5 --cut-out'
        },
        {
            'operation': 'Remove segment from 1:30 to 2:15',
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 01:30 --end 02:15 --cut-out'
        },
        {
            'operation': 'Keep only first 30 seconds',
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 0 --end 30'
        },
        {
            'operation': 'Remove decimal precision segment',
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 45.25 --end 52.75 --cut-out'
        },
        {
            'operation': 'Fast cut-out (less accurate)',
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 60 --end 90 --cut-out --fast'
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['operation']}")
        print(f"   {example['command']}")
        print()

if __name__ == "__main__":
    demonstrate_operations()
    command_line_examples()
    
    print("KEY DIFFERENCES:")
    print("• Without --cut-out: KEEPS only the specified segment")
    print("• With --cut-out: REMOVES the specified segment")
    print("• Decimal seconds supported: 2.4, 30.5, etc.")
    print("• Time formats: 30.5, 01:30.5, 01:02:30.5") 