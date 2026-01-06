import os
import time
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
import google.generativeai as genai
from dotenv import load_dotenv
from services.context_manager import process_sop_context

load_dotenv()

app = FastAPI(title="Process Miner AI")

# CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"status": "active", "service": "Process Miner AI"}

from services.storage_service import list_all_documents, read_document, load_latest_sop, save_next_version

# ... existing code ...

@app.get("/documents")
async def get_history():
    """Returns the list of all generated SOPs."""
    return {"documents": list_all_documents()}

@app.get("/document")
async def get_document(path: str):
    """Returns the content of a specific SOP."""
    content = read_document(path)
    if not content:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"content": content}

from typing import List
from services.multimodal_service import process_and_upload_files, upload_to_gemini, wait_for_files_active, get_mime_type
from services.sop_generator import SOP_MULTIMODAL_PROMPT
from services.video_splitter import split_video
from services.ai_service import analyze_video_chunks
from services.sop_aggregator import merge_partial_sops

@app.post("/analyze")
async def analyze_multimodal(files: List[UploadFile] = File(...), file_contexts: str = Form(default="{}"), session_id: str = Form(None)):
    start_time = time.time()
    try:
        print(f"Received {len(files)} files for analysis. Hybrid Mode.")
        
        # Parse context mapping
        try:
            context_mapping = json.loads(file_contexts)
        except json.JSONDecodeError:
            context_mapping = {}
        
        # 1. Classification
        long_videos_local_paths = []
        context_files_local_paths = []
        
        # We need to save them all to disk first to check/split
        for file in files:
            file_location = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
            
            # Simple check: Is it MP4?
            mime = file.content_type or get_mime_type(file.filename)
            
            # For simplicity: If Video > 200MB or explicitly treated as 'main video', we split.
            # But here user said "20 min batches". We should use split_video to check duration.
            # Let's treat ALL videos as "Main" for now, or just picking the longest one?
            # User's request: "If any videos are attached... flow is 20 min batches"
            if "video" in mime:
                long_videos_local_paths.append(file_location)
            else:
                context_files_local_paths.append(file_location)
                
        # 2. Upload Context Files (PDFs, Images, Audio) to Gemini
        gemini_context_files = []
        for path in context_files_local_paths:
             g_file = upload_to_gemini(path)
             gemini_context_files.append(g_file)
             
        wait_for_files_active(gemini_context_files)
        
        raw_sop = ""

        # Prepare Context String for AI
        context_description_lines = []
        for filename, context in context_mapping.items():
            if context and context.strip():
                 context_description_lines.append(f"- File '{filename}': {context}")
        
        context_description = "\n".join(context_description_lines)

        # 3. Process Videos (Parallel Orchestrator Flow)
        video_sops = []
        if long_videos_local_paths:
            print(f"Orchestrator: Found {len(long_videos_local_paths)} video(s). Processing in PARALLEL...")
            
            # Helper function for single video flow
            async def process_single_video_flow(path, index, total, context_str=""):
                try:
                        print(f"Processing chunk {index+1}/{total}...")
                        g_vid = upload_to_gemini(path)
                        wait_for_files_active([g_vid])
                        
                        model = genai.GenerativeModel(model_name="gemini-2.5-pro")
                        prompt = SOP_MULTIMODAL_PROMPT
                        if context_str:
                             prompt += f"\n\nUSER PROVIDED CONTEXT:\n{context_str}"
                             
                        response = await model.generate_content_async([prompt, g_vid])
                        text = response.text
                        
                        # Cleanup
                        try:
                             genai.delete_file(g_vid.name)
                        except:
                             pass
                        return text
                        
                except Exception as e:
                    print(f"❌ ERROR processing video {os.path.basename(path)}: {e}")
                    return None # Return None to signal failure but keep going

            # Create tasks for all videos
            tasks = [
                process_single_video_flow(path, idx, len(long_videos_local_paths))
                for idx, path in enumerate(long_videos_local_paths)
            ]
            
            # Execute in parallel
            results = await asyncio.gather(*tasks)
            
            # Filter out failures (None)
            video_sops = [res for res in results if res is not None]
            
            print(f"\nOrchestrator: {len(video_sops)}/{len(long_videos_local_paths)} videos processed successfully.")

            # If multiple successful videos, perform Master Merge
            if len(video_sops) > 1:
                print(f"\n--- Master Merge: Consolidating {len(video_sops)} Video SOPs ---")
                from services.sop_aggregator import merge_partial_sops
                raw_sop = merge_partial_sops(video_sops)
            elif video_sops:
                raw_sop = video_sops[0]
            else:
                raw_sop = "No videos were successfully processed. Check server logs."
                
        else:
             # No Video, just Documents?
             print("No Video found. Document-only analysis.")
             model = genai.GenerativeModel(model_name="gemini-2.5-pro")
             
             # Inject context into prompt if exists
             prompt_with_context = SOP_MULTIMODAL_PROMPT
             if context_description:
                 prompt_with_context += f"\n\nUSER PROVIDED CONTEXT FOR ATTACHMENTS:\n{context_description}\n"
                 prompt_with_context += "\nINSTRUCTION: Please add a final section '## Context Acknowledgement' explaining how this context was utilized."

             request_content = [prompt_with_context] + gemini_context_files
             response = await model.generate_content_async(request_content)
             raw_sop = response.text

        # 4. Context Processing / Saving
        # Calculate time
        end_time = time.time()
        duration = round(end_time - start_time, 2)

        # EXTENSION LOGIC: If session_id is present, handle iterative update
        if session_id:
            print(f"Extension Mode: Handling Session {session_id}")
            # 1. Try to load previous SOP
            prev_sop = load_latest_sop("Shadow_Sessions", f"Session_{session_id}")
            
            final_result = raw_sop
            
            if prev_sop:
                print("Found previous SOP version. Merging...")
                # Merge Previous + New
                merged_sop = await merge_partial_sops([prev_sop, raw_sop], model_name="gemini-2.5-pro", context_str=context_description)
                final_result = merged_sop
            else:
                print("No previous SOP found. Starting new session.")
                final_result = raw_sop # First chunk

            # 2. Save new version (Shadow_Sessions/Session_X_vN.md)
            saved_path = save_next_version("Shadow_Sessions", f"Session_{session_id}", final_result, processing_time=duration)
            print(f"Saved updated SOP to: {saved_path}")
            
            return {"sop": final_result, "status": "updated", "path": saved_path}

        # STANDARD FLOW (Drag & Drop)
        result = await process_sop_context(raw_sop, processing_time=duration)
        
        # Cleanup Context Files
        for g_file in gemini_context_files:
            try:
                genai.delete_file(g_file.name)
            except:
                pass
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

