from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent_lang.agent import get_agent_executor
from langchain_core.messages import HumanMessage
import time
import os
import shutil
import uuid
import asyncio
import websocket
import ssl  
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
OUTPUT_FILES_DIR = "output_files"
DOMAIN_URL="https://haeksimnoonsongi-production-9a31.up.railway.app/"
os.makedirs(OUTPUT_FILES_DIR, exist_ok=True) 


# 1. CORS 설정 (프론트엔드와 통신하기 위해 필수)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
tasks = {} 

class ChatRequest(BaseModel):
    prompt: str  # 프론트에서 { "prompt": "노래 만들어줘" } 형태로 보냄
    
@app.get("/api/test")
async def test_api():
    return {"status": "ok", "message": "API server is running normally!"}

@app.get("/api/test2")
async def test_websocket_connection():
    """
    CLOUD_URL 환경변수를 사용하여 ComfyUI WebSocket 연결을 테스트합니다.
    연결에 성공하면 status: ok를 반환합니다.
    """
    cloud_url = os.getenv("CLOUD_URL")
    
    if not cloud_url:
        return {"status": "failed", "message": "CLOUD_URL environment variable is missing."}

    # 1. http -> ws, https -> wss 변환
    if cloud_url.startswith("https"):
        ws_base = cloud_url.replace("https://", "wss://")
    else:
        ws_base = cloud_url.replace("http://", "ws://")
    
    # 2. WebSocket URL 구성
    client_id = str(uuid.uuid4())
    ws_url = f"{ws_base.rstrip('/')}/ws?clientId={client_id}"
    
    print(f"[TEST] Connecting to WebSocket: {ws_url}")
    
    try:
        # 3. 연결 시도 (Timeout 5초)
        ws = websocket.create_connection(ws_url, timeout=5, sslopt={"cert_reqs": ssl.CERT_NONE})
        
        if ws.connected:
            ws.close()
            return {"status": "ok", "message": f"WebSocket Connected Successfully to {ws_url}"}
        else:
             return {"status": "failed", "message": "WebSocket created but connection failed."}

    except Exception as e:
        print(f"[TEST] WebSocket Error: {e}")
        return {"status": "failed", "message": f"Connection Error: {str(e)}"}


@app.get("/api/test_cloud_urls")
async def test_cloud_urls():
    """
    CLOUD_URL_1~4 각각의 WebSocket 연결을 테스트하고 결과 반환
    """
    CLOUD_URLS = [
        os.getenv("CLOUD_URL_1"),
        os.getenv("CLOUD_URL_2"),
        os.getenv("CLOUD_URL_3"),
        os.getenv("CLOUD_URL_4")
    ]

    results = {}

    for i, cloud_url in enumerate(CLOUD_URLS, start=1):
        name = f"CLOUD_URL_{i}"

        if not cloud_url:
            results[name] = {
                "status": "failed",
                "message": f"{name} environment variable is missing."
            }
            continue

        # ws 또는 wss 변환
        if cloud_url.startswith("https"):
            ws_base = cloud_url.replace("https://", "wss://")
        else:
            ws_base = cloud_url.replace("http://", "ws://")

        client_id = str(uuid.uuid4())
        ws_url = f"{ws_base.rstrip('/')}/ws?clientId={client_id}"

        print(f"[TEST] Connecting to {name}: {ws_url}")

        try:
            ws = websocket.create_connection(
                ws_url,
                timeout=5,
                sslopt={"cert_reqs": ssl.CERT_NONE}
            )

            if ws.connected:
                ws.close()
                results[name] = {
                    "status": "ok",
                    "message": f"WebSocket Connected Successfully to {ws_url}"
                }
            else:
                results[name] = {
                    "status": "failed",
                    "message": "WebSocket created but not connected."
                }

        except Exception as e:
            print(f"[TEST] WebSocket Error ({name}): {e}")
            results[name] = {
                "status": "failed",
                "message": f"Connection Error: {str(e)}"
            }

    return results


