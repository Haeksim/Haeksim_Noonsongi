# 1. Base Image: Python 3.11.14 slim 버전
FROM python:3.11.14-slim

# 2. 시스템 패키지 설치 (FFmpeg 필수)
# apt-get update 후 ffmpeg를 설치하고, 이미지 크기를 줄이기 위해 캐시 삭제
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 설치
# requirements.txt를 먼저 복사해서 캐시를 활용 (빌드 속도 향상)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 복사
COPY . .

# 6. 포트 노출 (정보 제공용)
EXPOSE 8000

# 7. 실행 명령어
# --host 0.0.0.0: 컨테이너 외부에서 접속 가능하게 함 (필수)
# --reload: 코드 변경 시 자동 재시작
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]