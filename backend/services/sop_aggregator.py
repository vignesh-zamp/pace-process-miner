import google.generativeai as genai
import asyncio

MERGE_PROMPT = """
You are an expert Technical Writer and Solutions Architect. 
You have been given multiple "Partial SOPs" extracted from different context/segments of the same process.

Your goal is to MERGE these partial inputs into one single, cohesive, and EXTREMELY COMPREHENSIVE Standard Operating Procedure (SOP) and Implementation Specification.

Input:
A list of partial SOP texts.

Output: 
A STRICT Markdown SOP starting with a JSON Metadata block, followed by the exact structure below.

## RULES
1.  **Deduplicate**: If chunks repeat info, merge it.
2.  **Continuity**: Ensure step numbering is continuous across the whole process.
3.  **Completeness**: Fill in all sections of the schema below. If a section is missing from partials, infer it or mark as "Not Observed".
4.  **Consolidate Evidence**: Merge all Evidence Logs into Section 3.12 and 5.1.

## FORMAT (Strict)

### 1. JSON Metadata Block
```json
{
  "company_name": "Inferred or Generic",
  "process_name": "Descriptive Process Title"
}
```

### 2. Open Questions for Client
*   **Priority: Critical**:
*   **Priority: Medium**:
*   **Priority: Low**:

### 3. Process Document
#### 3.1 Executive Summary
*   **Overview**:
*   **Scope (Volume, Geo, Team, Impact)**:
*   **Key Characteristics**:
*   **Confidence Level**:

#### 3.2 Business Context
*   **What the Company Does**:
*   **Entity Hierarchy**:
*   **Process Cycle**:

#### 3.3 Process Types/Variants
*   (List variants, when used, complexity)

#### 3.4 Detailed Process Workflow
(Iterate Stages)
*   **Stage**:
*   (Iterate Steps):
    *   **Step #, Name, Owner, System**:
    *   **Input**:
    *   **Process Actions**: (Detailed)
    *   **Output**:
    *   **Logic/Decisions**:
    *   **Exceptions**:

#### 3.5 Systems Landscape
*   **Systems Table**:
*   **Data Sources**:
*   **Integrations**:

#### 3.6 Regional Variations
*   (If applicable)

#### 3.7 Roles and Responsibilities
*   **Roles Table**:
*   **Approval Authorities**:

#### 3.8 Input Documents & Data
*   **Static/Dynamic Inputs**:
*   **Key Data Fields**:

#### 3.9 QA & Controls
*   **Pre/In/Post Controls**:

#### 3.10 Exception Handling
*   **Exception Table**:
*   **Edge Cases**:

#### 3.11 Timing & SLAs
*   **Timeline Table**:
*   **SLA Metrics**:

#### 3.12 Evidence Source Log
*   (Consolidated list from all chunks)

---

### 4. SOP Implementation Spec

#### 4.1 Process Setup Metadata
*   (Org, Process, Type, Complexity, Automation Potential)

#### 4.2 Workflow Chart
*   (Text/Mermaid flow)

#### 4.3 Prompt Flow Chart Table
*   (Step, Prompt Name, Objective, I/O)

#### 4.4 External System Dependencies
*   (System, Access, Credentials, API, Limits)

#### 4.5 Data Tables & Datasets
*   (Dataset Name, Columns, Validation Rules)

#### 4.6 Dashboard Config
*   (Run States, Process View Table)

#### 4.7 Log Groups
*   (Log Group Name, Messages, Triggers, Artifacts)

#### 4.8 Cross-Doc Validation
*   (Validation Matrix)

#### 4.9 Email/Triggers
*   (Config)

#### 4.10 IDs Table
*   (Type, ID)

#### 4.11 Implementation Notes
*   (Readiness, Phases, Risks)

#### 4.12 Test Plan
*   (Golden Dataset, Scenarios)

#### 4.13 Change Log

---

### 5. Appendix
#### 5.1 Evidence Quality Assessment
*   (Quality, Strengths, Gaps, Recommendations)
"""

def merge_partial_sops(partial_sops: list[str], model_name="gemini-2.5-pro") -> str:
    """Sends all partial SOPs to Gemini to be merged into one."""
    
    if not partial_sops:
        return ""
        
    if len(partial_sops) == 1:
        return partial_sops[0]

    combined_text = "\n\n=== NEXT PARTIAL SOP ===\n\n".join(partial_sops)
    
    model = genai.GenerativeModel(model_name=model_name)
    
    response = model.generate_content([MERGE_PROMPT, combined_text])
    
    return response.text
