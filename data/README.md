# ComfyUI Workflow Submitter

This Python script submits ComfyUI workflows to a local ComfyUI instance, polls for completion, and uploads the results to Hugging Face repositories.

## Features

- ✅ Submits ComfyUI workflows via REST API
- ✅ Real-time monitoring via WebSocket connection
- ✅ Automatic LoRA parameter modification in node #56
- ✅ Custom prompt modification in node #16
- ✅ Downloads completed video results
- ✅ Uploads results to Hugging Face repositories with custom filename postfix
- ✅ Comprehensive error handling and logging

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have ComfyUI running locally on `localhost:8081` (or specify a different address)

3. (Optional) Set up your Hugging Face token:
```bash
export HF_TOKEN="your_huggingface_token_here"
```

## Usage

### Basic Usage

```bash
python comfyui_workflow_submitter.py \
  --lora "my_custom_lora.safetensors" \
  --hf-repo "username/my-repo" \
  --hf-path "outputs/my_video.mp4"
```

### Full Example with Custom Prompt and Postfix

```bash
python comfyui_workflow_submitter.py \
  --lora "epoch280/my_trained_lora.safetensors" \
  --prompt "A beautiful sunset over mountains, cinematic style, 4k quality" \
  --postfix "experiment_001" \
  --workflow "wand_trained_lora_eval_infer-api.json" \
  --server "localhost:8081" \
  --hf-repo "myusername/video-results" \
  --hf-path "outputs/sunset_video.mp4" \
  --hf-token "hf_xxxxxxxxxxxx" \
  --output-dir "./local_outputs" \
  --timeout 600
```

## Arguments

### Required Arguments

- `--lora`: LoRA model name to use (replaces the value in node #56)
- `--hf-repo`: Hugging Face repository ID (format: `username/repo-name`)
- `--hf-path`: Path within the HF repository to upload the file

### Optional Arguments

- `--workflow`: Path to workflow JSON file (default: `wand_trained_lora_eval_infer-api.json`)
- `--server`: ComfyUI server address (default: `localhost:8081`)
- `--hf-token`: Hugging Face token (can also use `HF_TOKEN` env var)
- `--output-dir`: Local directory for downloads (default: `./outputs`)
- `--timeout`: Timeout in seconds for workflow completion (default: 300)
- `--prompt`: Custom positive prompt to use in the workflow (replaces prompt in node #16)
- `--postfix`: Postfix to add to the uploaded filename (e.g., `video.mp4` becomes `video_experiment001.mp4`)

## Workflow Process

1. **Load Workflow**: Reads the JSON workflow file
2. **Modify LoRA**: Updates node #56 with the specified LoRA name
3. **Modify Prompt**: (Optional) Updates node #16 with custom positive prompt
4. **Submit**: Sends the workflow to ComfyUI via REST API
5. **Monitor**: Uses WebSocket to monitor execution progress
6. **Download**: Downloads the generated video file
7. **Upload**: Uploads the result to the specified Hugging Face repository with optional filename postfix

## ComfyUI Workflow Structure

The script expects a ComfyUI workflow with:
- Node #56: `WanVideoLoraSelect` class with LoRA configuration
- Node #16: `WanVideoTextEncode` class with prompt configuration
- Video output from `VHS_VideoCombine` node

The included `wand_trained_lora_eval_infer-api.json` workflow generates videos using the WanVideo model.

## Error Handling

The script handles various error conditions:
- Network connectivity issues
- ComfyUI execution errors
- File download failures
- Hugging Face upload problems
- WebSocket connection issues

## Environment Variables

- `HF_TOKEN`: Your Hugging Face authentication token

## Example Output

```
Updated LoRA in node #56 to: my_custom_lora.safetensors
Updated positive prompt in node #16 to: A beautiful sunset over mountains, cinematic style, 4k quality
WebSocket connection opened
Workflow submitted successfully. Prompt ID: abc123-def456-789
Waiting for completion of prompt abc123-def456-789...
Prompt abc123-def456-789 completed successfully!
Downloaded result to: ./outputs/WanVideo2_1_T2V_00001.mp4
Added postfix to filename: outputs/sunset_video_experiment_001.mp4
Successfully uploaded ./outputs/WanVideo2_1_T2V_00001.mp4 to username/repo/outputs/sunset_video_experiment_001.mp4
Pipeline completed successfully!
```

## Troubleshooting

### ComfyUI Connection Issues
- Ensure ComfyUI is running on the specified port
- Check if the server address is correct
- Verify firewall settings

### Hugging Face Upload Issues
- Ensure your token has write permissions
- Check repository exists and you have access
- Verify the repository type (dataset vs model)

### Workflow Execution Issues
- Check that all required models are available in ComfyUI
- Verify LoRA files exist in the specified path
- Monitor ComfyUI logs for detailed error messages

## Dependencies

- `requests`: HTTP client for REST API calls
- `websocket-client`: WebSocket client for real-time monitoring
- `huggingface-hub`: Hugging Face repository interactions 