async def process_generation(task_id: str, prompt: str, file_path: str):
    
    try:
        # 상태 업데이트: 처리 중
        tasks[task_id]["status"] = "processing"
        print(f"🔄 [Task {task_id}] 백그라운드 작업 시작...")

        # 에이전트 실행 준비
        combined_prompt = f"{prompt}\n\n[Attached File Path: {file_path}]"
        agent_executor = get_agent_executor()
        
        # 여기서 시간이 오래 걸림 (노래/영상 생성)
        response = await agent_executor.ainvoke({
            "messages": [HumanMessage(content=combined_prompt)]
        })
        
        # 결과 추출
        final_path = ""
        if "messages" in response and response["messages"]:
            last_message = response['messages'][-1]
            
            # last_message가 content 속성을 가진 객체인 경우
            if hasattr(last_message, 'content'):
                content = last_message.content
                
                # content가 리스트인 경우 (현재 상황)
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    
                    # 딕셔너리이고 'text' 키가 있는 경우
                    if isinstance(first_item, dict) and 'text' in first_item:
                        final_path = first_item['text']
                    else:
                        final_path = str(first_item)
                        
                # content가 문자열인 경우
                elif isinstance(content, str):
                    final_path = content
                else:
                    final_path = str(content)
                    
            # last_message가 문자열인 경우
            elif isinstance(last_message, str):
                final_path = last_message
            else:
                final_path = str(last_message)
                
        elif "output" in response:
            final_path = response.get("output", "")
        else:
            final_path = "No output generated"
        
        # 문자열이 아닌 경우 변환
        if not isinstance(final_path, str):
            final_path = str(final_path)
        
        processed_path = final_path.strip()
        final_url = processed_path
        
        if DOMAIN_URL and not processed_path.startswith("http"):
            
            # 1. 파일 이름만 추출
            file_name = os.path.basename(processed_path)
            
            # 2. 파일 복사/이동 (Agent가 생성한 파일이 존재할 경우)
            if os.path.exists(processed_path):
                destination_path = os.path.join(OUTPUT_FILES_DIR, file_name)
                if os.path.abspath(processed_path) != os.path.abspath(destination_path):
                    shutil.copy(processed_path, destination_path)
                    print(f"결과 파일 output_files로 복사 (덮어쓰기) 완료: {destination_path}")
                else:
                    print("동일 파일 경로 감지: copy 수행하지 않음.")
            
            # 3. URL 생성: https://도메인/static/파일명
            base_url = DOMAIN_URL.rstrip('/')
            final_url = f"{base_url}/static/{file_name.replace(os.path.sep, '/')}"
            
        # 작업 완료 처리
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = final_url
        print(f"✅ [Task {task_id}] 작업 완료: {final_url}")

    except Exception as e:
        print(f"❌ [Task {task_id}] 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)

OUTPUT_FILE_PATH = "output_files/result.mp4"

def process_fake_generation(wait_time: int):
    time.sleep(wait_time)

    os.makedirs("output_files", exist_ok=True)

    # 가짜 mp4 생성 (또는 기존 파일 overwrite)
    with open(OUTPUT_FILE_PATH, "wb") as f:
        f.write(b"fake mp4 content")

# --- [추가] 로컬 환경 테스트용 가짜 작업 처리 함수 ---
async def process_local_fake_generation(task_id: str, prompt: str, wait_time: int):
    # 로컬 테스트에서는 CLOUD_URL 환경변수를 사용하지 않습니다.
    LOCAL_URL = "http://127.0.0.1:8000" 
    
    try:
        tasks[task_id]["status"] = "processing"
        print(f"🔄 [Local Fake Task {task_id}] 로컬 테스트 시작. {wait_time}초 대기...")

        await asyncio.sleep(wait_time)
        
        processed_path = "result.mp4" 
        
        # URL 생성: 로컬 주소와 /static/파일명 형태로 생성
        final_url = f"{LOCAL_URL}/static/{processed_path.replace(os.path.sep, '/')}" 

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = final_url
        tasks[task_id]["message"] = f"Local Fake completed after {wait_time} seconds with prompt: {prompt}"
        print(f"✅ [Local Fake Task {task_id}] 가짜 작업 완료: {final_url}")

    except Exception as e:
        print(f"❌ [Local Fake Task {task_id}] 에러 발생: {e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)


@app.post("/api/generate")
async def generate_response(
    background_tasks: BackgroundTasks, # FastAPI의 백그라운드 기능
    prompt: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # [핵심 수정 6] 파일 이름 중복 방지: UUID와 원래 파일명 조합
        original_file_name = file.filename
        unique_file_name = f"{uuid.uuid4()}_{original_file_name}"
        
        # 1. 파일 서버에 저장하기 (프로젝트 루트 폴더에 임시 저장)
        file_path = unique_file_name
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 절대 경로로 변환 (에이전트가 파일을 확실히 찾을 수 있도록)
        abs_file_path = os.path.abspath(file_path)

        # 2. 작업 ID 생성 (대기표 번호)
        task_id = str(uuid.uuid4())

        # 3. 작업 목록에 '대기 중'으로 등록
        tasks[task_id] = {
            "status": "queued",
            "result": None,
            "error": None
        }

        # 4. 백그라운드 작업 시작 (기다리지 않고 함수만 등록해둠)
        background_tasks.add_task(process_generation, task_id, prompt, abs_file_path)

        # 5. 즉시 응답 (프론트엔드는 이 task_id를 받아서 로딩 화면을 띄움)
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "작업이 시작되었습니다. /api/status/{task_id} 로 상태를 확인하세요."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/generate_fake")
async def generate_fake_response_async(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    file: UploadFile = File(None)
):
    wait_time = 15  # 고정 15초 (원하면 random)

    # 기존 파일 제거 → 바로 접근 못 하게
    if os.path.exists(OUTPUT_FILE_PATH):
        os.remove(OUTPUT_FILE_PATH)

    background_tasks.add_task(process_fake_generation, wait_time)

    return {
        "status": "queued",
        "video_url": f"{DOMAIN_URL}/static/result.mp4",
        "message": "15초 후 영상이 생성됩니다."
    }

# --- [추가] 로컬 테스트용 가짜 API ---
@app.post("/api/generate_fake2")
async def generate_fake2_async(
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    file: UploadFile = File(None) 
):
    """
    로컬 환경에서 output_files/result.mp4 파일 접근 테스트용 비동기 API.
    """
    import random
    
    # 15초 고정 대기 시간 설정 (테스트 신속성 위해)
    wait_time = 15 

    task_id = str(uuid.uuid4())

    tasks[task_id] = {
        "status": "queued",
        "result": None,
        "error": None
    }
    
    # 로컬 전용 가짜 작업 함수 호출
    background_tasks.add_task(process_local_fake_generation, task_id, prompt, wait_time)

    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"로컬 테스트 작업이 시작되었습니다. {wait_time}초 후 완료됩니다."
    }
    

@app.get("/api/status/{task_id}")
async def check_status(task_id: str):
    # ID가 없으면 404 에러
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task ID not found")
    
    # 현재 상태(processing, completed 등)와 결과를 반환
    return tasks[task_id]

app.mount("/static", StaticFiles(directory=OUTPUT_FILES_DIR), name="static_files") 