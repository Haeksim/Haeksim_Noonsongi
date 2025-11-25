import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv

key = os.getenv("GOOGLE_API_KEY_GEMINI")

from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from pydub import AudioSegment  # <-- 추가됨

load_dotenv()

TOTAL_SEGMENTS = 8
THEME_STYLE = (
    "Cinematic lighting, high fidelity, fluid motion, "
    "consistent character details, masterpiece, 8k resolution, "
    "unreal engine 5 render style, slight volumetric fog"
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=key,
    transport="rest",
)


# -------------------- 유틸 함수 --------------------

def parse_time(time_str: str) -> float:
    """SRT 시간 포맷을 float(seconds)로 변환."""
    time_obj = datetime.strptime(time_str, "%H:%M:%S,%f")
    return (
        time_obj.hour * 3600 +
        time_obj.minute * 60 +
        time_obj.second +
        time_obj.microsecond / 1_000_000
    )


def clean_text(text: str) -> str:
    """HTML 태그(remove <font ...>) 제거."""
    cleaned = re.sub(r'<[^>]+>', '', text)
    return cleaned.strip()


def parse_srt(file_path: str):
    """SRT 파싱 → [{'start': float, 'end': float, 'text': str}, ...]"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"SRT 파일을 찾을 수 없음: {file_path}")

    pattern = re.compile(
        r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)",
        re.DOTALL
    )
    matches = pattern.findall(content)

    subtitles = []
    for _, start, end, text in matches:
        cleaned_text = clean_text(text)
        if cleaned_text:
            subtitles.append({
                "start": parse_time(start),
                "end": parse_time(end),
                "text": cleaned_text
            })

    return subtitles


def get_lyrics_for_segment(subtitles, seg_start, seg_end):
    """특정 시간 구간에 midpoint가 포함되는 자막 모음."""
    segment_texts = []

    for sub in subtitles:
        midpoint = (sub["start"] + sub["end"]) / 2
        if seg_start <= midpoint < seg_end:
            segment_texts.append(sub["text"])

    # 중복 제거 + 순서 유지
    return " ".join(dict.fromkeys(segment_texts))



# -------------------- 메인 툴 --------------------

@tool
def generate_video_prompt_tool(srt_file_path: str) -> list:
    """
    mp3 길이를 기준으로 8분할 → 각 구간에 대응하는 SRT 가사 → LLM 프롬프트 생성
    """

    print(f"SRT 분석 시작: {srt_file_path}")

    # 1) SRT 로드
    try:
        subtitles = parse_srt(srt_file_path)
    except FileNotFoundError as e:
        return [str(e)]

    mp3_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "files", "song.mp3")
    if not os.path.exists(mp3_path):
        return [f"song.mp3 파일을 찾을 수 없습니다: {mp3_path}"]

    audio = AudioSegment.from_mp3(mp3_path)
    total_duration = audio.duration_seconds

    print(f"MP3 총 길이: {total_duration:.2f} 초")

    segment_duration = total_duration / TOTAL_SEGMENTS
    print(f"세그먼트 1개 길이: {segment_duration:.2f} 초")

    results = []

    for i in range(TOTAL_SEGMENTS):
        seg_start = i * segment_duration
        seg_end = (i + 1) * segment_duration
        segment_time = int(round(segment_duration))

        lyrics = get_lyrics_for_segment(subtitles, seg_start, seg_end)
        if not lyrics:
            lyrics = "(Instrumental/Transition)"

        gemini_prompt = f"""
            You are an expert AI Video Prompt Engineer specialized in Image-to-Video (I2V) generation.
            I have a STARTING IMAGE of a character. I need a 'Positive Prompt' to animate this character.

            **Rules:**
            1. DO NOT describe physical appearance (hair, clothes, face).
            2. Focus ONLY on movement, camera angles, atmosphere.
            3. Interpret lyrics metaphorically into expressive actions.
            4. Style: {THEME_STYLE}
            5. Segment duration: {segment_time} seconds.

            **Lyrics for this segment:** "{lyrics}"

            Output a single, comma-separated I2V prompt.
        """

        print(f"[Segment {i+1}/{TOTAL_SEGMENTS}] LLM 프롬프트 생성 중...")

        try:
            response = llm.invoke(gemini_prompt)
            generated_prompt = response.content.strip()
        except Exception as e:
            generated_prompt = f"LLM Error: {str(e)}"

        results.append({
            "segment": i + 1,
            "time": segment_time,
            "lyrics": lyrics,
            "prompt": generated_prompt
        })

    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    files_dir = os.path.join(parent_dir, "files")
    os.makedirs(files_dir, exist_ok=True)

    save_path = os.path.join(files_dir, "video_prompt.json")

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"\n JSON 저장 완료: {save_path}")

    return [item["segment"] for item in results]