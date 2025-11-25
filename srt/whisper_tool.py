import os
import warnings 


os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # TensorFlow 로그 억제
os.environ["GRPC_VERBOSITY"] = "ERROR"    # gRPC 로그 억제
os.environ["GRPC_TRACE"] = ""             # gRPC 트레이스 끄기
warnings.filterwarnings("ignore")         # 파이썬 경고 무시


import stable_whisper
from langchain.tools import tool

print("⏳ Whisper 모델 로딩 중... (최초 1회)")
try:
    model = stable_whisper.load_model("small")
    print("✅ Whisper 모델 로드 완료.")
except Exception as e:
    print(f"⚠️ 모델 로드 실패: {e}")
    model = None

@tool
def generate_srt_tool(audio_file_path: str, lyrics_file_path: str) -> str:
    """
    (LLM 설명서)
    노래 오디오 파일(.mp3)의 경로와 가사 텍스트 파일(.txt)의 경로를 입력받아,
    Whisper AI를 사용하여 싱크가 맞는 자막 파일(.srt)을 생성합니다.
    생성된 SRT 파일의 경로를 반환합니다.
    """
    print(f"\n--- 🛠️ 'SRT 자막 생성' 툴 호출됨 ---")
    
    if model is None:
        return "오류: Whisper 모델이 로드되지 않았습니다. stable-ts 패키지 설치를 확인하세요."

    if not os.path.exists(audio_file_path):
        return f"오류: 오디오 파일 '{audio_file_path}'을 찾을 수 없습니다."
    if not os.path.exists(lyrics_file_path):
        return f"오류: 가사 파일 '{lyrics_file_path}'을 찾을 수 없습니다."

    # 2. 가사 읽기
    try:
        with open(lyrics_file_path, 'r', encoding='utf-8') as f:
            lyrics_text = f.read()
    except Exception as e:
        return f"오류: 가사 파일 읽기 실패. {e}"

    # 출력 파일명 설정 (song.mp3 -> song.srt)
    output_srt_path = os.path.splitext(audio_file_path)[0] + ".srt"

    # 3. 강제 정렬 (Alignment) 실행
    print(f"🎵 '{audio_file_path}' 오디오와 가사를 매칭 중...")
    try:
        # align() 함수가 핵심입니다.
        result = model.align(audio_file_path, lyrics_text, language='ko')
        
        # SRT 저장
        result.to_srt_vtt(output_srt_path)
        print(f"✅ SRT 생성 완료: {output_srt_path}")
        
        return output_srt_path

    except Exception as e:
        print(f"SRT 생성 중 오류 발생: {e}")
        return f"실패: SRT 생성 중 오류가 발생했습니다. {e}"