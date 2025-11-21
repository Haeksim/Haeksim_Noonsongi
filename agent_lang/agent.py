import os
import re
import magic
from pypdf import PdfReader
from dotenv import load_dotenv

from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

from langchain.agents import create_agent

# from lyric.generate_lyric import generate_lyrics_tool 
# from song.mureka_generate import generate_song_via_api 
# from lyric.generate_lyric import read_lyrics_file_tool
# from srt.whisper_tool import generate_srt_tool
from video_prompt.generate_video_prompt import generate_video_prompt_tool
from video.batch_generate_video import batch_generate_video_tool
from video.generate_video import generate_video_tool
from merge_video.merge_video import merge_video_tool


load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

def get_agent_executor():
    """
    모든 툴들을 사용하는 에이전트를 생성하고 반환합니다.
    """
    # agent가 사용할 tools
    tools = [
        # generate_lyrics_tool, 
        # generate_song_via_api,
        # read_lyrics_file_tool, 
        # generate_srt_tool,
        generate_video_prompt_tool,
        batch_generate_video_tool,
        generate_video_tool,
        merge_video_tool
    ]
    
    # system_message prompt
    system_message_string = (
        "You are a music video producer. "
        # "1. Generate lyrics first. "
        # "2. Generate a song using the lyrics. "
        # "3. Create an .srt file using generate_srt_tool. "
        "Generate video prompts using generate_video_prompt_tool based on the srt file. "
        "Generate a video using batch_generate_video_tool."
        "merge videos using merge_video_tool."
    )
    
    # creating agent
    agent = create_agent(model=llm, tools=tools, system_prompt=system_message_string)
    
    return agent