import json
import os
import shutil
from typing import List
from langchain_core.tools import tool
from concurrent.futures import ThreadPoolExecutor, as_completed

from video.generate_video import generate_video_tool as gen_tool

CONCURRENCY_LIMIT = 4

GENERATED_VIDEO_DIR = "files/generated_videos"


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


@tool
def batch_generate_video_tool(indexes: List[int]) -> None:
    """
    LangGraph가 어떤 index 리스트를 주든 무시하고
    무조건 index 1~8만 실행한다.
    실행 시작할 때 files/generated_video 폴더를 비운다.
    """

    _clear_generated_video_dir()

    real_indexes = [1, 2, 3, 4, 5, 6, 7, 8]

    for batch in chunk_list(real_indexes, CONCURRENCY_LIMIT):
        with ThreadPoolExecutor(max_workers=CONCURRENCY_LIMIT) as exe:
            futures = [exe.submit(call_generate_video, idx) for idx in batch]
            for fut in as_completed(futures):
                _ = fut.result()
