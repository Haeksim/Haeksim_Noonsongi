from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent_lang.agent import get_agent_executor
from langchain_core.messages import HumanMessage
import os
import shutil
import uuid
import asyncio
import websocket
import ssl  
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="output_files"), name="static_files") 

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
    CLOUD_URL = os.getenv("CLOUD_URL")
    
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
        
        if CLOUD_URL and not processed_path.startswith("http"):
            # CLOUD_URL의 마지막 /는 제거하고 파일 경로의 시작 /는 제거하여 합침
            base_url = CLOUD_URL.rstrip('/')
            file_name = processed_path.lstrip('/')
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


async def process_fake_generation(task_id: str, prompt: str, wait_time: int):
    CLOUD_URL = os.getenv("CLOUD_URL")
    
    try:
        tasks[task_id]["status"] = "processing"
        print(f"🔄 [Fake Task {task_id}] 가짜 작업 시작. {wait_time}초 대기...")

        await asyncio.sleep(wait_time)
        
        processed_path = "result.mp4"
        base_url = CLOUD_URL.rstrip('/')
        final_url = f"{base_url}/static/{processed_path.replace(os.path.sep, '/')}" 

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = final_url
        tasks[task_id]["message"] = f"Fake completed after {wait_time} seconds with prompt: {prompt}"
        print(f"✅ [Fake Task {task_id}] 가짜 작업 완료: {final_url}")

    except Exception as e:
        print(f"❌ [Fake Task {task_id}] 에러 발생: {e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)


@app.post("/api/generate")
async def generate_response(
    background_tasks: BackgroundTasks, # FastAPI의 백그라운드 기능
    prompt: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # 1. 파일 서버에 저장하기 (프로젝트 루트 폴더)
        file_path = file.filename
        
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
    """
    프론트엔드 테스트용 비동기 API. 입력 프롬프트와 파일명을 받고, 
    5초~15초 사이를 랜덤으로 대기한 후 가짜 output.mp4 URL을 반환합니다.
    """
    import random
    
    # 5초에서 15초 사이 랜덤 대기 시간 설정
    wait_time = random.randint(5, 15) 

    task_id = str(uuid.uuid4())

    tasks[task_id] = {
        "status": "queued",
        "result": None,
        "error": None
    }

    # 파일이 넘어왔다면, 파일 저장 및 절대 경로 생성 로직이 필요합니다.
    # 여기서는 가짜 테스트를 위해 파일을 저장하지 않고 바로 가짜 작업으로 넘깁니다.
    
    background_tasks.add_task(process_fake_generation, task_id, prompt, wait_time)

    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"가짜 작업이 시작되었습니다. {wait_time}초 후 완료됩니다."
    }
    

@app.get("/api/status/{task_id}")
async def check_status(task_id: str):
    # ID가 없으면 404 에러
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task ID not found")
    
    # 현재 상태(processing, completed 등)와 결과를 반환
    return tasks[task_id]