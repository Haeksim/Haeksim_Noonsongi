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
        ("system", "You are a professional lyricist. All responses must be in Korean. "
                   "**절대로 다음 형식 규칙을 어겨서는 안 됩니다.**"), # 시스템 프롬프트 강화
        ("user", "'{topic_content}'라는 주제로 1분 길이의 노래 가사를 생성해주세요. "
                 "**[Verse 1]과 [Outro] 두 파트만**으로, 각각 **단 한 번씩** 구성해야 합니다. "
                 "**다른 파트([Verse 2], [Chorus], [Bridge] 등)는 절대 포함하지 마세요.**\n\n"
                 "--- 형식 규칙 (필수 준수 사항) ---\n"
                 "1. **문장 길이 제한:** 각 문장의 길이는 **최대 25자**를 넘을 수 없습니다.\n"
                 "2. **파트당 라인 수 제한:** [Verse 1]은 **최대 4줄**, [Outro]는 **최대 4줄**로 구성합니다.\n" # 라인 수 제한 추가
                 "3. **시작 형식:** 결과물은 **노래 제목이나 다른 텍스트 없이 바로 [Verse 1]으로 시작**해야 합니다.\n"
                 "4. **스타일:** {style} 스타일로 작성해주세요.\n"
                 "-------------------------------\n\n"
                 "**규칙을 어기면 안 됩니다. 문장 길이와 파트 구성을 엄격히 지키세요.**") # 최종 경고 추가
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
    
# test code!!! 
# (기존 코드의 맨 끝에 추가)

# --- 2. 테스트 환경 설정 ---
# NOTE: 이 스크립트가 실행될 때, 'files/test_topic.pdf' 경로에 실제 PDF 파일이 존재해야 합니다.
def setup_test_environment():
    """테스트를 위한 'files' 폴더를 생성합니다."""
    # 현재 스크립트의 디렉토리를 기준으로 'files' 폴더를 찾거나 생성
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) # 스크립트가 포함된 폴더의 부모 폴더를 프로젝트 루트로 가정
    files_dir = os.path.join(project_root, "files")
    
    # files_dir 생성
    os.makedirs(files_dir, exist_ok=True)
    
    # 가상의 PDF 파일 경로 (실제 파일을 여기에 넣어주세요)
    test_pdf_path = os.path.join(files_dir, "test_topic.pdf")
    
    # 환경 변수 로드 확인
    if not os.getenv("GOOGLE_API_KEY_GEMINI"):
        print("🚨 경고: GOOGLE_API_KEY_GEMINI 환경 변수가 설정되지 않았습니다.")
        print("API 키를 .env 파일에 설정하거나 직접 할당해야 합니다.")
    
    return test_pdf_path

# --- 3. 메인 테스트 함수 ---
def main_test():
    # 1. 테스트 환경 설정 및 PDF 파일 경로 획득
    pdf_filepath = setup_test_environment()
    
    print("\n=============================================")
    print(f"** 테스트 시작 (PDF 파일 경로: {pdf_filepath}) **")
    
    if not os.path.exists(pdf_filepath):
        print("❌ 테스트 실패: 지정된 경로에 PDF 파일이 없습니다.")
        print(f"   테스트를 위해 '{pdf_filepath}' 경로에 PDF 파일을 넣어주세요.")
        return
        
    # 2. generate_lyrics_tool 호출
    topic_style = "k-pop"
    
    print(f"\n🔍 툴 호출: generate_lyrics_tool(주제: PDF 파일, 스타일: {topic_style})")
    
    # PDF 파일 경로를 인자로 전달
    result_filepath = generate_lyrics_tool(
        topic_or_filepath=pdf_filepath, 
        style=topic_style
    )
    
    print("\n=============================================")
    print(f"** 가사 생성 결과 (반환 경로): {result_filepath} **")
    print("=============================================")
    
    # 3. 결과 파일 내용 확인 (선택 사항)
    if not "실패:" in result_filepath and os.path.exists(result_filepath):
        print("✅ 가사 파일 내용 확인:")
        lyrics = read_lyrics_file_tool(result_filepath)
        print("---------------------------------")
        print(lyrics)
        print("---------------------------------")
        
    elif "오류:" in result_filepath:
        print(f"❌ 툴 실행 중 오류 발생: {result_filepath}")
        
    else:
        print("❌ 툴 실행 실패 또는 가사 파일 경로가 유효하지 않음.")

# 스크립트가 직접 실행될 때만 main_test 함수 호출
if __name__ == "__main__":
    main_test()