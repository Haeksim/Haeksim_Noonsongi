import requests
import os

test_file_path = "files/test_output.mp4"

# 2. API 엔드포인트 (로컬 실행 기준)
url = "http://127.0.0.1:8000/api/generate"

# 3. 요청 데이터
payload = {
    "prompt": test_file_path
}

print(f"🔵 요청 보내는 중: {test_file_path}")

try:
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print("🟢 성공!")
        print(f"응답 받은 경로: {result['response']}")
        
        # 절대 경로인지 눈으로 확인
        if os.path.isabs(result['response']):
            print("✅ 절대 경로 형식입니다.")
        else:
            print("❌ 절대 경로가 아닙니다 (상대 경로임).")
            
    else:
        print(f"🔴 실패: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"에러 발생: {e}")