# ---- Python 3.13 PaddleOCR fix ----
import types, sys
imghdr = types.ModuleType("imghdr")
imghdr.what = lambda *args, **kwargs: "jpeg"
sys.modules["imghdr"] = imghdr
# -----------------------------------

import os, re, json, io
import numpy as np
import pdfplumber
from paddleocr import PaddleOCR
from pdf2image import convert_from_bytes

ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)

# ---------------- HELPERS ---------------- #

def clean_reason_text(text):
    if not text:
        return None
    text = re.sub(r'\s+', ' ', text).strip()
    return text if len(text) > 2 else None

def group_by_y(tokens, threshold=100):
    tokens.sort(key=lambda x: x[1])
    rows, current_row, current_y = [], [], None

    for x, y, text in tokens:
        if current_y is None or abs(y - current_y) < threshold:
            current_row.append((x, y, text))
            current_y = y
        else:
            rows.append(current_row)
            current_row = [(x, y, text)]
            current_y = y

    if current_row:
        rows.append(current_row)
    return rows

# ---------------- E-PDF PARSER ---------------- #

def extract_using_columns(full_text):
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
    # Updated pattern to be case-insensitive and handle 8-char IDs
    id_pattern = r'[A-Z0-9]{8}' 
    extracted = []

    for line in lines:
        # Search for the ID anywhere in the line to be safe
        match = re.search(id_pattern, line)
        if match:
            # Flexible splitting: handles 1 or more spaces/tabs
            parts = re.split(r'\s{1,}', line) 
            
            # Locate the index where the ID starts
            id_idx = -1
            for i, p in enumerate(parts):
                if re.fullmatch(id_pattern, p):
                    id_idx = i
                    break
            
            # If we found an ID and there are at least 3 numbers following it
            if id_idx != -1 and len(parts) >= id_idx + 4:
                extracted.append({
                    "Agreement Number": parts[id_idx],
                    "Penal Charge": parts[id_idx + 1],
                    "Bounce Charge": parts[id_idx + 2],
                    "Total Amount to be Waived off": parts[id_idx + 3],
                    # Join remaining parts as the Reason
                    "Reason": clean_reason_text(" ".join(parts[id_idx + 4:])) or "Not Specified"
                })
    return extracted

# ---------------- OCR PARSER ---------------- #

def extract_using_ocr_layout(raw_pdf_bytes):
    pages = convert_from_bytes(raw_pdf_bytes, dpi=300)
    id_pattern = r'\b[A-Z0-9]{8}\b'
    extracted, full_page_text = [], []

    for page in pages:
        img = np.array(page)
        result = ocr.ocr(img, cls=True)
        tokens = []

        if result and result[0]:
            for box, (text, conf) in result[0]:
                x = (box[0][0] + box[2][0]) / 2
                y = (box[0][1] + box[2][1]) / 2
                text = text.strip()
                tokens.append((x, y, text))
                full_page_text.append(text)

        rows = group_by_y(tokens)

        for row in rows:
            row.sort(key=lambda x: x[0])
            texts = [t[2] for t in row]

            id_match = next((t for t in texts if re.fullmatch(id_pattern, t)), None)
            if not id_match:
                continue

            numbers = [t for t in texts if re.fullmatch(r'\d+(?:,\d{3})*(?:\.\d+)?', t)]
            reason_parts = []
            for t in texts:
                if t not in numbers and t != id_match:
                    reason_parts.append(t)
            reason = clean_reason_text(" ".join(reason_parts))

            if len(numbers) >= 3:
                extracted.append({
                    "Agreement Number": id_match,
                    "Penal Charge": numbers[0],
                    "Bounce Charge": numbers[1],
                    "Total Amount to be Waived off": numbers[2],
                    "Reason": clean_reason_text(" ".join(reason_parts)) or "Not Specified"
                })

    return extracted, " ".join(full_page_text)

# ---------------- MAIN PIPELINE ---------------- #

def dms_extraction_logic(pdf_filename):
    base_path = "data/dms"
    raw_file_path = os.path.join("raw_files", pdf_filename) # Updated to point to common raw_files
    final_json_path = os.path.join(base_path, "03_decoded_output", pdf_filename.replace(".pdf", ".json"))
    
    with open(raw_file_path, "rb") as f:
        raw_pdf_bytes = f.read()

    # -------- Detect PDF type --------
    full_text = ""
    text_found = False

    with pdfplumber.open(io.BytesIO(raw_pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text_found = True
                full_text += page_text + "\n"

    if text_found:
        extraction_mode = "pdfplumber"
        rows = extract_using_columns(full_text)
        meta_text = full_text
    else:
        extraction_mode = "OCR Layout"
        rows, meta_text = extract_using_ocr_layout(raw_pdf_bytes)

    # -------- Remove duplicate agreements --------
    unique_rows = {}
    for r in rows:
        key = (r["Agreement Number"], r["Penal Charge"], r["Bounce Charge"], r["Total Amount to be Waived off"])
        unique_rows[key] = r
    rows = list(unique_rows.values())

    # -------- Metadata Extraction --------
    from_match = re.search(r'From\s+.*?([\w\.-]+@[\w\.-]+\.\w+)', meta_text, re.IGNORECASE) 
    approver = from_match.group(1) if from_match else None   
    date_match = re.search(r'Date\s+.*?(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})', meta_text, re.IGNORECASE)

    # Static categorization for DMS logic
    result = {
        "category": "DMS",
        "origin": "Customer Eye",
        "metadata": {
            "approver": approver,
            "approval_date": date_match.group(1) if date_match else None,
            "status": "Approved" if re.search(r'approved', meta_text, re.I) else "Pending"
        },
        "waiver_details": rows,
        "extraction_method": extraction_mode
    }

    # Save to DMS folder
    os.makedirs(os.path.dirname(final_json_path), exist_ok=True)
    with open(final_json_path, "w") as f:
        json.dump(result, f, indent=4)

    return result