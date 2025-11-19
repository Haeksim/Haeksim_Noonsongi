import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain.agents import create_agent

from lyric.generate_lyric import generate_lyrics_tool 
from song.mureka_generate import generate_song_via_api 
from lyric.generate_lyric import read_lyrics_file_tool
from srt.whisper_tool import generate_srt_tool

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

def get_agent_executor():
    """
    3개의 툴들을 사용하는 에이전트를 생성하고 반환합니다.
    """
    # agent가 사용할 tools
    tools = [generate_lyrics_tool, generate_song_via_api,read_lyrics_file_tool, generate_srt_tool]
    
    # system_message prompt
    system_message_string = "You are a music producer. You must use tools to generate lyrics first, then generate a song. And then, you must make .srt file using generate_srt_tool"
    
    # creating agent
    agent = create_agent(model=llm, tools=tools, system_prompt=system_message_string)
    
    return agent