import json
import os
import shutil
import time
from typing import List
from langchain_core.tools import tool
from concurrent.futures import ThreadPoolExecutor, as_completed

from video.generate_video import generate_video_tool as gen_tool

CONCURRENCY_LIMIT = 4
GENERATED_VIDEO_DIR = "files/generated_videos"
POLLING_TIMEOUT = 600  # 최대 대기 시간 (초) - 10분
POLLING_INTERVAL = 5   # 확인 간격 (초)

def _clear_generated_video_dir():
    """files/generated_video 폴더를 완전히 비우는 함수"""
    if os.path.exists(GENERATED_VIDEO_DIR):
        shutil.rmtree(GENERATED_VIDEO_DIR)
    os.makedirs(GENERATED_VIDEO_DIR, exist_ok=True)


def call_generate_video(index: int):
    """generate_video_tool 내부 실제 동기함수 호출"""
    func = getattr(gen_tool, "func", None)
    if callable(func):
        return func(index)

    if callable(getattr(gen_tool, "run", None)):
        return gen_tool.run(index)

    if callable(getattr(gen_tool, "invoke", None)):
        return gen_tool.invoke(index)

    raise RuntimeError("generate_video_tool을 호출할 수 없습니다.")


def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def _wait_for_files(target_count: int):
    """
    목표 파일 개수(target_count)만큼 파일이 생성될 때까지 대기하는 함수
    """
    start_time = time.time()
    print(f"[*] 파일 생성 대기 시작... (목표: {target_count}개)")

    while True:
        # 현재 디렉토리의 .mp4 파일 개수 확인
        if os.path.exists(GENERATED_VIDEO_DIR):
            files = [f for f in os.listdir(GENERATED_VIDEO_DIR) if f.endswith(".mp4")]
            current_count = len(files)
        else:
            current_count = 0

        # 목표 개수에 도달하면 대기 종료
        if current_count >= target_count:
            print(f"[*] 배치 작업 완료 확인: 현재 {current_count}개의 파일이 존재합니다.")
            break

        # 타임아웃 체크
        if time.time() - start_time > POLLING_TIMEOUT:
            raise TimeoutError(f"비디오 생성 대기 시간 초과 ({POLLING_TIMEOUT}초). 현재 파일 수: {current_count}")

        print(f"   ...파일 생성 기다리는 중 ({current_count}/{target_count})")
        time.sleep(POLLING_INTERVAL)


@tool
def batch_generate_video_tool(indexes: List[int]) -> None:
    """
    LangGraph가 어떤 index 리스트를 주든 무시하고
    무조건 index 1~8만 실행한다.
    실행 시작할 때 files/generated_video 폴더를 비운다.
    4개씩 끊어서 실행하며, 파일 생성을 확인한 후 다음 배치로 넘어간다.
    """

    _clear_generated_video_dir()

    real_indexes = [1, 2, 3, 4, 5, 6, 7, 8]
    accumulated_target_count = 0  # 누적 목표 파일 개수

    print(f"[*] 총 {len(real_indexes)}개의 작업을 {CONCURRENCY_LIMIT}개씩 나누어 실행합니다.")

    # chunk_list로 4개씩 잘라서 반복
    for batch_idx, batch in enumerate(chunk_list(real_indexes, CONCURRENCY_LIMIT)):
        print(f"\n=== [Batch {batch_idx + 1}] 시작: 인덱스 {batch} ===")
        
        # 1. 4개 작업 병렬 요청 (Request)
        with ThreadPoolExecutor(max_workers=CONCURRENCY_LIMIT) as exe:
            futures = [exe.submit(call_generate_video, idx) for idx in batch]
            for fut in as_completed(futures):
                try:
                    _ = fut.result() # 요청 자체의 성공 여부 확인
                except Exception as e:
                    print(f"[Error] 인덱스 요청 중 에러 발생: {e}")

        # 2. 이번 배치의 파일들이 생성될 때까지 대기 (Polling)
        # 예: 첫 번째 배치면 4개, 두 번째 배치면 8개가 될 때까지 기다림
        accumulated_target_count += len(batch)
        _wait_for_files(accumulated_target_count)

    print("\n[*] 모든 배치 작업 및 파일 생성이 완료되었습니다.")