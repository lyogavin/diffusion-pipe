#!/usr/bin/env python3
"""
Video Trimmer Tool
Cuts MP4 videos from specified start time to end time without changing size/FPS.
Uses FFmpeg for fast, high-quality video trimming.
"""

import subprocess
import os
import argparse
import json
from typing import Optional, Union

class VideoTrimmer:
    def __init__(self):
        """Initialize the video trimmer."""
        self.check_ffmpeg()
    
    def check_ffmpeg(self):
        """Check if FFmpeg is available."""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg not found. Please install FFmpeg first.\n"
                             "On macOS: brew install ffmpeg")
    
    def get_video_info(self, video_path: str) -> dict:
        """
        Get video information using ffprobe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary with video information
        """
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_streams', '-show_format', video_path
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
            
            # Get format info
            format_info = info.get('format', {})
            duration = float(format_info.get('duration', 0))
            
            return {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),  # Convert fraction to float
                'duration': duration,
                'codec': video_stream.get('codec_name', 'unknown'),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'size_mb': round(int(format_info.get('size', 0)) / (1024 * 1024), 2)
            }
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to get video info: {e}")
    
    def format_time(self, seconds: Union[int, float]) -> str:
        """
        Convert seconds to HH:MM:SS.mmm format for FFmpeg.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def validate_times(self, start_time: float, end_time: float, duration: float) -> None:
        """
        Validate start and end times against video duration.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            duration: Video duration in seconds
        """
        if start_time < 0:
            raise ValueError("Start time cannot be negative")
        
        if end_time <= start_time:
            raise ValueError("End time must be greater than start time")
        
        if start_time >= duration:
            raise ValueError(f"Start time ({start_time}s) exceeds video duration ({duration}s)")
        
        if end_time > duration:
            print(f"Warning: End time ({end_time}s) exceeds video duration ({duration}s). "
                  f"Will trim to end of video.")
    
    def trim_video(self, input_path: str, output_path: str, 
                   start_time: float, end_time: float,
                   fast_mode: bool = False,  # Changed default to False for accuracy
                   copy_streams: bool = False,  # Changed default to False for accuracy
                   cut_out: bool = False) -> None:  # New parameter for cutting OUT
        """
        Trim video from start_time to end_time, or cut out that segment.
        
        Args:
            input_path: Input MP4 file path
            output_path: Output MP4 file path
            start_time: Start time in seconds
            end_time: End time in seconds
            fast_mode: If True, use stream copy for faster processing
            copy_streams: If True, copy streams without re-encoding
            cut_out: If True, remove the segment between start_time and end_time
                    If False, keep only the segment between start_time and end_time
        """
        if not os.path.exists(input_path):
            raise ValueError(f"Input file does not exist: {input_path}")
        
        # Get video information
        try:
            video_info = self.get_video_info(input_path)
            print(f"Input video: {video_info['width']}x{video_info['height']}, "
                  f"{video_info['fps']:.2f} FPS, {video_info['duration']:.2f}s, "
                  f"{video_info['size_mb']} MB")
            print(f"Codec: {video_info['codec']}, Bitrate: {video_info['bitrate']} bps")
        except Exception as e:
            raise ValueError(f"Failed to analyze input video: {e}")
        
        # Validate times
        self.validate_times(start_time, end_time, video_info['duration'])
        
        if cut_out:
            # Cut OUT the segment - remove it and join the remaining parts
            print(f"Cutting OUT segment from {start_time:.2f}s to {end_time:.2f}s")
            print(f"Keeping: 0s to {start_time:.2f}s + {end_time:.2f}s to {video_info['duration']:.2f}s")
            self._cut_out_segment(input_path, output_path, start_time, end_time, 
                                video_info, fast_mode, copy_streams)
        else:
            # Original behavior - keep only the segment between start and end
            duration = min(end_time, video_info['duration']) - start_time
            start_formatted = self.format_time(start_time)
            duration_formatted = self.format_time(duration)
            
            print(f"Keeping segment from {start_formatted} for {duration_formatted} "
                  f"({start_time:.2f}s to {min(end_time, video_info['duration']):.2f}s)")
            
            self._trim_to_segment(input_path, output_path, start_time, end_time,
                                video_info, fast_mode, copy_streams)
    
    def _cut_out_segment(self, input_path: str, output_path: str, 
                        start_time: float, end_time: float, video_info: dict,
                        fast_mode: bool, copy_streams: bool) -> None:
        """Cut out a segment and join the remaining parts."""
        
        if start_time <= 0 and end_time >= video_info['duration']:
            raise ValueError("Cannot cut out the entire video")
        
        # Create temporary directory for segments
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            segments = []
            segment_files = []
            
            # First segment: 0 to start_time
            if start_time > 0:
                segment1_path = os.path.join(temp_dir, "segment1.mp4")
                self._extract_segment(input_path, segment1_path, 0, start_time, 
                                    fast_mode, copy_streams)
                segments.append(f"file '{segment1_path}'")
                segment_files.append(segment1_path)
            
            # Second segment: end_time to end of video
            if end_time < video_info['duration']:
                segment2_path = os.path.join(temp_dir, "segment2.mp4")
                self._extract_segment(input_path, segment2_path, end_time, 
                                    video_info['duration'], fast_mode, copy_streams)
                segments.append(f"file '{segment2_path}'")
                segment_files.append(segment2_path)
            
            if not segments:
                raise ValueError("No segments to concatenate")
            
            if len(segments) == 1:
                # Only one segment, just copy it
                import shutil
                shutil.copy2(segment_files[0], output_path)
                print(f"Single segment copied to: {output_path}")
            else:
                # Concatenate segments
                concat_file = os.path.join(temp_dir, "concat.txt")
                with open(concat_file, 'w') as f:
                    for segment in segments:
                        f.write(segment + '\n')
                
                self._concatenate_segments(concat_file, output_path, copy_streams)
    
    def _extract_segment(self, input_path: str, output_path: str, 
                        start_time: float, end_time: float,
                        fast_mode: bool, copy_streams: bool) -> None:
        """Extract a single segment."""
        duration = end_time - start_time
        start_formatted = self.format_time(start_time)
        duration_formatted = self.format_time(duration)
        
        print(f"  Extracting segment: {start_time:.2f}s to {end_time:.2f}s")
        
        # Build FFmpeg command for segment extraction
        cmd = ['ffmpeg', '-y']
        
        if fast_mode:
            cmd.extend(['-ss', start_formatted])
        
        cmd.extend(['-i', input_path])
        
        if not fast_mode:
            cmd.extend(['-ss', start_formatted])
        
        cmd.extend(['-t', duration_formatted])
        
        if copy_streams:
            cmd.extend(['-c', 'copy'])
            cmd.extend(['-avoid_negative_ts', 'make_zero'])
        else:
            cmd.extend([
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'medium',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '128k'
            ])
        
        cmd.append(output_path)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to extract segment: {e}")
    
    def _concatenate_segments(self, concat_file: str, output_path: str, 
                             copy_streams: bool) -> None:
        """Concatenate segments using FFmpeg."""
        print(f"  Concatenating segments...")
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file
        ]
        
        if copy_streams:
            cmd.extend(['-c', 'copy'])
        else:
            cmd.extend([
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'medium',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart'
            ])
        
        cmd.append(output_path)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Cut-out operation complete! Saved to: {output_path}")
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to concatenate segments: {e}")
    
    def _trim_to_segment(self, input_path: str, output_path: str,
                        start_time: float, end_time: float, video_info: dict,
                        fast_mode: bool, copy_streams: bool) -> None:
        """Original trim functionality - keep only the specified segment."""
        duration = min(end_time, video_info['duration']) - start_time
        start_formatted = self.format_time(start_time)
        duration_formatted = self.format_time(duration)
        
        # Build FFmpeg command
        cmd = ['ffmpeg', '-y']  # Overwrite output file
        
        if copy_streams and fast_mode:
            # Fast mode with stream copy - seek before input but add keyframe handling
            cmd.extend(['-ss', start_formatted])
            cmd.extend(['-i', input_path])
            cmd.extend(['-t', duration_formatted])
            # Use stream copy but avoid negative timestamps and handle keyframes
            cmd.extend(['-c', 'copy'])
            cmd.extend(['-avoid_negative_ts', 'make_zero'])
            # Add keyframe seeking to avoid black frames
            cmd.extend(['-copyts', '-start_at_zero'])
        elif copy_streams and not fast_mode:
            # Accurate mode with stream copy - seek after input for precision
            cmd.extend(['-i', input_path])
            cmd.extend(['-ss', start_formatted])
            cmd.extend(['-t', duration_formatted])
            cmd.extend(['-c', 'copy'])
            cmd.extend(['-avoid_negative_ts', 'make_zero'])
        else:
            # Re-encode mode - most accurate, handles all edge cases
            if fast_mode:
                # Seek before input for speed
                cmd.extend(['-ss', start_formatted])
            
            cmd.extend(['-i', input_path])
            
            if not fast_mode:
                # Seek after input for accuracy
                cmd.extend(['-ss', start_formatted])
            
            cmd.extend(['-t', duration_formatted])
            
            # Re-encode with high quality settings
            cmd.extend([
                '-c:v', 'libx264',
                '-crf', '18',  # High quality
                '-preset', 'medium',
                '-pix_fmt', 'yuv420p',  # Ensure compatibility
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart'  # Optimize for streaming
            ])
        
        # Output file
        cmd.append(output_path)
        
        print("Running FFmpeg command...")
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
                                if duration > 0:
                                    progress = min((current_seconds / duration) * 100, 100)
                                    print(f"Progress: {progress:.1f}% ({current_seconds:.1f}s/{duration:.1f}s)")
                        except (IndexError, ValueError):
                            pass
            
            # Wait for completion
            return_code = process.poll()
            if return_code != 0:
                stderr_output = process.stderr.read()
                raise subprocess.CalledProcessError(return_code, cmd, stderr_output)
            
            # Get output file info
            if os.path.exists(output_path):
                output_info = self.get_video_info(output_path)
                print(f"\nTrimming complete!")
                print(f"Output: {output_info['width']}x{output_info['height']}, "
                      f"{output_info['fps']:.2f} FPS, {output_info['duration']:.2f}s, "
                      f"{output_info['size_mb']} MB")
                print(f"Saved to: {output_path}")
            
        except subprocess.CalledProcessError as e:
            raise ValueError(f"FFmpeg failed: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error during video processing: {e}")
    
    def batch_trim(self, input_path: str, output_dir: str, 
                   segments: list, fast_mode: bool = False) -> None:
        """
        Trim multiple segments from the same video.
        
        Args:
            input_path: Input MP4 file path
            output_dir: Directory to save output segments
            segments: List of (start_time, end_time, name) tuples
            fast_mode: Use fast mode for processing
        """
        os.makedirs(output_dir, exist_ok=True)
        
        for i, (start_time, end_time, name) in enumerate(segments):
            output_path = os.path.join(output_dir, f"{name}.mp4")
            print(f"\nProcessing segment {i+1}/{len(segments)}: {name}")
            
            try:
                self.trim_video(input_path, output_path, start_time, end_time, fast_mode)
            except Exception as e:
                print(f"Failed to process segment '{name}': {e}")

def parse_time(time_str: str) -> float:
    """
    Parse time string in various formats to seconds.
    
    Supports:
    - Decimal seconds: "2.4", "30.5", "123.75"
    - Seconds (integer): "30", "90", "123"
    - MM:SS format: "02:30", "01:45.5"
    - HH:MM:SS format: "01:02:30", "00:01:45.25"
    - HH:MM:SS.mmm format: "01:02:30.500"
    
    Args:
        time_str: Time string in one of the supported formats
        
    Returns:
        Time in seconds as float
        
    Examples:
        parse_time("2.4") -> 2.4
        parse_time("30.5") -> 30.5
        parse_time("01:30.25") -> 90.25
        parse_time("00:02:30.5") -> 150.5
    """
    # Remove any whitespace
    time_str = time_str.strip()
    
    try:
        # Try parsing as float (seconds) - handles both integer and decimal
        value = float(time_str)
        if value < 0:
            raise ValueError("Time cannot be negative")
        return value
    except ValueError:
        # If it's not a simple number, try parsing as time format
        pass
    
    # Try parsing as time format (MM:SS or HH:MM:SS)
    parts = time_str.split(':')
    
    if len(parts) == 2:  # MM:SS format
        try:
            minutes = float(parts[0])
            seconds = float(parts[1])
            if minutes < 0 or seconds < 0 or seconds >= 60:
                raise ValueError("Invalid time values")
            return minutes * 60 + seconds
        except ValueError:
            raise ValueError(f"Invalid MM:SS format: {time_str}")
            
    elif len(parts) == 3:  # HH:MM:SS format
        try:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            if hours < 0 or minutes < 0 or seconds < 0 or minutes >= 60 or seconds >= 60:
                raise ValueError("Invalid time values")
            return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            raise ValueError(f"Invalid HH:MM:SS format: {time_str}")
    else:
        raise ValueError(f"Invalid time format: {time_str}. "
                        f"Supported formats: seconds (2.4), MM:SS (01:30.5), HH:MM:SS (01:02:30.5)")

def main():
    parser = argparse.ArgumentParser(
        description='Trim MP4 videos without changing size/FPS. Can either keep a segment or cut out a segment.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Time formats supported:
  - Decimal seconds: 2.4, 30.5, 123.75
  - Integer seconds: 30, 90, 123
  - MM:SS: 02:30, 01:45.5, 00:02.4
  - HH:MM:SS: 01:02:30, 00:01:45.25
  - HH:MM:SS.mmm: 01:02:30.500

Examples:
  # Keep only the segment from 2.4s to 30.5s:
  python video_trimmer.py input.mp4 output.mp4 --start 2.4 --end 30.5
  
  # Cut OUT the segment from 30s to 90s (remove it):
  python video_trimmer.py input.mp4 output.mp4 --start 30 --end 90 --cut-out
  
  # Regular trimming examples:
  python video_trimmer.py input.mp4 output.mp4 --start 01:30.5 --end 02:45.25
  python video_trimmer.py input.mp4 output.mp4 --start 00:02.4 --end 00:30.8
  
  # Performance options:
  python video_trimmer.py input.mp4 output.mp4 --start 30 --end 90 --fast
  python video_trimmer.py input.mp4 output.mp4 --start 30 --end 90 --copy --fast
        """
    )
    
    parser.add_argument('input', help='Input MP4 file path')
    parser.add_argument('output', help='Output MP4 file path')
    parser.add_argument('--start', '-s', required=True, 
                       help='Start time (decimal seconds like 2.4, or MM:SS, or HH:MM:SS)')
    parser.add_argument('--end', '-e', required=True,
                       help='End time (decimal seconds like 30.5, or MM:SS, or HH:MM:SS)')
    parser.add_argument('--fast', action='store_true',
                       help='Use fast mode (less accurate but faster)')
    parser.add_argument('--copy', action='store_true',
                       help='Use stream copy (fastest but may have keyframe issues)')
    parser.add_argument('--cut-out', action='store_true',
                       help='Cut OUT the segment between start and end (remove it), instead of keeping it')
    parser.add_argument('--info', '-i', action='store_true',
                       help='Show video information only')
    
    args = parser.parse_args()
    
    # Create trimmer
    trimmer = VideoTrimmer()
    
    # Show info if requested
    if args.info:
        try:
            info = trimmer.get_video_info(args.input)
            print(f"Video Information for: {args.input}")
            print(f"Resolution: {info['width']}x{info['height']}")
            print(f"FPS: {info['fps']:.2f}")
            print(f"Duration: {info['duration']:.2f} seconds")
            print(f"Codec: {info['codec']}")
            print(f"Bitrate: {info['bitrate']} bps")
            print(f"File size: {info['size_mb']} MB")
        except Exception as e:
            print(f"Error getting video info: {e}")
        return
    
    # Parse times
    try:
        start_time = parse_time(args.start)
        end_time = parse_time(args.end)
    except ValueError as e:
        print(f"Error parsing time: {e}")
        return
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file '{args.input}' does not exist")
        return
    
    try:
        trimmer.trim_video(
            args.input, 
            args.output, 
            start_time, 
            end_time,
            fast_mode=args.fast,
            copy_streams=args.copy,
            cut_out=args.cut_out
        )
    except Exception as e:
        print(f"Error during video trimming: {e}")

if __name__ == "__main__":
    main() 