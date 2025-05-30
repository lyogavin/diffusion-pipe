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
            response = requests.post(
                f"{self.base_url}/prompt",
                json={
                    "prompt": workflow,
                    "client_id": self.client_id
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            prompt_id = result['prompt_id']
            print(f"Workflow submitted successfully. Prompt ID: {prompt_id}")
            return prompt_id
            
        except requests.exceptions.RequestException as e:
            print(f"Error submitting workflow: {e}")
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
            if 'videos' in node_data:
                videos = node_data['videos']
                if videos:
                    video_info = videos[0]  # Take the first video
                    filename = video_info['filename']
                    subfolder = video_info.get('subfolder', '')
                    
                    # Download the file
                    download_url = f"{self.base_url}/view"
                    params = {
                        'filename': filename,
                        'subfolder': subfolder,
                        'type': 'output'
                    }
                    
                    try:
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
                        
        print("No video output found in execution results")
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


def modify_workflow(workflow: Dict[str, Any], lora_name: str, prompt: str = None) -> Dict[str, Any]:
    """Modify the LoRA name in node #56 and optionally the prompt in node #16 of the workflow"""
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
    
    return workflow


def upload_to_huggingface(file_path: str, repo_id: str, hf_path: str, token: str = None, postfix: str = None):
    """Upload file to Hugging Face repository with optional filename postfix"""
    if not HF_AVAILABLE:
        print("Error: huggingface_hub not installed. Cannot upload to Hugging Face.")
        return False
    
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
            login(token=token)
        
        # Upload file
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=hf_path,
            repo_id=repo_id,
            repo_type="dataset"  # Change to "model" if needed
        )
        
        print(f"Successfully uploaded {file_path} to {repo_id}/{hf_path}")
        return True
        
    except Exception as e:
        print(f"Error uploading to Hugging Face: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Submit ComfyUI workflow and upload results to Hugging Face")
    parser.add_argument("--lora", required=True, help="LoRA name to use in the workflow")
    parser.add_argument("--workflow", default="wand_trained_lora_eval_infer-api.json", 
                       help="Path to workflow JSON file")
    parser.add_argument("--server", default="localhost:8081", 
                       help="ComfyUI server address")
    parser.add_argument("--hf-repo", required=True, 
                       help="Hugging Face repository ID (e.g., username/repo-name)")
    parser.add_argument("--hf-path", required=True, 
                       help="Path in Hugging Face repo to upload file")
    parser.add_argument("--hf-token", 
                       help="Hugging Face token (or set HF_TOKEN env var)")
    parser.add_argument("--output-dir", default="./outputs", 
                       help="Local directory to save outputs")
    parser.add_argument("--timeout", type=int, default=300, 
                       help="Timeout in seconds for workflow completion")
    parser.add_argument("--prompt", 
                       help="Custom positive prompt to use in the workflow (node #16)")
    parser.add_argument("--postfix", 
                       help="Postfix to add to the uploaded filename")
    
    args = parser.parse_args()
    
    # Get HF token from args or environment
    hf_token = args.hf_token or os.getenv('HF_TOKEN')
    
    # Load and modify workflow
    workflow = load_workflow(args.workflow)
    workflow = modify_workflow(workflow, args.lora, args.prompt)
    
    # Initialize ComfyUI client
    client = ComfyUIClient(args.server)
    
    try:
        # Connect to WebSocket for real-time updates
        client.connect_websocket()
        
        # Submit workflow
        prompt_id = client.submit_workflow(workflow)
        
        # Wait for completion
        if client.wait_for_completion(prompt_id, args.timeout):
            # Download result
            result_path = client.download_result(prompt_id, args.output_dir)
            
            if result_path:
                # Upload to Hugging Face
                if upload_to_huggingface(result_path, args.hf_repo, args.hf_path, hf_token, args.postfix):
                    print("Pipeline completed successfully!")
                else:
                    print("Pipeline completed but upload to Hugging Face failed.")
                    sys.exit(1)
            else:
                print("Failed to download result file.")
                sys.exit(1)
        else:
            print("Workflow execution failed or timed out.")
            sys.exit(1)
            
    finally:
        client.close()


if __name__ == "__main__":
    main() 