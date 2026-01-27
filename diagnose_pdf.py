"""
Diagnostic script to check what OCR is reading from PDFs.
Run this BEFORE updating your extractor to see what's being captured.

Usage: python diagnose_pdf.py
"""

import os
import re
import pytesseract
from pdf2image import convert_from_bytes

def diagnose_pdf(pdf_path):
    """Diagnose what OCR is reading from a PDF file."""
    
    print("\n" + "="*80)
    print(f"DIAGNOSING: {os.path.basename(pdf_path)}")
    print("="*80 + "\n")
    
    # Read PDF
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    # Convert to images
    pages = convert_from_bytes(pdf_bytes, dpi=300)
    
    for page_num, page in enumerate(pages, 1):
        print(f"\n{'='*80}")
        print(f"PAGE {page_num}")
        print('='*80)
        
        # OCR with PSM 6 (what your code uses)
        text = pytesseract.image_to_string(page, config='--psm 6')
        
        # Split into lines
        lines = text.split('\n')
        
        print("\n--- ALL LINES (with line numbers) ---")
        for i, line in enumerate(lines):
            if line.strip():  # Only show non-empty lines
                print(f"{i:3d}: {repr(line)}")
        
        # Find Agreement IDs
        print("\n--- DETECTED AGREEMENT IDs AND THEIR CONTEXT ---")
        id_pattern = r'\b[A-Z0-9]{8}\b'
        
        for i, line in enumerate(lines):
            id_match = re.search(id_pattern, line)
            if id_match:
                agreement_id = id_match.group()
                print(f"\n▶ Found ID '{agreement_id}' at line {i}")
                
                # Show context (this line + next 3 lines)
                context_lines = []
                for j in range(i, min(i+4, len(lines))):
                    if lines[j].strip():
                        context_lines.append(lines[j])
                
                print("  Context:")
                for ctx_line in context_lines:
                    print(f"    {repr(ctx_line)}")
                
                # Combine context and find numbers
                context_text = ' '.join(context_lines)
                numbers = re.findall(r'\b\d{4}\b', context_text)
                print(f"  Numbers found: {numbers}")
                
                # Show what's after the 3rd number
                if len(numbers) >= 3:
                    number_positions = list(re.finditer(r'\b\d{4}\b', context_text))
                    after_third = context_text[number_positions[2].end():]
                    print(f"  Text after 3rd number: {repr(after_third.strip())}")
                
                # Check for common reason patterns
                reason_patterns = {
                    'Bank side issue': r'bank\s+side\s+issue',
                    'Signature Missing': r'signature\s+missing',
                    'Customer request': r'customer\s+request',
                }
                
                found_patterns = []
                for name, pattern in reason_patterns.items():
                    if re.search(pattern, context_text, re.IGNORECASE):
                        found_patterns.append(name)
                
                if found_patterns:
                    print(f"  Detected reason patterns: {', '.join(found_patterns)}")
                else:
                    print(f"  ⚠️  No known reason patterns detected")
        
        # Check for table structure
        print("\n--- TABLE STRUCTURE DETECTION ---")
        has_headers = False
        for line in lines:
            if re.search(r'Agreement.*Number|Penal.*Charge|Reason', line, re.IGNORECASE):
                print(f"✓ Found header: {repr(line)}")
                has_headers = True
        
        if not has_headers:
            print("⚠️  No table headers detected")
        
        # Check for footer
        print("\n--- FOOTER DETECTION ---")
        for i, line in enumerate(lines):
            if re.search(r'Thanks|Regards|Source', line, re.IGNORECASE):
                print(f"✓ Found footer at line {i}: {repr(line)}")
                break
        else:
            print("⚠️  No footer detected")


if __name__ == "__main__":
    base_path = "data/dms/01_raw_pdf"
    
    # Check if the directory exists
    if not os.path.exists(base_path):
        print(f"ERROR: Directory '{base_path}' not found!")
        print("Please make sure you're running this from the project root directory.")
        exit(1)
    
    # Find all PDFs
    pdf_files = [f for f in os.listdir(base_path) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"ERROR: No PDF files found in '{base_path}'")
        exit(1)
    
    print("\n" + "="*80)
    print("PDF OCR DIAGNOSTIC TOOL")
    print("="*80)
    print(f"\nFound {len(pdf_files)} PDF(s) to analyze:")
    for pdf in pdf_files:
        print(f"  - {pdf}")
    
    # Diagnose each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(base_path, pdf_file)
        try:
            diagnose_pdf(pdf_path)
        except Exception as e:
            print(f"\n ERROR processing {pdf_file}: {e}")
    
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Review the output above to see what OCR is reading")
    print("2. Check if 'Bank side issue' appears in the OCR output")
    print("3. If it appears, note its position relative to the numbers")
    print("4. Update your extractor.py accordingly")