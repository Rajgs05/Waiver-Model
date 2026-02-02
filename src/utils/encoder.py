import base64
import os

def encode_all_raw_to_base64():
    """
    Scans the shared raw_files folder and encodes everything into the data directory.
    """
    input_folder = "raw_files"
    output_dir = "data/02_base64_encoded"
    
    # Ensure folders exist
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    files = [f for f in os.listdir(input_folder) if f.endswith('.pdf')]
    print(f"--- Found {len(files)} new PDFs to encode ---")

    for file_name in files:
        input_path = os.path.join(input_folder, file_name)
        output_path = os.path.join(output_dir, file_name.replace('.pdf', '.txt'))
        
        try:
            with open(input_path, "rb") as pdf_file:
                encoded_string = base64.b64encode(pdf_file.read()).decode('utf-8')
                
            with open(output_path, "w") as text_file:
                text_file.write(encoded_string)
            
            print(f"Successfully encoded: {file_name}")
        except Exception as e:
            print(f"Error encoding {file_name}: {e}")

if __name__ == "__main__":
    encode_all_raw_to_base64()