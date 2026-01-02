import os
import time
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

KB_DIR = "knowledge_base"
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
BUCKET_NAME = "sops"

# Initialize Supabase Client if keys exist
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase Client Initialized")
    except Exception as e:
        print(f"⚠️ Failed to init Supabase: {e}")

def use_cloud_storage():
    return supabase_client is not None

# --- Common Utils ---

def sanitize_name(name: str) -> str:
    """Sanitizes strings to be safe for filenames."""
    return "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()

# --- Local Filesystem Implementation ---

def _local_init():
    if not os.path.exists(KB_DIR):
        os.makedirs(KB_DIR)

def _local_save(company: str, process_name: str, content: str, processing_time: float) -> str:
    _local_init()
    company_clean = sanitize_name(company)
    company_dir = os.path.join(KB_DIR, company_clean)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
        
    # Get Version
    base_filename = f"{company_clean}_{sanitize_name(process_name)}"
    max_v = 0
    for f in os.listdir(company_dir):
        if f.startswith(base_filename) and f.endswith(".md"):
            try:
                v = int(f.rsplit("_v", 1)[1].replace(".md", ""))
                max_v = max(max_v, v)
            except: continue
    
    filename = f"{base_filename}_v{max_v + 1}.md"
    file_path = os.path.join(company_dir, filename)
    
    if processing_time > 0:
         content = f"<!-- metadata:processing_time={processing_time} -->\n{content}"
         
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path

def _local_list():
    docs = []
    if not os.path.exists(KB_DIR): return docs
    
    for company in os.listdir(KB_DIR):
        c_path = os.path.join(KB_DIR, company)
        if os.path.isdir(c_path):
            for f in os.listdir(c_path):
                if f.endswith(".md"):
                    try:
                        path = os.path.join(c_path, f)
                        stats = os.stat(path)
                        created = datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M")
                        
                        # Metadata read
                        proc_time = 0
                        with open(path, 'r') as file:
                            line = file.readline().strip()
                            if "metadata:processing_time" in line:
                                proc_time = float(line.split("=")[1].replace(" -->", ""))
                                
                        docs.append({
                            "id": path,
                            "company": company,
                            "filename": f,
                            "name": f.rsplit("_v", 1)[0].replace(f"{company}_", ""),
                            "version": "v" + f.rsplit("_v", 1)[1].replace(".md", ""),
                            "date": created,
                            "processing_time": proc_time
                        })
                    except: continue
    docs.sort(key=lambda x: x['date'], reverse=True)
    return docs

def _local_read(path: str) -> Optional[str]:
    # Handle both full paths (internal usage) and relative paths (API usage)
    if path.startswith(KB_DIR):
        full_path = path
    else:
        full_path = os.path.join(KB_DIR, path)
        
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

# --- Supabase Implementation ---

def _supabase_save(company: str, process_name: str, content: str, processing_time: float) -> str:
    company_clean = sanitize_name(company)
    base_filename = f"{company_clean}_{sanitize_name(process_name)}"
    
    # 1. List files to find ID
    # Simpler: Just rely on timestamp or random ID? No, user wants versioning.
    # We have to list bucket contents starting with prefix.
    # Path in bucket: {company}/{filename}
    
    try:
        max_v = 0
        res = supabase_client.storage.from_(BUCKET_NAME).list(company_clean)
        # res is a list of dicts or objects
        for file in res:
             name = file['name'] # type: ignore
             if name.startswith(base_filename) and name.endswith(".md"):
                 try:
                    v = int(name.rsplit("_v", 1)[1].replace(".md", ""))
                    max_v = max(max_v, v)
                 except: continue
                 
        next_v = max_v + 1
        filename = f"{base_filename}_v{next_v}.md"
        path = f"{company_clean}/{filename}"
        
        if processing_time > 0:
             content = f"<!-- metadata:processing_time={processing_time} -->\n{content}"
        
        # Upload
        supabase_client.storage.from_(BUCKET_NAME).upload(
            path,
            content.encode('utf-8'),
            {"content-type": "text/markdown"}
        )
        
        # Get Public URL
        public_url = supabase_client.storage.from_(BUCKET_NAME).get_public_url(path)
        return public_url
        
    except Exception as e:
        print(f"Supabase Save Error: {e}")
        return "error_saving_to_cloud"

def _supabase_list():
    docs = []
    try:
        # We need to list folders first? Supabase list accepts folder path.
        # Root list might return folders if empty path?
        # Supabase storage doesn't really have folders, just paths.
        # But `.list()` on root returns top level items.
        
        root_items = supabase_client.storage.from_(BUCKET_NAME).list()
        
        for item in root_items:
            # If it's a folder (no metadata/id usually, or is_metadata check)
            # Actually Supabase returns folders as items with id=None sometimes or mimetype
            # Let's assume structure is Company/File.md
            
            # Recursive check or just explicit knowledge of companies?
            # We implemented `list()` on root. It returns top-level folders?
            # Let's try iterating.
            
            company_name = item['name']
            
            # List inside company folder
            files = supabase_client.storage.from_(BUCKET_NAME).list(company_name)
            
            for f in files:
                fname = f['name']
                if fname.endswith(".md"):
                    created_at = f.get('created_at', '')
                    # Cleanup date format 2023-10-10T...
                    if created_at:
                        created_at = created_at.split('T')[0]
                    
                    # We can't peek content easily for metadata without downloading
                    # So we skip processing_time for list view in Cloud mode for efficiency
                    
                    try:
                        docs.append({
                            "id": f"{company_name}/{fname}", # Store relative path as ID
                            "company": company_name,
                            "filename": fname,
                            "name": fname.rsplit("_v", 1)[0].replace(f"{company_name}_", ""),
                            "version": "v" + fname.rsplit("_v", 1)[1].replace(".md", ""),
                            "date": created_at,
                            "processing_time": 0 # Not available without extra read
                        })
                    except: continue
                    
        docs.sort(key=lambda x: x['date'], reverse=True)
        return docs
        
    except Exception as e:
        print(f"Supabase List Error: {e}")
        return []

