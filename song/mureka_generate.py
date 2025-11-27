import requests
import time
import os
import subprocess
from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv() 

MUREKA_API_KEY = os.environ.get("MUREKA_API_KEY")
MUREKA_API_URL = os.environ.get("MUREKA_API_URL")

HEADERS = {
    "Authorization": f"Bearer {MUREKA_API_KEY}",
    "Content-Type": "application/json"
}

def get_audio_duration(file_path):
    """
    ffprobe를 사용하여 오디오 파일의 길이를 초(float) 단위로 반환합니다.
    """
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"⚠️ 오디오 길이 측정 실패: {result.stderr}")
            return 999.0 
            
        return float(result.stdout.strip())
    except Exception as e:
        print(f"⚠️ 오디오 길이 측정 중 에러: {e}")
        return 999.0

@tool
def generate_song_via_api(lyrics: str, prompt: str = "kpop, 30 seconds, no interlude, fast tempo") -> str:
    """
    Mureka API를 사용하여 노래를 생성합니다.
    1분(60초)을 초과하면 자동으로 재시도합니다. (최대 3회)
    """
    
    generation_url = f"{MUREKA_API_URL}/v1/song/generate"
    query_url_base = f"{MUREKA_API_URL}/v1/song/query"
    
    constraint_keywords = " MUST UNDER 30 SECONDS, kpop, no instrumental intro, no buildup, NO AD-LIBS, starts immediately, VOCALS START AT 0:00, NO INTERLUDE, EXACT LYRICS ONLY, no solo, no outro, very fast bpm "
    final_prompt = f"{prompt}{constraint_keywords}"

    # --- [재시도 로직 설정] ---
    MAX_RETRIES = 5
    TARGET_DURATION = 70.0 

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🎵 [시도 {attempt}/{MAX_RETRIES}] 노래 생성 시작...")
        
        payload = {
            "lyrics": lyrics,
            "model": "mureka-7.5",
            "prompt": final_prompt
        }
        
        task_id = None
        try:
            response = requests.post(generation_url, headers=HEADERS, json=payload)
            response.raise_for_status() 
            data = response.json()
            task_id = data.get('id')
            if not task_id:
                print(f"❌ ID 수신 실패. 재시도합니다.")
                continue 
            print(f"✅ 작업 ID: {task_id}")
        except Exception as e:
            print(f"❌ 요청 중 에러: {e}")
            continue

        # 2. 폴링 (대기)
        final_mp3_path = None
        print(f"⏳ 생성 대기 중...")
        
        polling_failed = False
        while True:
            try:
                time.sleep(10)
                
                poll_res = requests.get(f"{query_url_base}/{task_id}", headers=HEADERS)
                poll_res.raise_for_status()
                poll_data = poll_res.json()
                status = poll_data.get('status')
                
                print(f"   ... 진행 중 (상태: {status})")
                
                if status == "succeeded":
                    choices = poll_data.get('choices', [])
                    if choices and choices[0].get('url'):
                        mp3_url = choices[0]['url']
                        
                        # 다운로드
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        files_dir = os.path.join(os.path.dirname(current_dir), "files")
                        os.makedirs(files_dir, exist_ok=True)
                        final_mp3_path = os.path.join(files_dir, "song.mp3")
                        
                        audio_res = requests.get(mp3_url)
                        with open(final_mp3_path, 'wb') as f:
                            f.write(audio_res.content)
                        
                        print(f"📂 파일 다운로드 완료.")
                        break 
                    else:
                        print("❌ 결과 URL이 없습니다.")
                        polling_failed = True
                        break
                elif status == "FAILED":
                    print(f"❌ 생성 실패: {poll_data.get('error_message')}")
                    polling_failed = True
                    break
            except Exception as e:
                print(f"⚠️ 폴링 중 에러: {e}")
                polling_failed = True
                break
        
        if polling_failed or not final_mp3_path:
            continue 

        # 3. 길이 검증
        duration = get_audio_duration(final_mp3_path)
        print(f"⏱️ 생성된 길이: {duration:.1f}초")

        if duration <= TARGET_DURATION:
            print(f"🎉 성공! 1분 10초 이내입니다.")
            return final_mp3_path
        else:
            print(f"⚠️ 1분 10초를 초과했습니다. ({duration:.1f}초 > 60초)")
            if attempt < MAX_RETRIES:
                print("♻️ 다시 생성합니다...")
            else:
                print("🛑 최대 재시도 횟수 초과. 마지막 결과물을 사용합니다.")
                return final_mp3_path 

    return "오류: 노래 생성에 계속 실패했습니다."

if __name__ == "__main__":
    test_lyrics = "[Verse 1]\n유네스코 빛나는 유산\n17세기 숨결 담았네\n험준한 산세 품은 성\n조선의 임시 수도였네\n\n[Outro]\n수어장대 우뚝 섰네\n행궁에 담긴 조선\n삼학사의 충절 기억\n자주 독립 염원 담아"
    test_prompt = "kpop"
    
    result = generate_song_via_api(test_lyrics, test_prompt)
    print("\n--- 최종 결과 ---")
    print(result)