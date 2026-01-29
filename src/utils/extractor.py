import base64
import os
import re
import json
import pytesseract
from pdf2image import convert_from_bytes
import random
import pdfplumber
import io

def clean_reason_text(text):
    """Clean and normalize reason text."""
    if not text:
        return None
    
    cleaned = re.sub(r'\s+', ' ', text).strip()
    cleaned = re.sub(r'^[\s|,;:\-_"\']+', '', cleaned)
    cleaned = re.sub(r'[\s|,;:\-_"\']+$', '', cleaned)
    cleaned = re.sub(r'[|]+', '', cleaned)
    cleaned = re.sub(r'^Number\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\d+\s+(?=[A-Z])', '', cleaned)
    cleaned = cleaned.strip()
    
    if cleaned and re.search(r'[a-zA-Z]', cleaned) and len(cleaned) >= 3:
        return cleaned
    return None

def extract_table_using_line_analysis(full_text):
    """
    EXTRACTS ACROSS MULTIPLE PAGES.
    Analyzes line by line without stopping at page-break footers.
    """
    lines = full_text.split('\n')
    table_start_idx = 0
    for idx, line in enumerate(lines):
        if re.search(r'Reason', line, re.IGNORECASE):
            table_start_idx = idx + 1
            break
    
    extracted_rows = []
    # Using your 13-char pattern for the actual Agreement Numbers
    id_pattern = r'\b[A-Z0-9]{8}\b'
    
    i = table_start_idx
    while i < len(lines):
        line = lines[i].strip()
        if not line or re.search(r'(Outlook|Page|\d+/\d+|https://)', line, re.IGNORECASE):
            i += 1
            continue
        
        id_match = re.search(id_pattern, line)
        if id_match:
            agreement_id = id_match.group()
            row_lines = [line]
            j = i + 1
            while j < len(lines) and j < i + 5:
                next_line = lines[j].strip()
                if next_line and not re.search(id_pattern, next_line):
                    if not re.search(r'(Regards|Thanks|Source|http|Outlook|Page)', next_line, re.IGNORECASE):
                        row_lines.append(next_line)
                    j += 1
                elif next_line and re.search(id_pattern, next_line):
                    break
                else:
                    j += 1
            
            full_row_text = ' '.join(row_lines)
            row_after_id=full_row_text.split(agreement_id,1)[1]
            numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', row_after_id)
            
            if len(numbers) >= 3:
                reason = None
                amount_pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?\b'
                number_matches = list(re.finditer(amount_pattern, full_row_text))
                if len(number_matches) >= 3:
                    after_third = full_row_text[number_matches[2].end():].strip()
                    reason = clean_reason_text(after_third)
                
                if not reason:
                    patterns = [
                        r'(bank\s+side\s+issue)',
                        r'(signature\s+missing)',
                        r'(signature\s+mismatch)',
                        r'(customer\s+request)',
                        r'(system\s+error)',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, full_row_text, re.IGNORECASE)
                        if match:
                            reason = ' '.join(word.capitalize() for word in match.group(1).split())
                            break
                
                extracted_rows.append({
                    "Agreement Number": agreement_id,
                    "Penal Charge": numbers[0],
                    "Bounce Charge": numbers[1],
                    "Total Amount to be Waived off": numbers[2],
                    "Reason": reason if reason else "Not Specified"
                })
            i = j
        else:
            i += 1
    return extracted_rows

def extract_table_using_segment_analysis(table_zone):
    extracted_rows = []
    id_pattern = r'\b[A-Z0-9]{8}\b'
    id_matches = list(re.finditer(id_pattern, table_zone))
    for i, match in enumerate(id_matches):
        agreement_id = match.group().strip()
        row_start = match.start()
        row_end = id_matches[i + 1].start() if i + 1 < len(id_matches) else len(table_zone)
        row_text = table_zone[row_start:row_end]
        numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', row_text)
        if len(numbers) >= 3:
            reason = None
            amount_pattern = r'\b\d+(?:,\d{3})*(?:\.\d+)?\b'
            row_after_id = row_text.split(agreement_id,1)[1]
            number_matches = list(re.finditer(amount_pattern, row_after_id))
            if len(number_matches) >= 3:
                after_third = row_after_id[number_matches[2].end():].strip()
                reason = clean_reason_text(after_third)

            extracted_rows.append({
                "Agreement Number": agreement_id,
                "Penal Charge": numbers[0],
                "Bounce Charge": numbers[1],
                "Total Amount to be Waived off": numbers[2],
                "Reason": reason if reason else "Not Specified"
            })
    return extracted_rows

