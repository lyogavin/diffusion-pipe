# OpenBor Animation Generator

This Python program generates MP4 animations from OpenBor character configuration files. It processes animation definitions, handles frame timing, and creates video files with proper offset handling.

## Features

- **OpenBor Config Parsing**: Reads and parses OpenBor `.txt` configuration files
- **Animation Processing**: Handles `anim`, `frame`, `delay`, and `offset` commands
- **Offset Normalization**: Adjusts all animations to use a consistent offset point
- **Video Generation**: Creates MP4 videos with customizable frame rates
- **Idle Frame Padding**: Automatically adds idle frames at the beginning and end of each animation
- **Canvas Color Customization**: Set custom background colors for video canvases
- **Ratio-Based Positioning**: Consistent character positioning using ratio coordinates
- **Video Scaling**: Scale output video dimensions with high-quality resampling
- **Proper Canvas Filling**: Ensures canvas color fills all blank areas (no black strips)
- **Repeat Fill**: Automatically extend animations to target frame counts based on loop settings
- **JSON Summary**: Generates a summary file with animation details

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python process_obor_assets.py path/to/config.txt
```

### Advanced Usage

```bash
python process_obor_assets.py path/to/config.txt --offset-x-ratio 0.6 --offset-y-ratio 0.7 --fps 24 --canvas-color "#FF0000" --scale-ratio 2.0 --repeat-fill 60
```

### Command Line Arguments

- `config_file`: Path to the OpenBor configuration `.txt` file (required)
- `--offset-x-ratio`: Target offset X ratio (0.0 to 1.0, default: 0.5) - 0.0 = left edge, 1.0 = right edge
- `--offset-y-ratio`: Target offset Y ratio (0.0 to 1.0, default: 0.8) - 0.0 = top edge, 1.0 = bottom edge  
- `--fps`: Frames per second for output videos (default: 16)
- `--canvas-color`: Canvas background color in hex format (default: #000000)
- `--scale-ratio`: Scale factor for output video dimensions (default: 1.0)
- `--repeat-fill`: Target frame count for repeat filling (respects loop setting)

### Offset Ratio System

The new ratio-based offset system provides more flexible positioning:
- **X Ratio**: 0.0 = left edge, 0.5 = center, 1.0 = right edge
- **Y Ratio**: 0.0 = top edge, 0.5 = center, 1.0 = bottom edge

This ensures consistent character positioning regardless of image dimensions.

### Video Scaling

The scale ratio feature allows you to resize the entire output video:
- **Scale Ratio > 1.0**: Upscales the video (e.g., 2.0 = double size)
- **Scale Ratio < 1.0**: Downscales the video (e.g., 0.5 = half size)
- **Scale Ratio = 1.0**: Original size (default)

Examples:
- `--scale-ratio 2.0`: A 320x240 image becomes 640x480 video
- `--scale-ratio 0.5`: A 320x240 image becomes 160x120 video
- `--scale-ratio 1.5`: A 320x240 image becomes 480x360 video

The scaling uses high-quality LANCZOS resampling for best visual results.

### Repeat Fill Feature

The repeat fill feature allows you to extend animations to a specific frame count, respecting the animation's loop setting:

**Loop Setting Behavior**:
- **loop 1** (Repeatable): The animation frames are repeated cyclically until the target frame count is reached
- **loop 0** (Non-repeatable): The animation plays once, then idle frames fill the remaining time

**Usage Examples**:
```bash
# Extend all animations to 60 frames
python process_obor_assets.py config.txt --repeat-fill 60

# Create 2-second videos at 30 FPS (60 frames total)
python process_obor_assets.py config.txt --fps 30 --repeat-fill 60
```

**Behavior Details**:
- If an animation already has more frames than the target, it remains unchanged
- For repeatable animations (loop=1), the core animation frames are repeated
- For non-repeatable animations (loop=0), idle frames are added at the end
- Idle frames at the beginning and end are preserved and not counted in the repeat cycle

### Canvas Color Options

You can specify any hex color for the canvas background:
- `#000000` - Black (default)
- `#FFFFFF` - White  
- `#FF0000` - Red
- `#00FF00` - Green
- `#0000FF` - Blue
- `#808080` - Gray

