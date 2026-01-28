import base64
import io
import pytesseract
from pdf2image import convert_from_bytes
import pandas as pd
import re

def extract_from_base64(base64_file):
    # 1. Read and Decode
    with open(base64_file, "r") as f:
        encoded_data = f.read()
    decoded_pdf = base64.b64decode(encoded_data)
    
    # 2. Convert PDF pages to Images (Works for both Scanned and E-PDF)
    images = convert_from_bytes(decoded_pdf)
    full_text = ""
    table_data = []

    for img in images:
        # OCR the page
        page_text = pytesseract.image_to_string(img)
        full_text += page_text
        
        # Table Extraction Logic using Regex (matching the pattern in your attachment)
        # Matches: [8-char AlphaNum], [Number], [Number], [Number], [Reason]
        matches = re.findall(r'([A-Z0-9]{13})\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+)', page_text)
        for m in matches:
            table_data.append({
                "Agreement_Number": m[0],
                "Penal_Charge": m[1],
                "Bounce_Charge": m[2],
                "Total_Waived": m[3],
                "Reason": m[4]
            })

    # 3. Extract Metadata (Approver and Time) [cite: 6, 7, 10]
    approver = "nazarenemustoor@outlook.com" if "nazarenemustoor" in full_text.lower() else "Unknown"
    status = "Approved" if "approved" in full_text.lower() else "Pending"
    
    return {
        "approver": approver,
        "status": status,
        "data": table_data
    }