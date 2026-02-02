import types, sys
imghdr = types.ModuleType("imghdr")
imghdr.what = lambda *args, **kwargs: "jpeg"
sys.modules["imghdr"] = imghdr




import io
import re
import numpy as np
import pdfplumber
from paddleocr import PaddleOCR
from pdf2image import convert_from_bytes

# Lightweight OCR instance for routing
router_ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)

def categorize_document(pdf_bytes):
    """
    Categorizes PDF as DMS (Customer Eye) or Non-DMS (Non-Customer Eye).
    Works for both digital and scanned documents.
    """
    full_text = ""
    
    # 1. Digital Text Check
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                full_text += text + "\n"
    
    # 2. Scanned Fallback: OCR first page only
    if not full_text.strip():
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
        if images:
            img_array = np.array(images[0])
            result = router_ocr.ocr(img_array, cls=True)
            if result and result[0]:
                full_text = " ".join([line[1][0] for line in result[0]])

    # 3. Decision Logic
    # DMS (Customer Eye) contains table headers
    if "Agreement" in full_text and ("Penal" in full_text or "Bounce" in full_text):
        return "DMS"
    
    # Non-DMS (Non-Customer Eye) contains LAN/Waiver keywords
    elif "LAN" in full_text or "P2W" in full_text or "waiver" in full_text.lower():
        return "Non-DMS"
        
    return "Non-DMS"