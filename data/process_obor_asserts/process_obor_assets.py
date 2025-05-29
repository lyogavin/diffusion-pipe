#!/usr/bin/env python3
"""
OpenBor Animation Generator

This program generates MP4 animations from OpenBor character config files.
It processes the animation definitions, handles frame timing, and creates
video files with proper offset handling.
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np
from PIL import Image, ImageOps


class OpenBorAnimation:
    """Represents a single OpenBor animation with its frames and properties."""
    
    def __init__(self, name: str):
        self.name = name
        self.frames = []  # List of (image_path, delay, offset)
        self.default_delay = 10  # Default delay in centiseconds
        self.default_offset = (0, 0)  # Default offset (x, y)
        self.loop = 1  # Default loop setting (1 = repeatable, 0 = non-repeatable)
    
    def add_frame(self, image_path: str, delay: Optional[int] = None, offset: Optional[Tuple[int, int]] = None):
        """Add a frame to the animation."""
        frame_delay = delay if delay is not None else self.default_delay
        frame_offset = offset if offset is not None else self.default_offset
        self.frames.append((image_path, frame_delay, frame_offset))
    
    def set_default_delay(self, delay: int):
        """Set the default delay for frames."""
        self.default_delay = delay
    
    def set_default_offset(self, offset: Tuple[int, int]):
        """Set the default offset for frames."""
        self.default_offset = offset
    
    def set_loop(self, loop: int):
        """Set the loop setting for the animation."""
        self.loop = loop


class OpenBorParser:
    """Parser for OpenBor configuration files."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self.animations = {}
    
    def parse(self) -> Dict[str, OpenBorAnimation]:
        """Parse the OpenBor config file and return animations."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_animation = None
        current_delay = 10
        current_offset = (0, 0)
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            command = parts[0].lower()
            
            if command == 'anim':
                # Start new animation
                if len(parts) > 1:
                    anim_name = parts[1]
                    current_animation = OpenBorAnimation(anim_name)
                    self.animations[anim_name] = current_animation
                    current_delay = 10
                    current_offset = (0, 0)
            
            elif current_animation is not None:
                if command == 'delay':
                    if len(parts) > 1:
                        current_delay = int(parts[1])
                        current_animation.set_default_delay(current_delay)
                
                elif command == 'offset':
                    if len(parts) > 2:
                        x, y = int(parts[1]), int(parts[2])
                        current_offset = (x, y)
                        current_animation.set_default_offset(current_offset)
                
                elif command == 'loop':
                    if len(parts) > 1:
                        loop_value = int(parts[1])
                        current_animation.set_loop(loop_value)
                
                elif command == 'frame':
                    if len(parts) > 1:
                        # Extract just the filename from the path
                        frame_path = Path(parts[1]).name
                        current_animation.add_frame(frame_path, current_delay, current_offset)
        
        return self.animations


class AnimationGenerator:
    """Generates MP4 videos from OpenBor animations."""
    
    def __init__(self, config_path: str, target_offset_ratio: Tuple[float, float] = (0.5, 0.8), fps: int = 16, canvas_color: str = "#000000", scale_ratio: float = 1.0, repeat_fill: Optional[int] = None):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self.target_offset_ratio = target_offset_ratio  # Now using ratios (0.0 to 1.0)
        self.fps = fps
        self.canvas_color = self.hex_to_bgr(canvas_color)  # Convert hex to BGR for OpenCV
        self.scale_ratio = scale_ratio  # Scale factor for output video dimensions
        self.repeat_fill = repeat_fill  # Target frame count for repeat filling
        self.parser = OpenBorParser(config_path)
        self.animations = self.parser.parse()
        self.generated_videos = []
    
    def hex_to_bgr(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to BGR tuple for OpenCV."""
        # Remove '#' if present
        hex_color = hex_color.lstrip('#')
        
        # Ensure it's a valid 6-character hex color
        if len(hex_color) != 6:
            print(f"Warning: Invalid hex color '{hex_color}', using black (#000000)")
            hex_color = "000000"
        
        try:
            # Convert hex to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Return as BGR for OpenCV
            return (b, g, r)
        except ValueError:
            print(f"Warning: Invalid hex color '{hex_color}', using black (#000000)")
            return (0, 0, 0)
    
    def offset_to_ratio(self, offset: Tuple[int, int], image_size: Tuple[int, int]) -> Tuple[float, float]:
        """Convert absolute offset coordinates to ratios based on image size."""
        width, height = image_size
        if width == 0 or height == 0:
            return (0.5, 0.5)  # Default to center if image has no size
        
        ratio_x = offset[0] / width
        ratio_y = offset[1] / height
        
        return (ratio_x, ratio_y)
    
    def ratio_to_offset(self, ratio: Tuple[float, float], image_size: Tuple[int, int]) -> Tuple[int, int]:
        """Convert ratio coordinates to absolute offset based on image size."""
        width, height = image_size
        
        offset_x = int(ratio[0] * width)
        offset_y = int(ratio[1] * height)
        
        return (offset_x, offset_y)
    
    def load_and_process_image(self, image_path: str, current_offset: Tuple[int, int]) -> np.ndarray:
        """Load an image and adjust its position based on offset differences."""
        full_path = self.config_dir / image_path
        
        if not full_path.exists():
            print(f"Warning: Image not found: {full_path}")
            # Create a placeholder image
            img = np.zeros((200, 200, 3), dtype=np.uint8)
            img.fill(128)  # Gray placeholder
            return img
        
        # Load image with PIL for better format support
        pil_img = Image.open(full_path).convert('RGBA')
        orig_width, orig_height = pil_img.size
        
        # Convert current offset to ratio based on original image size
        current_offset_ratio = self.offset_to_ratio(current_offset, (orig_width, orig_height))
        
        # Calculate target offset in absolute coordinates for this image size
        target_offset = self.ratio_to_offset(self.target_offset_ratio, (orig_width, orig_height))
        
        # Calculate offset difference
        offset_diff_x = target_offset[0] - current_offset[0]
        offset_diff_y = target_offset[1] - current_offset[1]
        
        # If we need to adjust the image position
        if offset_diff_x != 0 or offset_diff_y != 0:
            # Calculate new canvas size (add padding for movement)
            new_width = orig_width + abs(offset_diff_x)
            new_height = orig_height + abs(offset_diff_y)
            
            # Create new image with canvas color background
            canvas_color_rgba = (*self.canvas_color[::-1], 255)  # Convert BGR to RGBA
            new_img = Image.new('RGBA', (new_width, new_height), canvas_color_rgba)
            
            # Calculate paste position
            paste_x = max(0, offset_diff_x)
            paste_y = max(0, offset_diff_y)
            
            # Paste the original image
            new_img.paste(pil_img, (paste_x, paste_y), pil_img)  # Use alpha channel for proper blending
            
            # If we moved the image, we need to pad the empty areas
            if offset_diff_x > 0:  # Moved right, pad left
                # Get the leftmost column color for padding
                left_col = pil_img.crop((0, 0, 1, orig_height))
                for x in range(offset_diff_x):
                    new_img.paste(left_col, (x, paste_y), left_col)
            elif offset_diff_x < 0:  # Moved left, pad right
                # Get the rightmost column color for padding
                right_col = pil_img.crop((orig_width-1, 0, orig_width, orig_height))
                for x in range(abs(offset_diff_x)):
                    new_img.paste(right_col, (paste_x + orig_width + x, paste_y), right_col)
            
            if offset_diff_y > 0:  # Moved down, pad top
                # Get the topmost row color for padding
                top_row = pil_img.crop((0, 0, orig_width, 1))
                for y in range(offset_diff_y):
                    new_img.paste(top_row, (paste_x, y), top_row)
            elif offset_diff_y < 0:  # Moved up, pad bottom
                # Get the bottommost row color for padding
                bottom_row = pil_img.crop((0, orig_height-1, orig_width, orig_height))
                for y in range(abs(offset_diff_y)):
                    new_img.paste(bottom_row, (paste_x, paste_y + orig_height + y), bottom_row)
            
            pil_img = new_img
        
        # Apply scaling if scale_ratio is not 1.0
        if self.scale_ratio != 1.0:
            current_width, current_height = pil_img.size
            new_width = int(current_width * self.scale_ratio)
            new_height = int(current_height * self.scale_ratio)
            
            # Use high-quality resampling for scaling
            if self.scale_ratio > 1.0:
                # Upscaling - use LANCZOS for best quality
                pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
            else:
                # Downscaling - use LANCZOS for best quality
                pil_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to RGB (remove alpha channel) and then to numpy array
        pil_img = pil_img.convert('RGB')
        img_array = np.array(pil_img)
        
        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_bgr
    
    def get_idle_frame(self) -> Optional[np.ndarray]:
        """Get the first frame of the idle animation for padding."""
        if 'idle' in self.animations and self.animations['idle'].frames:
            first_frame = self.animations['idle'].frames[0]
            return self.load_and_process_image(first_frame[0], first_frame[2])
        return None
    
    def apply_repeat_fill(self, animation: OpenBorAnimation, video_frames: List[Tuple[np.ndarray, int]]) -> List[Tuple[np.ndarray, int]]:
        """Apply repeat fill logic to reach target frame count."""
        if self.repeat_fill is None:
            return video_frames
        
        # Calculate current total frame count
        current_frame_count = sum(frame_count for _, frame_count in video_frames)
        
        if current_frame_count >= self.repeat_fill:
            # Already at or above target, no need to fill
            return video_frames
        
        frames_needed = self.repeat_fill - current_frame_count
        
        if animation.loop == 1:
            # Animation is repeatable - repeat the animation frames (excluding idle frames)
            print(f"Repeating animation '{animation.name}' to reach {self.repeat_fill} frames (loop=1)")
            
            # Find animation frames (exclude idle frames at beginning and end)
            animation_frames = []
            idle_frame = self.get_idle_frame()
            
            # Skip idle frame at beginning if present
            start_idx = 0
            if len(video_frames) > 0 and idle_frame is not None:
                first_frame = video_frames[0]
                if first_frame[1] == 1 and np.array_equal(first_frame[0], idle_frame):
                    start_idx = 1
            
            # Skip idle frame at end if present
            end_idx = len(video_frames)
            if len(video_frames) > 1 and idle_frame is not None:
                last_frame = video_frames[-1]
                if last_frame[1] == 1 and np.array_equal(last_frame[0], idle_frame):
                    end_idx = len(video_frames) - 1
            
            for i in range(start_idx, end_idx):
                animation_frames.append(video_frames[i])
            
            if not animation_frames:
                # No animation frames found, just add idle frames
                idle_frame = self.get_idle_frame()
                if idle_frame is not None:
                    video_frames.extend([(idle_frame, 1)] * frames_needed)
                return video_frames
            
            # Calculate frames per animation cycle
            frames_per_cycle = sum(frame_count for _, frame_count in animation_frames)
            
            # Add complete cycles
            while frames_needed >= frames_per_cycle:
                video_frames.extend(animation_frames)
                frames_needed -= frames_per_cycle
            
            # Add partial cycle if needed
            if frames_needed > 0:
                frames_added = 0
                for img, frame_count in animation_frames:
                    if frames_added + frame_count <= frames_needed:
                        video_frames.append((img, frame_count))
                        frames_added += frame_count
                    else:
                        # Add partial frame count
                        remaining = frames_needed - frames_added
                        if remaining > 0:
                            video_frames.append((img, remaining))
                        break
        
        else:
            # Animation is not repeatable (loop=0) - fill with idle frames
            print(f"Filling animation '{animation.name}' with idle frames to reach {self.repeat_fill} frames (loop=0)")
            
            idle_frame = self.get_idle_frame()
            if idle_frame is not None:
                video_frames.extend([(idle_frame, 1)] * frames_needed)
            else:
                # No idle frame available, use the last frame of the animation
                if video_frames:
                    last_frame = video_frames[-1][0]
                    video_frames.extend([(last_frame, 1)] * frames_needed)
        
        return video_frames
    
    def generate_animation_video(self, animation: OpenBorAnimation) -> Tuple[str, int]:
        """Generate an MP4 video for a single animation."""
        if not animation.frames:
            print(f"Warning: Animation '{animation.name}' has no frames")
            return None, 0
        
        # Prepare output filename
        output_filename = f"{animation.name}.mp4"
        output_path = self.config_dir / output_filename
        
        # Get idle frame for padding
        idle_frame = self.get_idle_frame()
        
        # Collect all frames with their durations
        video_frames = []
        
        # Add idle frame at the beginning
        if idle_frame is not None:
            video_frames.append((idle_frame, 1))  # 1 frame duration
        
        # Process animation frames
        for frame_path, delay, offset in animation.frames:
            img = self.load_and_process_image(frame_path, offset)
            # Convert delay from centiseconds to frame count
            frame_count = max(1, int(delay * self.fps / 100))
            video_frames.append((img, frame_count))
        
        # Add idle frame at the end
        if idle_frame is not None:
            video_frames.append((idle_frame, 1))  # 1 frame duration
        
        # Apply repeat fill logic if specified
        video_frames = self.apply_repeat_fill(animation, video_frames)
        
        if not video_frames:
            print(f"Warning: No frames to process for animation '{animation.name}'")
            return None, 0
        
        # Determine video dimensions (use the largest frame dimensions)
        max_height = max(frame[0].shape[0] for frame in video_frames)
        max_width = max(frame[0].shape[1] for frame in video_frames)
        
        # Ensure dimensions are even (required for many codecs)
        if max_width % 2 != 0:
            max_width += 1
        if max_height % 2 != 0:
            max_height += 1
        
        # Try ffmpeg first (best compatibility on macOS)
        try:
            return self.generate_video_with_ffmpeg(animation, video_frames, max_width, max_height)
        except Exception as e:
            print(f"ffmpeg method failed for {animation.name}: {e}")
        
        # Fall back to OpenCV with multiple codec options
        codecs_to_try = [
            ('avc1', '.mp4'),  # H.264 - best compatibility
            ('mp4v', '.mp4'),  # MPEG-4 Part 2
            ('XVID', '.avi'),  # Xvid codec
        ]
        
        video_writer = None
        final_output_path = None
        
        for fourcc_str, extension in codecs_to_try:
            try:
                # Update filename with correct extension
                test_filename = f"{animation.name}{extension}"
                test_output_path = self.config_dir / test_filename
                
                # Try to create video writer with this codec
                fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
                test_writer = cv2.VideoWriter(str(test_output_path), fourcc, self.fps, (max_width, max_height))
                
                # Test if the writer was created successfully
                if test_writer.isOpened():
                    video_writer = test_writer
                    final_output_path = test_output_path
                    output_filename = test_filename
                    print(f"Using OpenCV codec: {fourcc_str} for {animation.name}")
                    break
                else:
                    test_writer.release()
                    # Clean up failed file
                    if test_output_path.exists():
                        test_output_path.unlink()
                        
            except Exception as e:
                print(f"Failed to create video writer with codec {fourcc_str}: {e}")
                if 'test_writer' in locals():
                    test_writer.release()
                continue
        
        # If no codec worked, fall back to creating individual frame images
        if video_writer is None:
            print(f"Warning: Could not create video writer for {animation.name}. Saving as image sequence instead.")
            return self.generate_image_sequence(animation, video_frames, max_width, max_height)
        
        total_frames = 0
        
        try:
            # Write frames to video
            for img, frame_count in video_frames:
                # Resize frame to match video dimensions if needed
                if img.shape[0] != max_height or img.shape[1] != max_width:
                    # Create a canvas with the specified color
                    canvas = np.full((max_height, max_width, 3), self.canvas_color, dtype=np.uint8)
                    
                    # Instead of centering, maintain the ratio-based positioning
                    # Calculate position based on target offset ratios
                    target_x = int(self.target_offset_ratio[0] * max_width) - int(self.target_offset_ratio[0] * img.shape[1])
                    target_y = int(self.target_offset_ratio[1] * max_height) - int(self.target_offset_ratio[1] * img.shape[0])
                    
                    # Ensure the image fits within canvas bounds
                    target_x = max(0, min(target_x, max_width - img.shape[1]))
                    target_y = max(0, min(target_y, max_height - img.shape[0]))
                    
                    # Place the image at the calculated position
                    end_y = min(target_y + img.shape[0], max_height)
                    end_x = min(target_x + img.shape[1], max_width)
                    canvas[target_y:end_y, target_x:end_x] = img[:end_y-target_y, :end_x-target_x]
                    img = canvas
                
                # Write the frame multiple times based on delay
                for _ in range(frame_count):
                    video_writer.write(img)
                    total_frames += 1
            
            video_writer.release()
            
            # Verify the video file was created and has content
            if final_output_path.exists() and final_output_path.stat().st_size > 0:
                print(f"Generated video: {output_filename} ({total_frames} frames)")
                return output_filename, total_frames
            else:
                print(f"Warning: Video file {output_filename} was not created properly. Trying image sequence fallback.")
                return self.generate_image_sequence(animation, video_frames, max_width, max_height)
                
        except Exception as e:
            print(f"Error writing video {animation.name}: {e}")
            video_writer.release()
            return self.generate_image_sequence(animation, video_frames, max_width, max_height)
    
    def generate_image_sequence(self, animation: OpenBorAnimation, video_frames: list, max_width: int, max_height: int) -> Tuple[str, int]:
        """Fallback method to generate image sequence when video creation fails."""
        print(f"Generating image sequence for {animation.name}")
        
        # Create directory for image sequence
        sequence_dir = self.config_dir / f"{animation.name}_frames"
        sequence_dir.mkdir(exist_ok=True)
        
        total_frames = 0
        frame_index = 0
        
        for img, frame_count in video_frames:
            # Resize frame to match video dimensions if needed
            if img.shape[0] != max_height or img.shape[1] != max_width:
                # Create a canvas with the specified color
                canvas = np.full((max_height, max_width, 3), self.canvas_color, dtype=np.uint8)
                
                # Instead of centering, maintain the ratio-based positioning
                # Calculate position based on target offset ratios
                target_x = int(self.target_offset_ratio[0] * max_width) - int(self.target_offset_ratio[0] * img.shape[1])
                target_y = int(self.target_offset_ratio[1] * max_height) - int(self.target_offset_ratio[1] * img.shape[0])
                
                # Ensure the image fits within canvas bounds
                target_x = max(0, min(target_x, max_width - img.shape[1]))
                target_y = max(0, min(target_y, max_height - img.shape[0]))
                
                # Place the image at the calculated position
                end_y = min(target_y + img.shape[0], max_height)
                end_x = min(target_x + img.shape[1], max_width)
                canvas[target_y:end_y, target_x:end_x] = img[:end_y-target_y, :end_x-target_x]
                img = canvas
            
            # Save the frame multiple times based on delay
            for _ in range(frame_count):
                frame_filename = sequence_dir / f"frame_{frame_index:04d}.png"
                cv2.imwrite(str(frame_filename), img)
                frame_index += 1
                total_frames += 1
        
        # Create a simple script to convert to video using ffmpeg if available
        script_path = sequence_dir / "convert_to_video.sh"
        with open(script_path, 'w') as f:
            f.write(f"""#!/bin/bash
# Convert image sequence to video using ffmpeg
# Run this script if you have ffmpeg installed

ffmpeg -r {self.fps} -i frame_%04d.png -c:v libx264 -pix_fmt yuv420p -y ../{animation.name}.mp4

echo "Video created: {animation.name}.mp4"
""")
        script_path.chmod(0o755)
        
        print(f"Generated {total_frames} frame images in {sequence_dir}")
        print(f"Run the script {script_path} to convert to video if you have ffmpeg installed")
        
        return f"{animation.name}_frames/", total_frames
    
    def generate_video_with_ffmpeg(self, animation: OpenBorAnimation, video_frames: list, max_width: int, max_height: int) -> Tuple[str, int]:
        """Generate video using ffmpeg directly for better compatibility."""
        print(f"Attempting to generate video using ffmpeg for {animation.name}")
        
        # Check if ffmpeg is available
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ffmpeg not found. Falling back to image sequence.")
            return self.generate_image_sequence(animation, video_frames, max_width, max_height)
        
        # Create temporary directory for frames
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            total_frames = 0
            frame_index = 0
            
            # Save all frames as temporary images
            for img, frame_count in video_frames:
                # Resize frame to match video dimensions if needed
                if img.shape[0] != max_height or img.shape[1] != max_width:
                    # Create a canvas with the specified color
                    canvas = np.full((max_height, max_width, 3), self.canvas_color, dtype=np.uint8)
                    
                    # Instead of centering, maintain the ratio-based positioning
                    # Calculate position based on target offset ratios
                    target_x = int(self.target_offset_ratio[0] * max_width) - int(self.target_offset_ratio[0] * img.shape[1])
                    target_y = int(self.target_offset_ratio[1] * max_height) - int(self.target_offset_ratio[1] * img.shape[0])
                    
                    # Ensure the image fits within canvas bounds
                    target_x = max(0, min(target_x, max_width - img.shape[1]))
                    target_y = max(0, min(target_y, max_height - img.shape[0]))
                    
                    # Place the image at the calculated position
                    end_y = min(target_y + img.shape[0], max_height)
                    end_x = min(target_x + img.shape[1], max_width)
                    canvas[target_y:end_y, target_x:end_x] = img[:end_y-target_y, :end_x-target_x]
                    img = canvas
                
                # Save the frame multiple times based on delay
                for _ in range(frame_count):
                    frame_filename = temp_path / f"frame_{frame_index:06d}.png"
                    cv2.imwrite(str(frame_filename), img)
                    frame_index += 1
                    total_frames += 1
            
            # Generate video using ffmpeg
            output_filename = f"{animation.name}.mp4"
            output_path = self.config_dir / output_filename
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-r', str(self.fps),  # Frame rate
                '-i', str(temp_path / 'frame_%06d.png'),  # Input pattern
                '-c:v', 'libx264',  # Video codec
                '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                '-crf', '23',  # Quality setting
                str(output_path)
            ]
            
            try:
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
                
                # Verify the video file was created
                if output_path.exists() and output_path.stat().st_size > 0:
                    print(f"Generated video with ffmpeg: {output_filename} ({total_frames} frames)")
                    return output_filename, total_frames
                else:
                    print(f"ffmpeg failed to create video file. Falling back to image sequence.")
                    return self.generate_image_sequence(animation, video_frames, max_width, max_height)
                    
            except subprocess.CalledProcessError as e:
                print(f"ffmpeg failed: {e.stderr}")
                print("Falling back to image sequence.")
                return self.generate_image_sequence(animation, video_frames, max_width, max_height)
    
    def generate_all_animations(self) -> str:
        """Generate videos for all animations and create a JSON summary."""
        if not self.animations:
            print("No animations found in config file")
            return None
        
        results = []
        
        for anim_name, animation in self.animations.items():
            video_filename, frame_count = self.generate_animation_video(animation)
            if video_filename:
                results.append({
                    "animation": anim_name,
                    "video": video_filename,
                    "frames": frame_count
                })
        
        # Generate JSON summary
        json_filename = f"{self.config_path.stem}_animations.json"
        json_path = self.config_dir / json_filename
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"Generated JSON summary: {json_filename}")
        return json_filename


