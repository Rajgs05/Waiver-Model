# ---- Python 3.13 PaddleOCR fix ----
import types, sys
imghdr = types.ModuleType("imghdr")
imghdr.what = lambda *args, **kwargs: "jpeg"
sys.modules["imghdr"] = imghdr
# -----------------------------------

import os, re, json, random, io
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
    id_pattern = r'\b[A-Z0-9]{8}\b'
    rows, buffer = [], ""

    for line in lines:
        if re.search(id_pattern, line):
            if buffer:
                rows.append(buffer)
            buffer = line
        else:
            buffer += " " + line
    if buffer:
        rows.append(buffer)

    extracted = []
    for row in rows:
        parts = re.split(r'\s{2,}', row)
        if len(parts) < 5 or not re.fullmatch(id_pattern, parts[0]):
            continue

        extracted.append({
            "Agreement Number": parts[0],
            "Penal Charge": parts[1],
            "Bounce Charge": parts[2],
            "Total Amount to be Waived off": parts[3],
            "Reason": clean_reason_text(parts[4]) or "Not Specified"
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
    raw_file_path = os.path.join(base_path, "01_raw_pdf", pdf_filename)
    final_json_path = os.path.join(base_path, "03_decoded_output", pdf_filename.replace(".pdf", ".json"))
    debug_path = os.path.join(base_path, "03_decoded_output", pdf_filename.replace(".pdf", "_debug.txt"))
    txt_output_path = os.path.join(base_path, "03_decoded_output", pdf_filename.replace(".pdf", "_table.txt"))

    origin = random.choice(['Customer Eye', 'Non-Customer Eye'])

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

    # -------- Save debug --------
    with open(debug_path, "w", encoding="utf-8") as f:
        f.write(f"Mode: {extraction_mode}\n\n")
        f.write(meta_text)

    # -------- Metadata Extraction --------
    from_match = re.search(r'From\s+.*?([\w\.-]+@[\w\.-]+\.\w+)',meta_text, re.IGNORECASE) 
    approver = from_match.group(1) if from_match else None   
    date_match = re.search(r'Date\s+.*?(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})', meta_text,re.IGNORECASE)

    result = {
        "category": "DMS" if origin == "Customer Eye" else "Non-DMS",
        "origin": origin,
        "metadata": {
            "approver": approver,
            "approval_date": date_match.group(1) if date_match else None,
            "status": "Approved" if re.search(r'approved', meta_text, re.I) else "Pending"
        },
        "waiver_details": rows
    }

    with open(final_json_path, "w") as f:
        json.dump(result, f, indent=4)

    # -------- Save Table TXT --------
    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write("Agreement Number | Penal Charge | Bounce Charge | Total Amount | Reason\n")
        f.write("-" * 85 + "\n")
        for row in rows:
            f.write(f"{row['Agreement Number']} | {row['Penal Charge']} | {row['Bounce Charge']} | {row['Total Amount to be Waived off']} | {row['Reason']}\n")

    return result
