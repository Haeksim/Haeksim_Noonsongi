import os
from dotenv import load_dotenv

key = os.getenv("GOOGLE_API_KEY_GEMINI")

from langchain_google_genai import ChatGoogleGenerativeAI

from langchain.agents import create_agent

from lyric.generate_lyric import generate_lyrics_tool 
from song.mureka_generate import generate_song_via_api 
from lyric.generate_lyric import read_lyrics_file_tool
from srt.whisper_tool import generate_srt_tool

from video_prompt.generate_video_prompt import generate_video_prompt_tool
from video.batch_generate_video import batch_generate_video_tool
from video.generate_video import generate_video_tool
from merge_video.merge_video import merge_video_tool


load_dotenv()
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=key,
    transport="rest",
)

def get_agent_executor():
    # agent가 사용할 tools
    tools = [
            generate_lyrics_tool, 
            generate_song_via_api,
            read_lyrics_file_tool, 
            generate_srt_tool,
            generate_video_prompt_tool,
            batch_generate_video_tool,
            generate_video_tool,
            merge_video_tool
        ]
    
    # system_message prompt
    system_message_string = """
    You are a music producer. You must use tools to generate lyrics first, then generate a song. 
    And then, you must make .srt file using generate_srt_tool.
    Generate a video using batch_generate_video_tool.
    merge videos using merge_video_tool.
    
    [IMPORTANT]
    When the final video is created, your final answer MUST be ONLY the file path returned by the merge_video_tool. 
    Do not add any other text or explanation.
    """
    
    # creating agent
    agent = create_agent(model=llm, tools=tools, system_prompt=system_message_string)
    
    return agent

# def get_agent_executor():
#     # 1. 툴은 잠시 비워둡니다 (실수로 실행되는 것 방지)
#     tools = [] 
    
#     # 2. 시스템 프롬프트를 "입력받은 경로를 절대 경로로 바꿔서 뱉어라"로 변경합니다.
#     system_message_string = """
#     You are a file path converter.
#     The user will give you a file path.
#     You must return ONLY the input file path as your final answer.
#     Do not add any other text.
#     """
    
#     agent = create_agent(model=llm, tools=tools, system_prompt=system_message_string)
#     return agent