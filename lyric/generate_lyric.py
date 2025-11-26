import os
import re
import magic
from pypdf import PdfReader
from dotenv import load_dotenv


key = os.getenv("GOOGLE_API_KEY_GEMINI")

from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

load_dotenv()
# key = os.getenv("GOOGLE_API_KEY_GEMINI") # 로컬 테스트용 
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=key,
    transport="rest",
)


def check_input_type_with_magic(input_path):
    """입력 경로가 PDF, TEXT 파일인지, 아니면 그냥 텍스트인지 확인합니다."""
    if os.path.exists(input_path) and (input_path.endswith('.pdf') or '.' not in input_path):
      try:
          mime_type = magic.Magic(mime=True).from_file(input_path)
          if mime_type == 'application/pdf':
              return "PDF_FILE"
          elif mime_type.startswith('text/'):
             return "TEXT_FILE"
          else:
             return f"OTHER_FILE ({mime_type})"
      except Exception as e:
         if input_path.endswith('.pdf'):
             print(f"Warning: magic 라이브러리 확인 실패 ({e}). PDF로 간주합니다.")
             return "PDF_FILE"
         else:
             print(f"Error checking file with magic: {e}")
             return "UNKNOWN"
    else:
      return "TEXT_INPUT"

def load_topic_content(topic_or_filepath: str) -> str:
    """사용자 입력을 받아 파일(PDF/TXT)을 읽거나 텍스트 자체를 반환합니다."""
    input_type = check_input_type_with_magic(topic_or_filepath)
    content = ""

    if (input_type == 'PDF_FILE'):
        print(f"[{topic_or_filepath}] PDF 파일에서 텍스트를 추출합니다...")
        try:
            reader = PdfReader(topic_or_filepath)
            for page in reader.pages:
                content += page.extract_text()
        except Exception as e:
            print(f"Error reading PDF {topic_or_filepath}: {e}")
            return f"PDF 읽기 오류: {e}"
            
    elif (input_type == 'TEXT_FILE'):
        print(f"[{topic_or_filepath}] 텍스트 파일에서 텍스트를 읽어옵니다...")
        try:
            with open(topic_or_filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading text file {topic_or_filepath}: {e}")
            return f"텍스트 파일 읽기 오류: {e}"
            
    else:
        print(f"[{topic_or_filepath[:30]}...] 텍스트를 주제로 사용합니다.")
        content = topic_or_filepath
    
    if not content.strip():
        return "오류: 유효한 주제 텍스트가 없습니다."
        
    return content

def clean_lyrics_output(generated_text: str) -> str:
    """Gemini 응답에서 불필요한 '---'나 대화형 인트로를 제거합니다."""
    cleaned_lyrics = generated_text
    parts = generated_text.split('---')

    if len(parts) > 2: 
        cleaned_lyrics = parts[1].strip()
    elif len(parts) == 2: 
        cleaned_lyrics = parts[1].strip()
    else:
        lines = generated_text.splitlines()
        if lines and ("라는 주제로" in lines[0] or "작성해 드릴게요" in lines[0]):
            if len(lines) > 1 and not lines[1].strip():
                 cleaned_lyrics = "\n".join(lines[2:]).strip()
            else:
                 cleaned_lyrics = "\n".join(lines[1:]).strip()
        else:
            cleaned_lyrics = generated_text.strip()
    return cleaned_lyrics


@tool
def generate_lyrics_tool(topic_or_filepath: str, style: str="kpop") -> str:
    """
    (LLM이 읽는 설명서)
    주제(텍스트 또는 파일 경로)와 스타일을 입력받아 노래 가사를 생성합니다.
    가사를 'lyrics.txt' 파일로 저장하고, 가사 파일의 경로('lyrics.txt')를 반환합니다.
    """
    print(f"\n--- 🛠️ '가사 생성 및 저장' 툴 호출됨 ---")
    
    topic_content = load_topic_content(topic_or_filepath)
    if "오류:" in topic_content:
        return topic_content

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a professional lyricist. All responses must be in Korean."),
        ("user", "'{topic_content}'라는 주제로 1분 길이의 노래 가사를 생성해주세요. "
                 "가사 구조는 반드시 [Verse 1], [Chorus], [Outro] 이 세 파트**만**으로, 각각 **단 한 번씩** 구성되어야 합니다."
                 "[Verse 2], 두 번째 [Chorus], [Bridge], [Pre-Chorus] 등 다른 파트나 반복되는 파트는 절대 추가하지 마세요."
                 "**결과물 맨 위에 노래 제목이나 '##' 같은 헤더를 절대 포함하지 마세요. 바로 [Verse 1]으로 시작하세요.** "
                 "**와 같은 bold체는 제외해주세요. {style}")
    ])
    output_parser = StrOutputParser() | clean_lyrics_output
    lyric_chain = prompt | llm | output_parser

    print("AI가 노래 가사를 생성 중입니다...")
    try:
        cleaned_lyrics = lyric_chain.invoke({
            "topic_content": topic_content,
            "style": style
        })
        
        print("--- 생성된 노래 가사 ---")
        print(cleaned_lyrics)
        print("---------------------")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        files_dir = os.path.join(project_root, "files")
        os.makedirs(files_dir, exist_ok=True)
        output_filename = os.path.join(files_dir, "lyrics.txt")
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(cleaned_lyrics)
            
        print(f"가사가 '{output_filename}' 파일로 저장되었습니다.")
        return output_filename 

    except Exception as e:
        print(f"가사 생성 중 오류 발생: {e}")
        return f"실패: 가사 생성 중 오류가 발생했습니다. {e}"
    
@tool
def read_lyrics_file_tool(filepath: str) -> str:
    """
    (LLM이 읽는 설명서)
    'lyrics.txt'와 같이 가사가 저장된 텍스트 파일의 경로(filepath)를 입력받아
    파일 안의 내용(가사 텍스트)을 문자열로 반환합니다.
    이 툴은 'generate_lyrics_tool'이 성공한 직후에 사용해야 합니다.
    """
    print(f"\n--- 🛠️ '가사 파일 읽기' 툴 호출됨 ---")
    
    if not os.path.exists(filepath):
        print(f"오류: '{filepath}' 파일을 찾을 수 없습니다.")
        return f"오류: '{filepath}' 파일을 찾을 수 없습니다."
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lyrics_content = f.read()
        print(f"'{filepath}' 파일 읽기 성공.")
        
        if not lyrics_content.strip():
             print("오류: 파일 내용은 있으나, 빈 문자열입니다.")
             return "오류: 파일 내용은 있으나, 빈 문자열입니다."
             
        return lyrics_content
        
    except Exception as e:
        print(f"오류: '{filepath}' 파일 읽기 실패. {e}")
        return f"오류: '{filepath}' 파일 읽기 실패. {e}"