def dms_extraction_logic(pdf_filename):
    base_path = "data/dms"
    raw_file_path = os.path.join(base_path, "01_raw_pdf", pdf_filename)
    b64_output_path = os.path.join(base_path, "02_base64_encoded", pdf_filename.replace(".pdf", ".txt"))
    final_json_path = os.path.join(base_path, "03_decoded_output", pdf_filename.replace(".pdf", ".json"))
    debug_path = os.path.join(base_path, "03_decoded_output", pdf_filename.replace(".pdf", "_debug.txt"))
    
    origin = random.choice(['Customer Eye', 'Non-Customer Eye'])

    with open(raw_file_path, "rb") as pdf_file:
        raw_pdf_bytes = pdf_file.read()
        b64_string = base64.encodebytes(raw_pdf_bytes).decode('utf-8')
    
    with open(b64_output_path, "w") as b64_file:
        b64_file.write(b64_string)

    # --- HYBRID EXTRACTION START ---
    full_text = ""
    extraction_mode = "pdfplumber"

    with pdfplumber.open(io.BytesIO(raw_pdf_bytes)) as pdf:
        for page in pdf.pages:
            # extract_text with layout=True preserves table alignments
            page_text = page.extract_text(layout=True)
            if page_text:
                full_text += page_text + "\n"
    

    # Fallback to OCR if pdfplumber returns empty or very little text (Scanned PDF)
    if len(full_text.strip()) < 50:
        extraction_mode = "OCR (pytesseract)"
        full_text = ""
        pages = convert_from_bytes(raw_pdf_bytes, dpi=300)
        for page in pages:
            full_text += pytesseract.image_to_string(page, config='--psm 6') + "\n"
    # --- HYBRID EXTRACTION END ---

    with open(debug_path, "w", encoding='utf-8') as f:
        f.write(f"=== EXTRACTION MODE: {extraction_mode} ===\n\n")
        f.write(full_text)

    from_match = re.search(r'From\s*(?:[:\s])\s*([^<\n\r]+(?:<[^>]+>)?|[\w.-]+@[\w.-]+\.\w+)', full_text, re.IGNORECASE)
    approver_email = None
    if from_match:
        raw_from = from_match.group(1)
        email_only = re.search(r'[\w.-]+@[\w.-]+\.\w+', raw_from)
        approver_email = email_only.group(0) if email_only else raw_from.strip()
    else:
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@outlook\.com)', full_text)
        approver_email = email_match.group(1) if email_match else None

    date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})', full_text)
    category_type = "DMS" if origin == "Customer Eye" else "Non-DMS"
    
    extracted_data = {
        "category": category_type,
        "origin": origin,
        "metadata": {
            "approver": approver_email,
            "approval_date": date_match.group(1) if date_match else None,
            "status": "Approved" if re.search(r'approved', full_text, re.IGNORECASE) else "Pending"
        },
        "waiver_details": []
    }

    rows = extract_table_using_line_analysis(full_text)
    if not rows:
        header_match = re.search(r'(Reason|Total\s+Amount)', full_text, re.IGNORECASE)
        table_start = header_match.end() if header_match else 0
        table_zone = full_text[table_start:]
        rows = extract_table_using_segment_analysis(table_zone)
    
    extracted_data["waiver_details"] = rows
    
    with open(final_json_path, "w") as json_file:
        json.dump(extracted_data, json_file, indent=4)
    
    return extracted_data