def main():
    """Main function to run the OpenBor animation generator."""
    parser = argparse.ArgumentParser(description='Generate MP4 animations from OpenBor config files')
    parser.add_argument('config_file', help='Path to the OpenBor config .txt file')
    parser.add_argument('--offset-x-ratio', type=float, default=0.5, help='Target offset X ratio (0.0 to 1.0, default: 0.5)')
    parser.add_argument('--offset-y-ratio', type=float, default=0.8, help='Target offset Y ratio (0.0 to 1.0, default: 0.8)')
    parser.add_argument('--fps', type=int, default=16, help='Frames per second for output videos (default: 16)')
    parser.add_argument('--canvas-color', type=str, default='#000000', help='Canvas background color in hex format (default: #000000)')
    parser.add_argument('--scale-ratio', type=float, default=1.0, help='Scale ratio for output video dimensions (default: 1.0)')
    parser.add_argument('--repeat-fill', type=int, help='Target frame count for repeat filling (respects loop setting)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.config_file):
        print(f"Error: Config file not found: {args.config_file}")
        sys.exit(1)
    
    # Validate ratio values
    if not (0.0 <= args.offset_x_ratio <= 1.0):
        print(f"Error: offset-x-ratio must be between 0.0 and 1.0, got {args.offset_x_ratio}")
        sys.exit(1)
    
    if not (0.0 <= args.offset_y_ratio <= 1.0):
        print(f"Error: offset-y-ratio must be between 0.0 and 1.0, got {args.offset_y_ratio}")
        sys.exit(1)
    
    # Validate scale ratio
    if args.scale_ratio <= 0:
        print(f"Error: scale-ratio must be a positive number, got {args.scale_ratio}")
        sys.exit(1)
    
    # Create animation generator
    generator = AnimationGenerator(
        config_path=args.config_file,
        target_offset_ratio=(args.offset_x_ratio, args.offset_y_ratio),
        fps=args.fps,
        canvas_color=args.canvas_color,
        scale_ratio=args.scale_ratio,
        repeat_fill=args.repeat_fill
    )
    
    print(f"Using target offset ratio: ({args.offset_x_ratio}, {args.offset_y_ratio})")
    print(f"Using canvas color: {args.canvas_color}")
    print(f"Using scale ratio: {args.scale_ratio}")
    if args.repeat_fill:
        print(f"Using repeat fill: {args.repeat_fill} frames")
    
    # Generate all animations
    json_file = generator.generate_all_animations()
    
    if json_file:
        print(f"\nAnimation generation completed successfully!")
        print(f"Summary saved to: {json_file}")
    else:
        print("No animations were generated.")


if __name__ == "__main__":
    main()