def _supabase_read(path: str) -> Optional[str]:
    try:
        # Path is "Company/File.md"
        data = supabase_client.storage.from_(BUCKET_NAME).download(path)
        return data.decode('utf-8')
    except Exception as e:
        print(f"Supabase Read Error: {e}")
        return None

# --- Main Interface ---

def save_next_version(company: str, process_name: str, content: str, processing_time: float = 0.0) -> str:
    if use_cloud_storage():
        return _supabase_save(company, process_name, content, processing_time)
    else:
        return _local_save(company, process_name, content, processing_time)

def list_all_documents():
    if use_cloud_storage():
        return _supabase_list()
    else:
        return _local_list()

def read_document(path: str) -> Optional[str]:
    # Check if path looks like a Supabase URL or relative path
    # If using cloud, we expect path to be 'Company/File.md'
    if use_cloud_storage():
        # If it was returned by list(), it's 'Company/File.md'
        # If it's a URL, we need to extract? 
        # Our list returns relative path ID.
        return _supabase_read(path)
    else:
        return _local_read(path)

# Stub for compatibility (not critical for Cloud)
def init_knowledge_base():
    if not use_cloud_storage(): _local_init()

def get_latest_version(company_dir, base_name):
    return 0 # Not used externally much

def load_latest_sop(company: str, process_name: str) -> Optional[str]:
    """Loads the latest version of the SOP if it exists."""
    if use_cloud_storage():
        # Cloud Logic
        company_clean = sanitize_name(company)
        base_filename = f"{company_clean}_{sanitize_name(process_name)}"
        try:
            max_v = 0
            latest_file = None
            res = supabase_client.storage.from_(BUCKET_NAME).list(company_clean)
            for file in res:
                 name = file['name']
                 if name.startswith(base_filename) and name.endswith(".md"):
                     try:
                        v = int(name.rsplit("_v", 1)[1].replace(".md", ""))
                        if v > max_v:
                            max_v = v
                            latest_file = name
                     except: continue
            
            if latest_file:
                path = f"{company_clean}/{latest_file}"
                return _supabase_read(path)
            return None
        except:
             return None
    else:
        # Local Logic
        company_clean = sanitize_name(company)
        process_clean = sanitize_name(process_name)
        base_filename = f"{company_clean}_{process_clean}"
        company_dir = os.path.join(KB_DIR, company_clean)
        
        if not os.path.exists(company_dir):
            return None
            
        max_v = 0
        for filename in os.listdir(company_dir):
            if filename.startswith(base_filename) and filename.endswith(".md"):
                try:
                    v = int(filename.rsplit("_v", 1)[1].replace(".md", ""))
                    max_v = max(max_v, v)
                except: continue
        
        if max_v == 0: return None
        
        file_path = os.path.join(company_dir, f"{base_filename}_v{max_v}.md")
        return _local_read(file_path)

def get_all_process_identifiers() -> list[str]:
    """Returns a list of 'Company/ProcessName' string for all existing processes."""
    identifiers = []
    if use_cloud_storage():
         # Cloud Logic
        try:
            # We assume folder structure: Company/
            root_items = supabase_client.storage.from_(BUCKET_NAME).list()
            for item in root_items:
                company = item['name']
                # List files in company
                files = supabase_client.storage.from_(BUCKET_NAME).list(company)
                seen = set()
                for f in files:
                    fname = f['name']
                    if fname.endswith(".md") and "_v" in fname:
                        try:
                            # Org_Process_vN.md
                            base = fname.rsplit("_v", 1)[0]
                            # base is Company_Process
                            # We want to extract Process.
                            # But wait, sanitize_name might have removed separators?
                            # Our convention: "{company_clean}_{process_clean}"
                            # This is tricky to reverse if we don't know where the split is.
                            # But generally name_part.replace(f"{company}_", "") works if company matches.
                            
                            process_part = base.replace(f"{company}_", "")
                            full_id = f"{company}/{process_part}"
                            if full_id not in seen:
                                identifiers.append(full_id)
                                seen.add(full_id)
                        except: continue
        except:
            pass
    else:
        # Local Logic
        if not os.path.exists(KB_DIR): return []
        for company in os.listdir(KB_DIR):
            c_path = os.path.join(KB_DIR, company)
            if os.path.isdir(c_path):
                seen = set()
                for f in os.listdir(c_path):
                    if f.endswith(".md") and "_v" in f:
                        try:
                            base = f.rsplit("_v", 1)[0]
                            # Assuming base starts with company_
                            if base.startswith(f"{company}_"):
                                process_part = base[len(company)+1:]
                                full_id = f"{company}/{process_part}"
                                if full_id not in seen:
                                    identifiers.append(full_id)
                                    seen.add(full_id)
                        except: continue
    return identifiers

