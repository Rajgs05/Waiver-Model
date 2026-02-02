import os
import sys
import types, sys

imghdr = types.ModuleType("imghdr")
imghdr.what = lambda *args, **kwargs: "jpeg"
sys.modules["imghdr"] = imghdr

# CRITICAL: Set these BEFORE any paddle imports
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['FLAGS_use_cuda'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

from paddleocr import PaddleOCR
from pdf2image import convert_from_path
import numpy as np
import json
from pathlib import Path

print("="*60)
print("PaddleOCR Extraction Tool")
print("="*60)

# Auto-detect PDF
pdf_folder = 'data/dms/01_raw_pdf'
pdf_files = list(Path(pdf_folder).glob('*.pdf'))

if not pdf_files:
    print(f"❌ No PDF files found in {pdf_folder}")
    sys.exit(1)

pdf_path = str(pdf_files[0])
print(f"✅ PDF found: {pdf_path}")

# Initialize PaddleOCR
print("🔄 Initializing PaddleOCR (this may take a moment)...")
try:
    ocr = PaddleOCR(
        use_angle_cls=True,
        lang='en',
        use_gpu=False,
        show_log=False
    )
    print("✅ PaddleOCR initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize PaddleOCR: {e}")
    sys.exit(1)

# Convert PDF to images
print(f"🔄 Converting PDF to images...")
try:
    images = convert_from_path(pdf_path)
    print(f"✅ Converted {len(images)} page(s)")
except Exception as e:
    print(f"❌ Error converting PDF: {e}")
    print("💡 Make sure Poppler is installed")
    sys.exit(1)

# Process each page
all_text = []
all_structured_data = []
errors = []

for page_num, img in enumerate(images, 1):
    print(f"\n{'='*60}")
    print(f"📄 Processing Page {page_num}/{len(images)}")
    print(f"{'='*60}")
    
    try:
        # Convert to numpy array
        img_array = np.array(img)
        
        # Perform OCR
        result = ocr.ocr(img_array, cls=True)
        
        # Extract text
        page_text = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                box = line[0]
                
                print(f"📝 {text} (confidence: {confidence:.2%})")
                page_text.append(text)
                
                all_structured_data.append({
                    'page': page_num,
                    'text': text,
                    'confidence': confidence,
                    'bbox': box
                })
            
            all_text.extend(page_text)
            print(f"✅ Extracted {len(page_text)} lines from this page")
        else:
            print("⚠️  No text detected on this page")
            
    except Exception as e:
        error_msg = f"Page {page_num}: {str(e)}"
        errors.append(error_msg)
        print(f"❌ Error: {e}")
        continue

# Save outputs
print(f"\n{'='*60}")
print("💾 Saving results...")
output_folder = 'data/dms/03_decoded_output'
os.makedirs(output_folder, exist_ok=True)

# Save plain text
output_file = os.path.join(output_folder, 'extracted_text.txt')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(all_text))
print(f"✅ Text saved: {output_file}")

# Save JSON
json_file = os.path.join(output_folder, 'extracted_data.json')
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(all_structured_data, f, indent=2, ensure_ascii=False)
print(f"✅ JSON saved: {json_file}")

# Save errors if any
if errors:
    error_file = os.path.join(output_folder, 'errors.txt')
    with open(error_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(errors))
    print(f"⚠️  Errors logged: {error_file}")

# Summary
print(f"\n{'='*60}")
print(f"✅ EXTRACTION COMPLETE!")
print(f"{'='*60}")
print(f"📊 Total lines extracted: {len(all_text)}")
print(f"📄 Pages processed: {len(images)}")
if errors:
    print(f"⚠️  Errors encountered: {len(errors)}")
print(f"{'='*60}")