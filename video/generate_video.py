from websocket import create_connection
import uuid
import json
import urllib.request
import urllib.parse
import requests
import os
import ssl
from itertools import cycle
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

IMAGE_DIR = "images"
image_paths = [
    os.path.join(IMAGE_DIR, f"nunsong_variation_{i}.png")
    for i in range(1, 5)
]
image_cycle = cycle(image_paths)


class ComfyCloudClient:
    def __init__(self, base_url, auth_token=None, comfy_api_key=None):
        self.base_url = base_url.rstrip('/')
        self.client_id = str(uuid.uuid4())
        self.headers = {}
        self.comfy_api_key = comfy_api_key 
        
        if auth_token:
            self.headers['Authorization'] = f"Bearer {auth_token}"

    def get_ws_url(self):
        if self.base_url.startswith("https"):
            return self.base_url.replace("https://", "wss://")
        else:
            return self.base_url.replace("http://", "ws://")

    def upload_image(self, image_path, overwrite=False):
        url = f"{self.base_url}/upload/image"
        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                data = {'overwrite': str(overwrite).lower()}
                response = requests.post(url, files=files, data=data, headers=self.headers)
        except FileNotFoundError:
            raise Exception(f"로컬에서 파일을 찾을 수 없습니다: {image_path}")

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Image upload failed: {response.text}")

    def queue_prompt(self, workflow):
        url = f"{self.base_url}/prompt"
        
        extra_data = {
            "extra_pnginfo": {"workflow": workflow}
        }
        
        if self.comfy_api_key:
            extra_data["api_key"] = self.comfy_api_key
            extra_data["api_key_comfy_org"] = self.comfy_api_key
            extra_data["cd_token"] = self.comfy_api_key

        payload = {
            "prompt": workflow,
            "client_id": self.client_id,
            "extra_data": extra_data 
        }
        
        headers = self.headers.copy()
        if self.comfy_api_key:
            headers['Authorization'] = f"Bearer {self.comfy_api_key}"

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Queue prompt failed: {response.text}")

    def get_history(self, prompt_id):
        url = f"{self.base_url}/history/{prompt_id}"
        response = requests.get(url, headers=self.headers)
        return response.json()

    @staticmethod
    def inject_prompt_to_workflow(workflow, prompt: str, time: int):
        prompt_node_id = "13"
        image_node_id = "12"

        # prompt/time 입력
        workflow[prompt_node_id]["inputs"]["prompt"] = prompt
        workflow[prompt_node_id]["inputs"]["duration"] = time

        # 순환 이미지 선택
        selected_image = next(image_cycle)

        # 이미지 경로 직접 저장
        workflow[image_node_id]["inputs"]["images"] = selected_image

        return workflow

    def execute_workflow(self, workflow_file_path):
        with open(workflow_file_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # inject_prompt_to_workflow에서 넣어준 이미지 경로 읽기
        image_node_id = "12"
        local_image_path = workflow[image_node_id]["inputs"]["images"]

        print(f"[*] Uploading image: {local_image_path}")
        upload_resp = self.upload_image(local_image_path, overwrite=True)
        server_filename = upload_resp['name']

        # ComfyUI workflow 이미지 노드 12번에 파일명 삽입
        workflow[image_node_id]["inputs"]["image"] = server_filename
        print(f"[*] Workflow updated: Node {image_node_id} set to '{server_filename}'")

        # WebSocket 연결
        ws_url = f"{self.get_ws_url()}/ws?clientId={self.client_id}"
        print(f"ws_url: {ws_url}")
        
        ws = websocket.WebSocket()
        
        try:
            ws.connect(ws_url, sslopt={"cert_reqs": ssl.CERT_NONE})
            print(f"[*] WebSocket Connected: {ws_url}")
        except Exception as e:
            print(f"[!] WebSocket Connection Failed: {e}")
            raise e 

        try:
            resp = self.queue_prompt(workflow)
            prompt_id = resp['prompt_id']
            print(f"[*] Prompt Queued. ID: {prompt_id}")

            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    msg_type = message['type']
                    
                    if msg_type == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            print("[*] Execution Finished!")
                            break
                        elif data['prompt_id'] == prompt_id:
                            print(f"[-] Node Executing: {data['node']}")
                            
                    elif msg_type == 'execution_error':
                        print(f"[!] Execution Error: {message['data']}")
                        break
        finally:
            ws.close()

        history = self.get_history(prompt_id)
        outputs = history[prompt_id].get('outputs', {})
        
        print("\n[Result Files]")
        results = []
        saved_files = []

        for node_id, output_data in outputs.items():
            for key in ['videos', 'images', 'gifs']:
                if key in output_data:
                    for item in output_data[key]:
                        file_url = f"{self.base_url}/view?filename={item['filename']}&subfolder={item['subfolder']}&type={item['type']}"
                        print(f"Output ({key}): {file_url}")
                        results.append(file_url)

                        save_dir = os.path.join("files", "generated_videos")
                        os.makedirs(save_dir, exist_ok=True)

                        local_path = os.path.join(save_dir, item['filename'])

                        try:
                            r = requests.get(file_url)
                            r.raise_for_status()
                            with open(local_path, "wb") as f:
                                f.write(r.content)
                            print(f"[*] Saved locally: {local_path}")
                            saved_files.append(local_path)
                        except Exception as e:
                            print(f"[!] Failed to save {file_url}: {e}")
                            continue

        return {
            "urls": results,
            "local_files": saved_files
        }


def load_prompt_by_index(index: int):
    with open("files/video_prompt.json", "r") as f:
        data = json.load(f)
    for item in data:
        if item["segment"] == index:
            return item
    raise Exception(f"Index {index} not found in video_prompt.json")


@tool
def generate_video_tool(index: int) -> list:
    """
    Generates a video using a ComfyUI workflow,
    automatically selecting a rotating variation image.
    """

    CLOUD_URL=os.getenv("CLOUD_URL")
    COMFY_API_KEY= os.getenv("COMFY_API_KEY")
    
    item = load_prompt_by_index(index)
    prompt = item["prompt"]
    time = item["time"]

    print(f"[*] Using prompt index={index}")
    print(f"    Time: {time}")
    print(f"    Prompt: {prompt[:50]}...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    workflow_file_path = os.path.join(current_dir, "video_workflow_api.json")

    with open(workflow_file_path, "r") as f:
        workflow = json.load(f)
    
    # inject prompt + time + image
    workflow = ComfyCloudClient.inject_prompt_to_workflow(workflow, prompt, time)

    # 임시 workflow 저장
    tmp_workflow_path = os.path.join(current_dir, f"workflow_index_{index}.json")
    with open(tmp_workflow_path, "w") as f:
        json.dump(workflow, f, indent=4)

    client = ComfyCloudClient(CLOUD_URL, auth_token=None, comfy_api_key=COMFY_API_KEY)
    
    try:
        return client.execute_workflow(tmp_workflow_path)
    except Exception as e:
        return [f"Error: {e}"]