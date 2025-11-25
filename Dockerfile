# 1. Base Image
FROM python:3.11.14-slim

# 2. 시스템 패키지 설치
# apt 캐시 삭제로 용량 절약
RUN apt-get update && \
    apt-get install -y ffmpeg libmagic1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4-1. PyTorch CPU 버전 먼저 설치
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# 4-2. 나머지 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 복사
COPY . .

# 6. 불필요한 파일 정리
RUN find . -type d -name "__pycache__" -exec rm -r {} +

# 7. 포트 노출
EXPOSE 8000

# 8. 실행 명령어
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]