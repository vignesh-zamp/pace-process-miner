import os
import shutil
import time
import mimetypes
from typing import List
import google.generativeai as genai
from fastapi import UploadFile

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    if not mime_type:
        mime_type = get_mime_type(path)
        
    print(f"Uploading {path} ({mime_type}) to Gemini...")
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

async def process_and_upload_files(files: List[UploadFile], upload_dir: str):
    """
    Saves UploadFiles to disk, uploads them to Gemini, and returns the Gemini File objects.
    """
    gemini_files = []
    
    for file in files:
        # Save to disk first
        file_location = os.path.join(upload_dir, file.filename)
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
        
        # Determine MIME type (or let Gemini guess, but explicit is better)
        mime_type = file.content_type
        if not mime_type:
            mime_type = get_mime_type(file.filename)
            
        # Upload to Gemini
        g_file = upload_to_gemini(file_location, mime_type=mime_type)
        gemini_files.append(g_file)
        
    # Wait for all to be ready
    wait_for_files_active(gemini_files)
    
    return gemini_files
