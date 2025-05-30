import subprocess
import os
import argparse
import tempfile
import json
from typing import Tuple

class VideoTransformer:
    def __init__(self, scale_factor: float = 2.512, 
                 target_size: Tuple[int, int] = (772, 450),
                 original_center: Tuple[float, float] = (0.4958, 0.6507),
                 target_center: Tuple[float, float] = (0.4531, 0.8348),
                 background_color: str = "#00fdff"):
        """
        Initialize video transformer with specified parameters.
        
        Args:
            scale_factor: Factor to scale the video by (2.512x)
            target_size: Final output size (width, height) - (772, 450)
            original_center: Original character center as relative coordinates (x, y)
            target_center: Target character center as relative coordinates (x, y)
            background_color: Background color in hex format (#00fdff)
        """
        self.scale_factor = scale_factor
        self.target_width, self.target_height = target_size
        self.original_center = original_center
        self.target_center = target_center
        self.background_color = background_color
        
    def get_video_info(self, video_path: str) -> dict:
        """Get video information using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_streams', video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in info['streams']:
                if stream['codec_type'] == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                raise ValueError("No video stream found")
                
            return {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),  # Convert fraction to float
                'duration': float(video_stream.get('duration', 0))
            }
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to get video info: {e}")
    
    def calculate_crop_parameters(self, original_width: int, original_height: int) -> Tuple[int, int, int, int]:
        """
        Calculate FFmpeg crop parameters.
        
        Returns:
            Tuple of (crop_width, crop_height, crop_x, crop_y)
        """
        # Calculate scaled dimensions
        scaled_width = int(original_width * self.scale_factor)
        scaled_height = int(original_height * self.scale_factor)
        
        # Calculate original character position in scaled image
        orig_char_x = self.original_center[0] * scaled_width
        orig_char_y = self.original_center[1] * scaled_height
        
        # Calculate where character should be in target image
        target_char_x = self.target_center[0] * self.target_width
        target_char_y = self.target_center[1] * self.target_height
        
        # Calculate crop position to move character to target position
        crop_x = int(orig_char_x - target_char_x)
        crop_y = int(orig_char_y - target_char_y)
        
        # Ensure crop parameters are within bounds
        crop_x = max(0, min(crop_x, scaled_width - self.target_width))
        crop_y = max(0, min(crop_y, scaled_height - self.target_height))
        
        return self.target_width, self.target_height, crop_x, crop_y
    
    def build_ffmpeg_filter(self, original_width: int, original_height: int) -> str:
        """
        Build FFmpeg filter string for the transformation.
        
        Args:
            original_width: Original video width
            original_height: Original video height
            
        Returns:
            FFmpeg filter string
        """
        # Calculate scaled dimensions
        scaled_width = int(original_width * self.scale_factor)
        scaled_height = int(original_height * self.scale_factor)
        
        # Calculate crop parameters
        crop_w, crop_h, crop_x, crop_y = self.calculate_crop_parameters(original_width, original_height)
        
        # Build filter chain
        filters = []
        
        # 1. Scale the video
        filters.append(f"scale={scaled_width}:{scaled_height}:flags=lanczos")
        
        # 2. Add padding with background color to create a larger canvas if needed
        # This handles cases where crop might go outside the scaled video bounds
        pad_width = max(scaled_width, self.target_width + abs(crop_x))
        pad_height = max(scaled_height, self.target_height + abs(crop_y))
        
        if pad_width > scaled_width or pad_height > scaled_height:
            # Calculate padding offsets to center the scaled video
            pad_x = max(0, (pad_width - scaled_width) // 2)
            pad_y = max(0, (pad_height - scaled_height) // 2)
            
            filters.append(f"pad={pad_width}:{pad_height}:{pad_x}:{pad_y}:color={self.background_color}")
            
            # Adjust crop position for the padding
            crop_x += pad_x
            crop_y += pad_y
        
        # 3. Crop to final size
        filters.append(f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}")
        
        return ",".join(filters)
    
    def transform_video(self, input_path: str, output_path: str, 
                       quality: str = "high", progress_callback=None) -> None:
        """
        Transform the entire video file using FFmpeg.
        
        Args:
            input_path: Path to input MP4 file
            output_path: Path for output MP4 file
            quality: Quality preset ('high', 'medium', 'fast')
            progress_callback: Optional callback function for progress updates
        """
        if not os.path.exists(input_path):
            raise ValueError(f"Input file does not exist: {input_path}")
        
        # Get video information
        try:
            video_info = self.get_video_info(input_path)
            print(f"Input video: {video_info['width']}x{video_info['height']}, "
                  f"{video_info['fps']:.2f} FPS, {video_info['duration']:.2f}s")
        except Exception as e:
            raise ValueError(f"Failed to analyze input video: {e}")
        
        # Build filter
        filter_complex = self.build_ffmpeg_filter(video_info['width'], video_info['height'])
        print(f"Filter: {filter_complex}")
        
        # Quality presets
        quality_settings = {
            'high': ['-crf', '18', '-preset', 'slow'],
            'medium': ['-crf', '23', '-preset', 'medium'],
            'fast': ['-crf', '28', '-preset', 'fast']
        }
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg', '-y',  # Overwrite output file
            '-i', input_path,
            '-vf', filter_complex,
            '-c:v', 'libx264',  # H.264 codec
            '-c:a', 'aac',      # AAC audio codec
            '-b:a', '128k',     # Audio bitrate
        ]
        
        # Add quality settings
        cmd.extend(quality_settings.get(quality, quality_settings['medium']))
        
        # Add output
        cmd.append(output_path)
        
        print(f"Running FFmpeg command...")
        print(' '.join(cmd))
        
        try:
            # Run FFmpeg with progress monitoring
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor progress
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # Parse FFmpeg progress output
                    if 'time=' in output:
                        try:
                            time_str = output.split('time=')[1].split()[0]
                            # Convert time to seconds
                            time_parts = time_str.split(':')
                            if len(time_parts) == 3:
                                current_seconds = (float(time_parts[0]) * 3600 + 
                                                 float(time_parts[1]) * 60 + 
                                                 float(time_parts[2]))
                                if video_info['duration'] > 0:
                                    progress = (current_seconds / video_info['duration']) * 100
                                    print(f"Progress: {progress:.1f}% ({current_seconds:.1f}s/{video_info['duration']:.1f}s)")
                                    
                                    if progress_callback:
                                        progress_callback(progress)
                        except (IndexError, ValueError):
                            pass
            
            # Wait for completion
            return_code = process.poll()
            if return_code != 0:
                stderr_output = process.stderr.read()
                raise subprocess.CalledProcessError(return_code, cmd, stderr_output)
            
            print(f"Video transformation complete! Output saved to: {output_path}")
            
        except subprocess.CalledProcessError as e:
            raise ValueError(f"FFmpeg failed: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error during video processing: {e}")

def main():
    parser = argparse.ArgumentParser(description='Transform MP4 video with scaling and cropping using FFmpeg')
    parser.add_argument('input', help='Input MP4 file path')
    parser.add_argument('output', help='Output MP4 file path')
    parser.add_argument('--scale', type=float, default=2.512, 
                       help='Scale factor (default: 2.512)')
    parser.add_argument('--width', type=int, default=772, 
                       help='Target width (default: 772)')
    parser.add_argument('--height', type=int, default=450, 
                       help='Target height (default: 450)')
    parser.add_argument('--orig-center-x', type=float, default=0.4958,
                       help='Original character center X (default: 0.4958)')
    parser.add_argument('--orig-center-y', type=float, default=0.6507,
                       help='Original character center Y (default: 0.6507)')
    parser.add_argument('--target-center-x', type=float, default=0.4531,
                       help='Target character center X (default: 0.4531)')
    parser.add_argument('--target-center-y', type=float, default=0.8348,
                       help='Target character center Y (default: 0.8348)')
    parser.add_argument('--bg-color', type=str, default='#00fdff',
                       help='Background color in hex (default: #00fdff)')
    parser.add_argument('--quality', choices=['high', 'medium', 'fast'], 
                       default='medium', help='Quality preset (default: medium)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' does not exist")
        return
    
    # Create transformer
    transformer = VideoTransformer(
        scale_factor=args.scale,
        target_size=(args.width, args.height),
        original_center=(args.orig_center_x, args.orig_center_y),
        target_center=(args.target_center_x, args.target_center_y),
        background_color=args.bg_color
    )
    
    try:
        transformer.transform_video(args.input, args.output, quality=args.quality)
    except Exception as e:
        print(f"Error during video transformation: {e}")

if __name__ == "__main__":
    main()