from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent_lang.agent import get_agent_executor
from langchain_core.messages import HumanMessage
import os
import shutil

app = FastAPI()

# 1. CORS 설정 (프론트엔드와 통신하기 위해 필수)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    prompt: str  # 프론트에서 { "prompt": "노래 만들어줘" } 형태로 보냄
    
@app.get("/api/test")
async def test_api():
    """서버가 정상 작동 중인지 확인하는 헬스 체크용 API"""
    return {"status": "ok", "message": "API server is running normally!"}

@app.post("/api/generate")
async def generate_response(
    prompt: str = Form(...),       # 프롬프트는 Form 형식으로 받음
    file: UploadFile = File(...)   # 파일은 File 형식으로 받음
):
    try:
        file_path = file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 에이전트에게 전달할 때는 절대 경로로 변환해서 주는 것이 안전합니다.
        abs_file_path = os.path.abspath(file_path)
        print(f"✅ 파일 저장 완료 (Root): {abs_file_path}")

        # 2. 에이전트에게 보낼 메시지 구성
        # 프롬프트 뒤에 파일 경로를 붙여서 에이전트가 파일을 인지하게 합니다.
        combined_prompt = f"{prompt}\n\n[Attached File Path: {abs_file_path}]"

        # 3. 에이전트 실행
        agent_executor = get_agent_executor()
        
        response = await agent_executor.ainvoke({
            "messages": [HumanMessage(content=combined_prompt)]
        })
        
        final_path = ""
        if "messages" in response:
            final_path = response['messages'][-1].content
        elif "output" in response:
            final_path = response.get("output")
        else:
            raise HTTPException(status_code=500, detail="No output generated")

        return {"response": final_path.strip()}

    except Exception as e:
        print(f"에러 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))