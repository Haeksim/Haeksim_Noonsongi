from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent_lang.agent import get_agent_executor
from langchain_core.messages import HumanMessage
import os

app = FastAPI()

print("[DEBUG] CLOUD_URL =", os.getenv("CLOUD_URL"))
print("[DEBUG] COMFY_API_KEY =", os.getenv("COMFY_API_KEY"))
print("[DEBUG] GOOGLE_API_KEY =", os.getenv("GOOGLE_API_KEY"))
print("[DEBUG] MUREKA_API_KEY =", os.getenv("MUREKA_API_KEY"))
print("[DEBUG] MUREKA_API_URL =", os.getenv("MUREKA_API_URL"))


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
async def generate_response(request: ChatRequest):
    try:
        agent_executor = get_agent_executor()
        
        response = await agent_executor.ainvoke({
            "messages": [HumanMessage(content=request.prompt)]
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
        raise HTTPException(status_code=500, detail=str(e))