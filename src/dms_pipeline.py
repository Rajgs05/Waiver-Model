import sys
import os
import json

# Fixes the 'Import could not be resolved' by pointing to the src folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.extractor import dms_extraction_logic
from utils.validator import validate_waiver_request

def run_pipeline():
    target_file = "Test1.pdf"
    print(f"--- Starting DMS Pipeline for {target_file} ---")
    
    try:
        raw_results = dms_extraction_logic(target_file)
        final_results = validate_waiver_request(raw_results)
        # Print JSON directly to the terminal as requested
        print("\nSUCCESS! EXTRACTED JSON DATA:")
        print(json.dumps(raw_results, indent=4))

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_pipeline()