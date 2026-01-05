import os
import google.generativeai as genai
import time
from fastapi import UploadFile

# Configure Gemini
# Enusre GEMINI_API_KEY is set in environment
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model_name = "gemini-2.5-pro"

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def wait_for_files_active(files):
    """Waits for the given files to be active."""
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    print("...all files ready")

import asyncio
from .sop_aggregator import merge_partial_sops

async def generate_sop_for_chunk(chunk_path: str, chunk_index: int, total_chunks: int, prompt: str, context_files: list = [], context_str: str = ""):
    """Processes a single video chunk with additional context files."""
    print(f"Processing chunk {chunk_index + 1}/{total_chunks}: {chunk_path}")
    
    # Upload
    video_file = upload_to_gemini(chunk_path, mime_type="video/mp4")
    
    # Wait
    wait_for_files_active([video_file])
    
    # Generate
    chunk_prompt = f"""
    {prompt}
    
    IMPORTANT: This is PART {chunk_index + 1} of {total_chunks} of the video. 
    Focus on extracting the steps shown IN THIS VIDEO SEGMENT.
    
    You have additionally been provided with {len(context_files)} context files (PDFs/Images).
    Use these context files to verify details (e.g. Rate Cards, Invoices) seen in the video.
    Do not hallucinate steps from outside this video segment.

    USER PROVIDED CONTEXT FOR ATTACHMENTS:
    {context_str}
    """
    
    # Construct Multimodal Request: [Video, *ContextFiles, Prompt]
    request_content = [video_file] + context_files + [chunk_prompt]
    
    model = genai.GenerativeModel(model_name=model_name)
    response = await model.generate_content_async(request_content)
    
    print(f"Chunk {chunk_index + 1} complete.")
    
    # Cleanup chunk video from Gemini to save space (Context files remain for other chunks)
    try:
        genai.delete_file(video_file.name)
    except:
        pass
        
    return response.text

async def analyze_video_chunks(chunk_paths: list[str], prompt: str, context_files: list = [], context_str: str = ""):
    """Uploads and processes multiple video chunks in parallel (with context), then merges them."""
    
    tasks = []
    for i, path in enumerate(chunk_paths):
        tasks.append(generate_sop_for_chunk(path, i, len(chunk_paths), prompt, context_files, context_str))
    
    # Run all chunks in parallel
    partial_sops = await asyncio.gather(*tasks)
    
    print("All chunks processed. Merging...")
    
    # Merge
    final_sop = await merge_partial_sops(partial_sops, model_name, context_str)
    
    return final_sop

