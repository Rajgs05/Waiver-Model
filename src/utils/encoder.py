import base64
import os

def encode_pdf_to_base64(file_name):
    input_path = f"data/dms/01_raw_pdf/{file_name}"
    output_path = f"data/dms/02_base64_encoded/{file_name.replace('.pdf', '.txt')}"
    
    with open(input_path, "rb") as pdf_file:
        encoded_string = base64.b64encode(pdf_file.read()).decode('utf-8')
        
    with open(output_path, "w") as text_file:
        text_file.write(encoded_string)
    
    return output_path