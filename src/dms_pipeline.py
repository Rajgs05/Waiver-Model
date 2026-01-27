import sys
import os
import json

# Fixes the 'Import could not be resolved' by pointing to the src folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.extractor import dms_extraction_logic

def run_pipeline():
    target_file = "multipage.pdf"
    print(f"--- Starting DMS Pipeline for {target_file} ---")
    
    try:
        results = dms_extraction_logic(target_file)
        
        # Print JSON directly to the terminal as requested
        print("\nSUCCESS! EXTRACTED JSON DATA:")
        print(json.dumps(results, indent=4))
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_pipeline()