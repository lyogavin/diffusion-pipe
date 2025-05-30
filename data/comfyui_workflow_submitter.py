#!/usr/bin/env python3
"""
ComfyUI Workflow Submitter
Submits ComfyUI workflows, polls for results, and uploads to Hugging Face.
"""

import json
import argparse
import time
import os
import sys
import requests
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import websocket
import threading
from urllib.parse import urljoin

try:
    from huggingface_hub import HfApi, login
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("Warning: huggingface_hub not available. Install with: pip install huggingface_hub")


class ComfyUIClient:
    def __init__(self, server_address: str = "localhost:8081"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.base_url = f"http://{server_address}"
        self.ws_url = f"ws://{server_address}/ws?clientId={self.client_id}"
        self.ws = None
        self.ws_thread = None
        self.messages = []
        self.completed_prompts = set()
        self.failed_prompts = set()
        
    def connect_websocket(self):
        """Connect to ComfyUI WebSocket for real-time updates"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.messages.append(data)
                
                if data['type'] == 'executed':
                    prompt_id = data['data']['prompt_id']
                    self.completed_prompts.add(prompt_id)
                    
                elif data['type'] == 'execution_error':
                    prompt_id = data['data']['prompt_id']
                    self.failed_prompts.add(prompt_id)
                    print(f"Execution error for prompt {prompt_id}: {data['data']}")
                    
            except json.JSONDecodeError:
                pass
                
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket connection closed")
            
        def on_open(ws):
            print("WebSocket connection opened")
            
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        time.sleep(1)  # Give websocket time to connect

    def submit_workflow(self, workflow: Dict[str, Any]) -> str:
        """Submit workflow to ComfyUI and return prompt_id"""
        try:
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            print(f"Submitting workflow to {self.base_url}/prompt...")
            print(f"Workflow has {len(workflow)} nodes")
            
            response = requests.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=30
            )
            
            # Print response details for debugging
            print(f"Response status code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error response content: {response.text}")
                try:
                    error_json = response.json()
                    if 'error' in error_json:
                        print(f"ComfyUI error details: {error_json['error']}")
                    if 'node_errors' in error_json:
                        print(f"Node errors: {error_json['node_errors']}")
                except:
                    pass
            
            response.raise_for_status()
            result = response.json()
            prompt_id = result['prompt_id']
            print(f"Workflow submitted successfully. Prompt ID: {prompt_id}")
            return prompt_id
            
        except requests.exceptions.RequestException as e:
            print(f"Error submitting workflow: {e}")
            print(f"Server address: {self.server_address}")
            print(f"Base URL: {self.base_url}")
            
            # Print workflow summary for debugging
            print("\nWorkflow summary:")
            for node_id, node_data in workflow.items():
                class_type = node_data.get('class_type', 'Unknown')
                print(f"  Node {node_id}: {class_type}")
            
            raise

    def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> bool:
        """Wait for workflow completion"""
        print(f"Waiting for completion of prompt {prompt_id}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if prompt_id in self.completed_prompts:
                print(f"Prompt {prompt_id} completed successfully!")
                return True
            elif prompt_id in self.failed_prompts:
                print(f"Prompt {prompt_id} failed!")
                return False
                
            time.sleep(2)
            
        print(f"Timeout waiting for prompt {prompt_id}")
        return False

    def get_history(self, prompt_id: str) -> Optional[Dict]:
        """Get execution history for a prompt"""
        try:
            response = requests.get(f"{self.base_url}/history/{prompt_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting history: {e}")
            return None

    def download_result(self, prompt_id: str, output_dir: str = "./outputs") -> Optional[str]:
        """Download the result file from ComfyUI"""
        history = self.get_history(prompt_id)
        if not history or prompt_id not in history:
            print(f"No history found for prompt {prompt_id}")
            return None
            
        execution_data = history[prompt_id]
        
        # Look for output files in the execution data
        for node_id, node_data in execution_data.get('outputs', {}).items():
            # Check for both 'videos' and 'gifs' (ComfyUI sometimes uses 'gifs' for video files)
            output_files = []
            if 'videos' in node_data:
                output_files = node_data['videos']
            elif 'gifs' in node_data:
                output_files = node_data['gifs']
            
            if output_files:
                file_info = output_files[0]  # Take the first file
                filename = file_info['filename']
                
                # Check if fullpath is available (direct file access)
                if 'fullpath' in file_info:
                    fullpath = file_info['fullpath']
                    print(f"Found result file at: {fullpath}")
                    
                    # Create output directory
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Copy file from fullpath to output directory
                    output_path = os.path.join(output_dir, filename)
                    try:
                        import shutil
                        shutil.copy2(fullpath, output_path)
                        print(f"Copied result to: {output_path}")
                        return output_path
                    except Exception as e:
                        print(f"Error copying file from {fullpath}: {e}")
                        # Fall back to download method
                        pass
                
                # Fallback: Download via ComfyUI API
                subfolder = file_info.get('subfolder', '')
                download_url = f"{self.base_url}/view"
                params = {
                    'filename': filename,
                    'subfolder': subfolder,
                    'type': 'output'
                }
                
                try:
                    print(f"Downloading via API: {filename}")
                    response = requests.get(download_url, params=params, stream=True)
                    response.raise_for_status()
                    
                    # Create output directory
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Save file
                    output_path = os.path.join(output_dir, filename)
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            
                    print(f"Downloaded result to: {output_path}")
                    return output_path
                    
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading file: {e}")
                    return None
                        
        print("No video/gif output found in execution results")
        return None

    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()


def load_workflow(workflow_path: str) -> Dict[str, Any]:
    """Load workflow from JSON file"""
    try:
        with open(workflow_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Workflow file not found: {workflow_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing workflow JSON: {e}")
        sys.exit(1)


def load_prompt_from_file(prompt_file_path: str) -> str:
    """Load prompt content from text file"""
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
        print(f"Loaded prompt from file: {prompt_file_path}")
        return prompt
    except FileNotFoundError:
        print(f"Prompt file not found: {prompt_file_path}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error reading prompt file (encoding issue): {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading prompt file: {e}")
        sys.exit(1)


def validate_workflow(workflow: Dict[str, Any]) -> bool:
    """Validate workflow structure before submitting"""
    print("Validating workflow...")
    
    if not isinstance(workflow, dict):
        print("Error: Workflow must be a dictionary")
        return False
    
    if len(workflow) == 0:
        print("Error: Workflow is empty")
        return False
    
    # Check for required nodes
    required_nodes = ["11", "16", "22", "27", "28", "30", "37", "38", "39", "56"]
    missing_nodes = []
    
    for node_id in required_nodes:
        if node_id not in workflow:
            missing_nodes.append(node_id)
    
    if missing_nodes:
        print(f"Warning: Missing expected nodes: {missing_nodes}")
    
    # Validate each node structure
    for node_id, node_data in workflow.items():
        if not isinstance(node_data, dict):
            print(f"Error: Node {node_id} must be a dictionary")
            return False
        
        if 'class_type' not in node_data:
            print(f"Error: Node {node_id} missing 'class_type'")
            return False
        
        if 'inputs' not in node_data:
            print(f"Error: Node {node_id} missing 'inputs'")
            return False
        
        if not isinstance(node_data['inputs'], dict):
            print(f"Error: Node {node_id} 'inputs' must be a dictionary")
            return False
    
    # Check specific node configurations
    if "56" in workflow:
        lora_input = workflow["56"]["inputs"].get("lora")
        if not lora_input:
            print("Warning: Node 56 (LoRA) has empty lora input")
    
    if "16" in workflow:
        prompt_input = workflow["16"]["inputs"].get("positive_prompt")
        if not prompt_input:
            print("Warning: Node 16 (Text Encode) has empty positive_prompt")
    
    if "37" in workflow:
        width = workflow["37"]["inputs"].get("width")
        height = workflow["37"]["inputs"].get("height")
        num_frames = workflow["37"]["inputs"].get("num_frames")
        if width:
            print(f"Info: Node 37 width: {width}")
        if height:
            print(f"Info: Node 37 height: {height}")
        if num_frames:
            print(f"Info: Node 37 num_frames: {num_frames}")
    
    print("Workflow validation completed")
    return True


def modify_workflow(workflow: Dict[str, Any], lora_name: str, prompt: str = None, width: int = None, height: int = None, num_frames: int = None) -> Dict[str, Any]:
    """Modify the LoRA name in node #56, optionally the prompt in node #16, and video dimensions in node #37 of the workflow"""
    # Modify LoRA in node #56
    if "56" in workflow:
        if "inputs" in workflow["56"]:
            workflow["56"]["inputs"]["lora"] = lora_name
            print(f"Updated LoRA in node #56 to: {lora_name}")
        else:
            print("Warning: No 'inputs' found in node #56")
    else:
        print("Warning: Node #56 not found in workflow")
    
    # Modify prompt in node #16 if provided
    if prompt:
        if "16" in workflow:
            if "inputs" in workflow["16"]:
                workflow["16"]["inputs"]["positive_prompt"] = prompt
                print(f"Updated positive prompt in node #16 to: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            else:
                print("Warning: No 'inputs' found in node #16")
        else:
            print("Warning: Node #16 not found in workflow")
    
    # Modify video dimensions in node #37 if provided
    if width is not None or height is not None or num_frames is not None:
        if "37" in workflow:
            if "inputs" in workflow["37"]:
                if width is not None:
                    workflow["37"]["inputs"]["width"] = width
                    print(f"Updated width in node #37 to: {width}")
                if height is not None:
                    workflow["37"]["inputs"]["height"] = height
                    print(f"Updated height in node #37 to: {height}")
                if num_frames is not None:
                    workflow["37"]["inputs"]["num_frames"] = num_frames
                    print(f"Updated num_frames in node #37 to: {num_frames}")
            else:
                print("Warning: No 'inputs' found in node #37")
        else:
            print("Warning: Node #37 not found in workflow")
    
    return workflow


def upload_to_huggingface(file_path: str, repo_id: str, hf_path: str, token: str = None, postfix: str = None, repo_type: str = None, dryrun: bool = False, keep_dryrun_file: bool = False):
    """Upload file to Hugging Face repository with optional filename postfix"""
    if not HF_AVAILABLE:
        print("Error: huggingface_hub not installed. Cannot upload to Hugging Face.")
        return False
    
    if dryrun:
        print("🧪 DRY RUN MODE: Testing upload process with real test file upload")
    
    # Add postfix to filename if provided
    if postfix:
        path_parts = hf_path.rsplit('.', 1)  # Split filename and extension
        if len(path_parts) == 2:
            hf_path = f"{path_parts[0]}_{postfix}.{path_parts[1]}"
        else:
            hf_path = f"{hf_path}_{postfix}"
        print(f"Added postfix to filename: {hf_path}")
    
    try:
        api = HfApi()
        
        # Login if token provided
        if token:
            if not dryrun:
                login(token=token)
            else:
                login(token=token)  # Need to login for dry run uploads too
            print("Successfully authenticated with Hugging Face" + (" (dry run)" if dryrun else ""))
        else:
            print("Warning: No Hugging Face token provided")
        
        print(f"Attempting to upload to repository: {repo_id}")
        print(f"Upload path: {hf_path}")
        print(f"Local file: {file_path}")
        
        # Check if file exists locally
        if not os.path.exists(file_path):
            print(f"Error: Local file does not exist: {file_path}")
            return False
        
        file_size = os.path.getsize(file_path)
        print(f"File size: {file_size / (1024*1024):.2f} MB")
        
        # Determine repository types to try
        if repo_type:
            repo_types = [repo_type]
            print(f"Using specified repository type: {repo_type}")
        else:
            repo_types = ["dataset", "model", "space"]
            print("Auto-detecting repository type...")
        
        for current_repo_type in repo_types:
            try:
                print(f"Trying to access repo as type '{current_repo_type}'...")
                
                # Check if repo exists (this works in dry run mode)
                try:
                    repo_info = api.repo_info(repo_id=repo_id, repo_type=current_repo_type)
                    print(f"✅ Repository found as type '{current_repo_type}': {repo_info.id}")
                    
                    if dryrun:
                        print(f"🧪 DRY RUN: Uploading test file {file_path} to {repo_id}/{hf_path} (type: {current_repo_type})")
                        print(f"🧪 DRY RUN: File size {file_size} bytes")
                        print(f"🧪 DRY RUN: Repository URL: https://huggingface.co/{repo_id}")
                        
                        # Actually upload the test file in dry run mode
                        result = api.upload_file(
                            path_or_fileobj=file_path,
                            path_in_repo=hf_path,
                            repo_id=repo_id,
                            repo_type=current_repo_type
                        )
                        
                        print(f"✅ Dry run upload completed successfully!")
                        print(f"🧪 Test file uploaded to: https://huggingface.co/{repo_id}/blob/main/{hf_path}")
                        print(f"Upload result: {result}")
                        
                        # Delete the test file from Hugging Face if not keeping it
                        if not keep_dryrun_file:
                            try:
                                print(f"🧪 Deleting test file from Hugging Face...")
                                api.delete_file(
                                    path_in_repo=hf_path,
                                    repo_id=repo_id,
                                    repo_type=current_repo_type
                                )
                                print(f"🧪 Test file deleted from Hugging Face")
                            except Exception as delete_error:
                                print(f"⚠️ Warning: Could not delete test file from HF: {delete_error}")
                                print(f"🧪 Test file remains at: https://huggingface.co/{repo_id}/blob/main/{hf_path}")
                        else:
                            print(f"🧪 Test file kept at: https://huggingface.co/{repo_id}/blob/main/{hf_path}")
                        
                        return True
                    else:
                        # Actual upload
                        print(f"🚀 Uploading {file_path} to {repo_id}/{hf_path}...")
                        result = api.upload_file(
                            path_or_fileobj=file_path,
                            path_in_repo=hf_path,
                            repo_id=repo_id,
                            repo_type=current_repo_type
                        )
                        
                        print(f"✅ Successfully uploaded {file_path} to {repo_id}/{hf_path} (type: {current_repo_type})")
                        print(f"Upload result: {result}")
                        return True
                    
                except Exception as repo_error:
                    print(f"❌ Failed with repo_type='{current_repo_type}': {repo_error}")
                    continue
                    
            except Exception as upload_error:
                print(f"❌ Upload failed for repo_type='{current_repo_type}': {upload_error}")
                continue
        
        # If all repo types failed, provide helpful error message
        error_prefix = "🧪 DRY RUN: Failed to upload test file" if dryrun else "❌ Failed to upload"
        print(f"\n{error_prefix} to {repo_id} with any repository type.")
        print("Common solutions:")
        print("1. Check if the repository exists on Hugging Face")
        print("2. Verify you have write access to the repository")
        print("3. Ensure your token has the correct permissions")
        print("4. Try creating the repository first if it doesn't exist")
        print(f"5. Check the repository URL: https://huggingface.co/{repo_id}")
        
        return False
        
    except Exception as e:
        error_prefix = "🧪 DRY RUN: Error uploading test file" if dryrun else "❌ Error"
        print(f"{error_prefix} uploading to Hugging Face: {e}")
        print(f"Repository: {repo_id}")
        print(f"File path: {hf_path}")
        
        # Additional debugging info
        try:
            from huggingface_hub.utils import get_token
            current_token = get_token()
            if current_token:
                print("Token is available")
            else:
                print("No token found - this might be the issue")
        except:
            pass
            
        return False


def main():
    parser = argparse.ArgumentParser(description="Submit ComfyUI workflow and upload results to Hugging Face")
    parser.add_argument("--lora", required=True, help="LoRA name to use in the workflow")
    parser.add_argument("--workflow", default="wand_trained_lora_eval_infer_v2-api.json", 
                       help="Path to workflow JSON file")
    parser.add_argument("--server", default="localhost:8081", 
                       help="ComfyUI server address")
    parser.add_argument("--hf-repo", required=True, 
                       help="Hugging Face repository ID (e.g., username/repo-name)")
    parser.add_argument("--hf-path", required=True, 
                       help="Path in Hugging Face repo to upload file")
    parser.add_argument("--hf-token", 
                       help="Hugging Face token (or set HF_TOKEN env var)")
    parser.add_argument("--hf-repo-type", choices=["dataset", "model", "space"], default=None,
                       help="Hugging Face repository type (auto-detect if not specified)")
    parser.add_argument("--hf-upload-dryrun", action="store_true",
                       help="Dry run: test upload process by uploading a test file")
    parser.add_argument("--hf-dryrun-keep-file", action="store_true",
                       help="Keep the test file on Hugging Face after dry run (default: delete it)")
    parser.add_argument("--output-dir", default="./outputs", 
                       help="Local directory to save outputs")
    parser.add_argument("--timeout", type=int, default=300, 
                       help="Timeout in seconds for workflow completion")
    parser.add_argument("--prompt-file", 
                       help="Path to text file containing the custom prompt to use in the workflow (node #16)")
    parser.add_argument("--postfix", 
                       help="Postfix to add to the uploaded filename")
    parser.add_argument("--debug", action="store_true",
                       help="Save the final workflow JSON for debugging")
    parser.add_argument("--width", type=int, default=None,
                       help="Video width in pixels (node #37)")
    parser.add_argument("--height", type=int, default=None,
                       help="Video height in pixels (node #37)")
    parser.add_argument("--num-frames", type=int, default=None,
                       help="Number of video frames (node #37)")
    
    args = parser.parse_args()
    
    # Get HF token from args or environment
    hf_token = args.hf_token or os.getenv('HF_TOKEN')
    
    # Load prompt from file if provided
    prompt = None
    if args.prompt_file:
        prompt = load_prompt_from_file(args.prompt_file)
    
    # Load and modify workflow
    workflow = load_workflow(args.workflow)
    workflow = modify_workflow(workflow, args.lora, prompt, args.width, args.height, args.num_frames)
    
    # Validate workflow before submitting
    if not validate_workflow(workflow):
        print("Workflow validation failed. Aborting.")
        sys.exit(1)
    
    # Save workflow for debugging if requested
    if args.debug:
        debug_filename = f"debug_workflow_{int(time.time())}.json"
        with open(debug_filename, 'w') as f:
            json.dump(workflow, f, indent=2)
        print(f"Debug: Saved final workflow to {debug_filename}")
    
    # Initialize ComfyUI client
    client = ComfyUIClient(args.server)
    
    try:
        # In dry run mode, skip workflow execution and create a test file
        if args.hf_upload_dryrun:
            print("🧪 DRY RUN MODE: Skipping workflow execution")
            print("🧪 Creating dummy test file for upload testing...")
            
            # Create output directory
            os.makedirs(args.output_dir, exist_ok=True)
            
            # Create a dummy test file
            test_filename = f"test_upload_{int(time.time())}.mp4"
            result_path = os.path.join(args.output_dir, test_filename)
            
            # Create a small dummy video file (just empty bytes for testing)
            with open(result_path, 'wb') as f:
                # Write some dummy data to make it look like a real file
                dummy_data = b"DUMMY_VIDEO_FILE_FOR_TESTING" * 1000  # ~27KB file
                f.write(dummy_data)
            
            print(f"🧪 Created test file: {result_path} ({os.path.getsize(result_path)} bytes)")
            
        else:
            # Normal mode: Connect to WebSocket and run workflow
            client.connect_websocket()
            
            # Submit workflow
            prompt_id = client.submit_workflow(workflow)
            
            # Wait for completion
            if client.wait_for_completion(prompt_id, args.timeout):
                # Download result
                result_path = client.download_result(prompt_id, args.output_dir)
                
                if not result_path:
                    print("Failed to download result file.")
                    sys.exit(1)
            else:
                print("Workflow execution failed or timed out.")
                sys.exit(1)
        
        # Upload to Hugging Face (works for both real files and test files)
        if result_path:
            if upload_to_huggingface(result_path, args.hf_repo, args.hf_path, hf_token, args.postfix, args.hf_repo_type, args.hf_upload_dryrun, args.hf_dryrun_keep_file):
                if args.hf_upload_dryrun:
                    print("🧪 Dry run completed successfully!")
                    # Clean up test file
                    if not args.hf_dryrun_keep_file:
                        os.remove(result_path)
                        print(f"🧪 Cleaned up test file: {result_path}")
                else:
                    print("Pipeline completed successfully!")
            else:
                error_msg = "Dry run upload test failed." if args.hf_upload_dryrun else "Pipeline completed but upload to Hugging Face failed."
                print(error_msg)
                if args.hf_upload_dryrun and os.path.exists(result_path):
                    if not args.hf_dryrun_keep_file:
                        os.remove(result_path)
                        print(f"🧪 Cleaned up test file: {result_path}")
                sys.exit(1)
        else:
            print("No result file available for upload.")
            sys.exit(1)
            
    finally:
        if not args.hf_upload_dryrun:
            client.close()


if __name__ == "__main__":
    main() 