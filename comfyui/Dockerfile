FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# ComfyUI 공식 레포지토리 클론
RUN git clone https://github.com/comfyanonymous/ComfyUI.git

# ComfyUI 의존성 설치
WORKDIR /app/ComfyUI
RUN pip install --no-cache-dir -r requirements.txt

# 커스텀 노드 설치 스크립트 복사 및 실행
COPY install_nodes.sh /app/install_nodes.sh
RUN chmod +x /app/install_nodes.sh && /app/install_nodes.sh

# Railway 포트를 사용하여 CPU 모드로 실행
CMD python main.py --listen 0.0.0.0 --port $PORT --cpu