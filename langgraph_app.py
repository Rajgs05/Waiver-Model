# ---- Python 3.13 PaddleOCR fix ----
import types, sys, os
imghdr = types.ModuleType("imghdr")
imghdr.what = lambda *args, **kwargs: "jpeg"
sys.modules["imghdr"] = imghdr
# -----------------------------------

import json
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

# Import your existing logic nodes
from src.utils.router import categorize_document
from src.utils.extractor import dms_extraction_logic
from src.utils.non_dms_extractor import decode_and_extract_non_dms
from src.utils.encoder import encode_all_raw_to_base64

# 1. Define the State Structure [cite: 2025-12-15]
class GraphState(TypedDict):
    current_file: str
    category: Optional[str]
    extracted_data: Optional[dict]

# 2. Define the Nodes (Functions)
def categorization_node(state: GraphState):
    print(f"--- Node: Categorizing {state['current_file']} ---")
    raw_path = os.path.join("raw_files", state["current_file"])
    with open(raw_path, "rb") as f:
        pdf_bytes = f.read()
    category = categorize_document(pdf_bytes)
    return {"category": category}

def dms_node(state: GraphState):
    print("--- Node: Executing DMS Extraction ---")
    result = dms_extraction_logic(state["current_file"])
    return {"extracted_data": result}

def non_dms_node(state: GraphState):
    print("--- Node: Executing Non-DMS Extraction ---")
    # Pointing to the encoded text file area
    base64_path = os.path.join("data", "02_base64_encoded", state["current_file"].replace(".pdf", ".txt"))
    result = decode_and_extract_non_dms(base64_path)
    return {"extracted_data": result}

# 3. Define Routing Logic
def decide_path(state: GraphState):
    if state["category"] == "DMS":
        return "dms"
    return "non_dms"

# 4. Build the Graph
workflow = StateGraph(GraphState)

workflow.add_node("categorize_doc", categorization_node)
workflow.add_node("dms_processor", dms_node)
workflow.add_node("non_dms_processor", non_dms_node)

workflow.set_entry_point("categorize_doc")

workflow.add_conditional_edges(
    "categorize_doc",
    decide_path,
    {
        "dms": "dms_processor",
        "non_dms": "non_dms_processor"
    }
)

workflow.add_edge("dms_processor", END)
workflow.add_edge("non_dms_processor", END)

app = workflow.compile()