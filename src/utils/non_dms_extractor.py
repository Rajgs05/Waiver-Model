# ---- Python 3.13 PaddleOCR fix ----
import types, sys
imghdr = types.ModuleType("imghdr")
imghdr.what = lambda *args, **kwargs: "jpeg"
sys.modules["imghdr"] = imghdr
# -----------------------------------

import base64
import io
import os
import re
import json
import pdfplumber
import numpy as np
from paddleocr import PaddleOCR
from pdf2image import convert_from_bytes

# Updated import to fix ModuleNotFoundError
try:
    from .validator import validate_non_dms_request
except ImportError:
    from validator import validate_non_dms_request

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)

def decode_and_extract_non_dms(base64_file_path):
    if not os.path.exists(base64_file_path):
        return {"error": f"File not found: {base64_file_path}"}

    with open(base64_file_path, "r") as f:
        encoded_data = f.read()
    decoded_pdf_bytes = base64.b64decode(encoded_data)
    
    full_text = ""
    text_found = False
    
    with pdfplumber.open(io.BytesIO(decoded_pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                text_found = True
                full_text += text + "\n"

    if not text_found:
        images = convert_from_bytes(decoded_pdf_bytes, dpi=300)
        for img in images:
            result = ocr.ocr(np.array(img), cls=True)
            if result and result[0]:
                page_text = " ".join([line[1][0] for line in result[0]])
                full_text += page_text + "\n"
        extraction_mode = "PaddleOCR"
    else:
        extraction_mode = "pdfplumber"

    # Metadata Extraction
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    from_match = re.search(r'From\s*[:\s]*(' + email_pattern + r')', full_text, re.I)
    sender_email = from_match.group(1) if from_match else (re.findall(email_pattern, full_text)[0] if re.findall(email_pattern, full_text) else "Unknown")

    date_match = re.search(r'Date\s*[:\s]*(.*?)(?=To|$)', full_text, re.I | re.S)
    extracted_date = date_match.group(1).strip() if date_match else "Unknown"

    lan_pattern = r'\b[A-Z][0-9][A-Z][0-9A-Z]{9,12}\b'
    found_lans = list(set(re.findall(lan_pattern, full_text, re.I)))

    extraction_results = {
        "category": "Non-DMS",
        "metadata": {
            "from": sender_email,
            "date_time": extracted_date,
            "fin_reference_no": found_lans
        },
        "is_waiver_request": "waiver" in full_text.lower(),
        "extraction_method": extraction_mode
    }

    return validate_non_dms_request(extraction_results)