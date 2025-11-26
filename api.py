from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent_lang.agent import get_agent_executor
from langchain_core.messages import HumanMessage
import os
import shutil
import uuid
import asyncio
from websocket import create_connection
import ssl  

app = FastAPI()

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
        if "messages" in response:
            final_path = response['messages'][-1].content
        elif "output" in response:
            final_path = response.get("output")
        else:
            final_path = "No output generated"

        # 작업 완료 처리
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = final_path.strip()
        print(f"✅ [Task {task_id}] 작업 완료: {final_path}")

    except Exception as e:
        print(f"❌ [Task {task_id}] 에러 발생: {e}")
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
    

@app.get("/api/status/{task_id}")
async def check_status(task_id: str):
    # ID가 없으면 404 에러
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task ID not found")
    
    # 현재 상태(processing, completed 등)와 결과를 반환
    return tasks[task_id]