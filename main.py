# ---- Python 3.13 PaddleOCR fix ----
import types, sys, os
imghdr = types.ModuleType("imghdr")
imghdr.what = lambda *args, **kwargs: "jpeg"
sys.modules["imghdr"] = imghdr
# -----------------------------------
from dotenv import load_dotenv
load_dotenv()
import json
# Ensure the src folder is accessible for imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from langgraph_app import app # Import the compiled StateGraph [cite: 2025-12-15]
from src.utils.encoder import encode_all_raw_to_base64

def run_agentic_automation():
    # 1. First, encode all raw PDFs into Base64
    encode_all_raw_to_base64()
    
    raw_folder = "raw_files"
    output_folder = "data/03_decoded_output"
    
    if not os.path.exists(raw_folder):
        print(f"Error: {raw_folder} directory not found. Please create it and drop PDFs.")
        return

    files = [f for f in os.listdir(raw_folder) if f.endswith('.pdf')]
    print(f"\n--- LangGraph Agentic Pipeline Started for {len(files)} files ---")

    for file_name in files:
        print(f"\n>>> Starting Agent for: {file_name}")
        
        # 2. Prepare the initial state for the document [cite: 2025-12-15]
        initial_state = {"current_file": file_name}
        
        # 3. Invoke the LangGraph workflow
        # This will automatically categorize and extract based on your nodes [cite: 2025-12-15]
        config = {"run_name": f"Processing_{file_name}"}
        final_state = app.invoke(initial_state,config=config)
        
        # 4. Save the finalized JSON result
        final_json_path = os.path.join(output_folder, file_name.replace(".pdf", ".json"))
        os.makedirs(os.path.dirname(final_json_path), exist_ok=True)
        
        with open(final_json_path, "w") as f:
            json.dump(final_state["extracted_data"], f, indent=4)
            
        print(f">>> Finished {file_name}. Recommendation: {final_state['extracted_data'].get('validation_results', [{}])[0].get('recommendation', 'Check DMS result')}")

if __name__ == "__main__":
    run_agentic_automation()