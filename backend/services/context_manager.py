import json
import re
import google.generativeai as genai
from .storage_service import save_next_version, load_latest_sop, init_knowledge_base, get_all_process_identifiers

MERGE_UPDATE_PROMPT = """
You are an intelligent SOP Manager. 

Input 1: EXISTING SOP for a process.
Input 2: NEW INFORMATION extracted from a recent video of the SAME process.

Goal: Update the EXISTING SOP with the NEW INFORMATION. 

Rules:
1. Preserve all valid information from the EXISTING SOP.
2. Add new steps, edge cases, or details found in the NEW INFORMATION.
3. If there is a conflict, trust the NEW INFORMATION (assume it's the latest version).
4. Add a "## Change Log" section at the bottom summarizing what was updated.
5. maintain the same strict Markdown structure.

Output: The fully updated SOP in Markdown.
"""

ROUTER_PROMPT = """
You are the Knowledge Base Librarian.
Your job is to decide where to file a new SOP document.

Input 1: New SOP Draft (Metadata & Summary)
Input 2: List of EXISTING Process Files in the Database (Format: Company/Process_FileName)

Task:
1. Analyze the New SOP context.
2. Check if it strictly belongs to any EXISTING process (is it an update, correction, or variation of that specific process?).
3. If it MATCHES an existing process, return the identifying parameters of that existing file.
4. If it is a COMPLETELY NEW process, return the proper new names.

Output JSON Format:
{
  "action": "UPDATE" or "CREATE",
  "target_company": "Name",
  "target_process_name": "Name",
  "reasoning": "Why you chose this action"
}

Constraints:
- If the new content is "Billing Process" and you see "Acme/Acme_Billing_Process", ACTION is UPDATE.
- If the new content is "Hiring" and you see "Acme/Acme_Billing_Process", ACTION is CREATE.
- Be smart about naming. 'target_process_name' should match the existing base filename if updating.
"""

def extract_metadata(sop_text: str):
    """Extracts the JSON metadata block from the SOP text."""
    try:
        match = re.search(r"```json\n(.*?)\n```", sop_text, re.DOTALL)
        if match:
            json_str = match.group(1)
            metadata = json.loads(json_str)
            # Remove the metadata block from the text so it doesn't duplicate
            clean_text = re.sub(r"```json\n(.*?)\n```", "", sop_text, flags=re.DOTALL).strip()
            return metadata, clean_text
    except Exception as e:
        print(f"Metadata extraction failed: {e}")
    
    # Fallback
    return {"company_name": "General", "process_name": "New Process"}, sop_text

async def process_sop_context(raw_sop: str, processing_time: float = 0.0, model_name="gemini-2.5-pro"):
    """
    1. Extracts metadata.
    2. ROUTER: Checks identity against DB.
    3. Merges or Saves.
    4. Saves with processing time metadata.
    """
    init_knowledge_base()
    
    # 1. Initial Extraction
    extracted_metadata, clean_text = extract_metadata(raw_sop)
    draft_company = extracted_metadata.get("company_name", "General")
    draft_process = extracted_metadata.get("process_name", "New Process")
    
    # 2. Router: Check against existing DB
    existing_processes = get_all_process_identifiers()
    print(f"Router Check: Checking '{draft_process}' against {len(existing_processes)} existing files.")
    
    model = genai.GenerativeModel(model_name=model_name)
    
    if existing_processes:
        router_response = await model.generate_content_async([
            ROUTER_PROMPT, 
            f"NEW SOP METADATA: {json.dumps(extracted_metadata)}",
            f"NEW SOP CONTENT SNIPPET: {clean_text[:500]}...",
            f"EXISTING PROCESSES: {json.dumps(existing_processes)}"
        ])
        
        try:
            # Extract JSON from Router Response
            router_json_match = re.search(r"```json\n(.*?)\n```", router_response.text, re.DOTALL)
            if router_json_match:
                decision = json.loads(router_json_match.group(1))
                print(f"Router Decision: {decision}")
                
                # Override with Router decision
                # Note: target_process_name from router should ideally be the 'Process Name' part, NOT the full filename if possible.
                # But storage_service expects the 'Process Name' to sanitize and build the filename.
                # If Router returns 'Acme_Billing_Process' (filename base), and we pass that as process_name, 
                # storage_service will sanitize it -> 'Acme_Billing_Process'.
                # We need to be careful not to double-prefix. 
                
                # Let's rely on the router returning the *semantic* name or the *filename base*.
                # If action is UPDATE, we MUST use the name that matches the file on disk to trigger the merge.
                
                if decision.get("action") == "UPDATE":
                    target_company = decision.get("target_company")
                    target_process_file = decision.get("target_process_name") # e.g. Acme_Billing
                    
                    # We need to extract the raw process name from the filename if it's prefixed
                    # Filename: {Company}_{Process}
                    # If target_process_file is "Acme_Billing", and Company is "Acme", Process is "Billing".
                    
                    final_company = target_company
                    
                    # heuristic to strip company prefix if present in the decided name
                    clean_company_prefix = target_company.replace(" ", "") + "_"
                    if target_process_file.startswith(clean_company_prefix):
                        final_process = target_process_file[len(clean_company_prefix):]
                    else:
                        final_process = target_process_file
                        
                    print(f"Routing to UPDATE: {final_company} / {final_process}")
                    draft_company = final_company
                    draft_process = final_process

                else:
                    # CREATE -> Use the refined names from router if available, else stick to draft
                    if decision.get("target_company"):
                         draft_company = decision.get("target_company")
                    if decision.get("target_process_name"):
                         draft_process = decision.get("target_process_name")
                    print(f"Routing to CREATE: {draft_company} / {draft_process}")

        except Exception as e:
             print(f"Router Parsing Failed: {e}. Falling back to extraction.")

    company = draft_company
    process = draft_process


    print(f"Final Context: Company='{company}', Process='{process}'")
    
    existing_sop = load_latest_sop(company, process)
    
    final_sop = clean_text
    status = "created"
    
    if existing_sop:
        print("Existing SOP found (Confirmed by context). Merging...")
        response = await model.generate_content_async([MERGE_UPDATE_PROMPT, f"EXISTING SOP:\n{existing_sop}", f"NEW INFO:\n{clean_text}"])
        final_sop = response.text
        status = "updated"
    
    # Save the final version with timing
    file_path = save_next_version(company, process, final_sop, processing_time)
    
    return {
        "sop": final_sop,
        "metadata": {"company_name": company, "process_name": process},
        "status": status,
        "file_path": file_path,
        "processing_time": processing_time
    }
