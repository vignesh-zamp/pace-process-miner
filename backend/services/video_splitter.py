import os
import subprocess
import math

CHUNK_DURATION = 1200  # 20 minutes in seconds

def get_video_duration(video_path: str) -> float:
    """Returns the duration of the video in seconds."""
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise Exception(f"Could not determine video duration. Error: {result.stderr}")

def split_video(video_path: str, output_dir: str) -> list[str]:
    """Splits video into 20-minute chunks and returns list of file paths."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    duration = get_video_duration(video_path)
    file_name = os.path.basename(video_path)
    base_name, ext = os.path.splitext(file_name)
    
    chunks = []
    
    # If video is shorter than chunk limit, return original
    if duration <= CHUNK_DURATION:
        return [video_path]

    num_chunks = math.ceil(duration / CHUNK_DURATION)
    
    print(f"Video duration: {duration}s. Splitting into {num_chunks} chunks...")

    for i in range(num_chunks):
        start_time = i * CHUNK_DURATION
        chunk_path = os.path.join(output_dir, f"{base_name}_part{i+1}{ext}")
        
        # ffmpeg command to slice
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", str(start_time),
            "-t", str(CHUNK_DURATION),
            "-c", "copy",  # Fast copy without re-encoding
            "-y",          # Overwrite output
            chunk_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        chunks.append(chunk_path)
        print(f"Created chunk: {chunk_path}")

    return chunks