## Input Format

The program expects an OpenBor configuration file with the following supported commands:

### Animation Definition
```
anim animation_name
```

### Frame Commands
```
frame path/to/image.png
```

### Timing Control
```
delay 15
```

### Position Control
```
offset 100 200
```

### Loop Control
```
loop 1
```

### Example OpenBor Config
```
anim idle
    offset 100 200
    delay 10
    loop 1
    frame data/chars/hero/idle_0.png
    frame data/chars/hero/idle_1.png
    frame data/chars/hero/idle_2.png

anim attack
    offset 102 189
    delay 6
    loop 0
    frame data/chars/hero/attack_0.png
    delay 15
    frame data/chars/hero/attack_1.png
    frame data/chars/hero/attack_2.png
```

## Output

The program generates:

1. **MP4 Videos**: One video file per animation (e.g., `idle.mp4`, `attack.mp4`)
2. **JSON Summary**: A summary file containing animation metadata

### JSON Output Format
```json
[
  {
    "animation": "idle",
    "video": "idle.mp4",
    "frames": 25
  },
  {
    "animation": "attack", 
    "video": "attack.mp4",
    "frames": 18
  }
]
```

## How It Works

### 1. Config Parsing
The program reads the OpenBor configuration file and extracts:
- Animation names
- Frame image paths
- Timing delays (in centiseconds)
- Offset coordinates

### 2. Offset Normalization
All animations are adjusted to use the same offset coordinates:
- Images are repositioned based on offset differences
- Empty areas are padded using edge pixel colors
- This ensures consistent character positioning across all animations

### 3. Video Generation
For each animation:
- Adds one idle frame at the beginning
- Processes all animation frames with proper timing
- Adds one idle frame at the end
- Converts delays from centiseconds to frame counts based on FPS
- Outputs as MP4 video

### 4. Frame Processing
- Supports various image formats (PNG, GIF, etc.)
- Handles missing images with placeholder frames
- Maintains aspect ratios and centers images on canvas
- Uses edge-based padding for offset adjustments

## Directory Structure

The program expects the following structure:
```
project_directory/
├── config.txt              # OpenBor configuration file
├── image1.png              # Animation frame images
├── image2.png
├── ...
└── generated_outputs/
    ├── idle.mp4            # Generated animation videos
    ├── attack.mp4
    └── config_animations.json  # Summary file
```

## Troubleshooting

### Common Issues

1. **Missing Images**: The program will create gray placeholder frames for missing images
2. **Invalid Delays**: Delays less than 1 centisecond are automatically set to 1 frame
3. **No Idle Animation**: If no idle animation is found, videos won't have padding frames
4. **Black Strips in Videos**: Fixed! The program now properly fills all blank areas with the specified canvas color

### Canvas Color Fix

Previous versions might have shown black strips at the top/bottom or sides of generated videos when images had different aspect ratios. This has been fixed by:

- **Proper Canvas Filling**: All blank areas are now filled with the specified canvas color
- **Ratio-Based Positioning**: Images are positioned using the offset ratio system instead of simple centering
- **Consistent Background**: The canvas color is applied uniformly across all video generation methods

### Error Messages

- `"Image not found"`: Check that image files exist in the same directory as the config file
- `"No animations found"`: Verify the config file format and animation definitions
- `"Animation has no frames"`: Ensure each animation has at least one frame command

## Dependencies

- **OpenCV**: For video generation and image processing
- **Pillow**: For advanced image format support and manipulation
- **NumPy**: For efficient array operations

## License

This program is provided as-is for OpenBor animation processing. 

**Final Usage Examples**:
```bash
# Basic usage
python process_obor_assets.py config.txt

# Advanced usage with all features
python process_obor_assets.py config.txt --canvas-color "#FF0000" --offset-x-ratio 0.2 --offset-y-ratio 0.3 --scale-ratio 2.0 --repeat-fill 60
``` 