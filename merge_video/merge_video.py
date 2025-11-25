import os
import re
import subprocess
from langchain_core.tools import tool


INPUT_DIR = "files/generated_videos"
OUTPUT_DIR = "files"
SONG_MP3 = "files/song.mp3"
SONG_SRT = "files/song.srt"

FILENAME_PREFIX = "ByteDance-Seedance_"
FILE_PATTERN = r"ByteDance-Seedance_(\d+)_\.mp4"


def _run_ffmpeg(cmd: list):
    """ffmpeg 명령을 실행하고, 실패 시 예외 발생"""
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise Exception(f"FFmpeg error: {process.stderr}")
    return process.stdout


def _get_ordered_video_list():
    """generated_videos 안에서 번호순으로 mp4 경로 반환"""
    files = os.listdir(INPUT_DIR)
    matched = []

    for f in files:
        m = re.match(FILE_PATTERN, f)
        if m:
            num = int(m.group(1))
            matched.append((num, os.path.join(INPUT_DIR, f)))

    if not matched:
        raise Exception("generated_videos 폴더에서 대상 mp4 파일을 찾을 수 없습니다.")

    matched.sort(key=lambda x: x[0])
    return [path for _, path in matched]


@tool
def merge_video_tool(dummy: str = "start") -> str:
    """
    generated_video 폴더의 ByteDance-Seedance_00003_.mp4 형식 파일들을
    번호 순대로 병합하고, song.srt 자막 + song.mp3 배경음악을 적용해 최종 mp4 생성.
    """

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    video_list = _get_ordered_video_list()

    concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")

    merged_video_path = os.path.join(OUTPUT_DIR, "merged_temp.mp4")
    final_output_path = os.path.join("output.mp4")

    # 1) concat videos
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        merged_video_path
    ]
    print("[*] Merging videos…")
    _run_ffmpeg(concat_cmd)

    # 2) subtitles + audio
    filter_sub = f"subtitles='{os.path.abspath(SONG_SRT)}':force_style='Alignment=2,FontSize=12'"

    final_cmd = [
        "ffmpeg", "-y",
        "-i", merged_video_path,
        "-i", SONG_MP3,
        "-vf", filter_sub,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        final_output_path
    ]

    print("[*] Adding music + subtitles…")
    _run_ffmpeg(final_cmd)
    

    return final_output_path