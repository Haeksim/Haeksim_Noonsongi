# 1. Base Image
FROM python:3.11.14-slim

# 2. 시스템 패키지 설치
RUN apt-get update && \
    apt-get install -y ffmpeg libmagic1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. 작업 디렉토리 설정
WORKDIR /app

# 5-1. PyTorch CPU 설치
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 5-2. requirements 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 소스 코드 복사
COPY . .

# 7. 캐시 제거
RUN find . -type d -name "__pycache__" -exec rm -r {} +

# 8. 포트
EXPOSE 8000

# 9. 실행 - 전체 환경 변수 확인
CMD ["sh", "-c", "echo '=== ALL ENV VARS ===' && env && echo '=== STARTING APP ===' && uvicorn api:app --host 0.0.0.0 --port 8000"]