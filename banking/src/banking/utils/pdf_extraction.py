import os
import json
import io
import boto3
import pytesseract
import re
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import trp.trp2 as t2
from PIL import Image

# Load environment variables
load_dotenv()
region_name = os.getenv('AWS_REGION_NAME')
access_key = os.getenv('ACCESS_KEY')
secret_key = os.getenv('SECRET_ACCESS_KEY')
POPPLER_PATH = os.getenv('POPPLER_PATH')
TESSERACT_PATH = os.getenv('TESSERACT_PATH')

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def read_img_pdf(filepath):
    """Extracts image bytes from a PDF or image file."""
    try:
        if filepath.endswith('.pdf'):
            images = convert_from_path(filepath, dpi=200, poppler_path=POPPLER_PATH)
            if images:
                with io.BytesIO() as output:
                    images[0].save(output, format="JPEG")
                    return output.getvalue()
        elif filepath.endswith(('.png', '.jpg', '.jpeg')):
            with open(filepath, 'rb') as img_file:
                return img_file.read()
    except Exception as e:
        print(f"Error processing {filepath}: {str(e)}")
        return None
    return None

def analyze_document(image_bytes, query_list, quest_dict):
    """Uses AWS Textract for primary extraction, with OCR fallback for missing values."""
    textract_client = boto3.client(
        'textract',
        region_name=region_name,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    try:
        response = textract_client.analyze_document(
            Document={'Bytes': image_bytes},
            FeatureTypes=["QUERIES"],
            QueriesConfig={"Queries": query_list}
        )

        extracted_info = extract_query_info(response, quest_dict)

        # Fallback to OCR if DOB or Address is missing
        if not extracted_info.get("DATE OF BIRTH") or not extracted_info.get("ADDRESS"):
            ocr_data = extract_with_ocr(image_bytes)
            extracted_info.update({k: v for k, v in ocr_data.items() if v})

        return extracted_info
    except Exception as e:
        print(f"Error analyzing document: {str(e)}")
        return {"error": "AWS Textract failed"}

def extract_query_info(response, quest_dict):
    """Extracts key-value pairs from Textract response."""
    query_dict = {}
    try:
        doc = t2.TDocumentSchema().load(response)
        page = doc.pages[0]
        query_answers = doc.get_query_answers(page=page)

        for answers in query_answers:
            key_ = quest_dict.get(answers[0], answers[0])  # Default to question text if no match
            query_dict[key_] = answers[-1]
    except Exception as e:
        print(f"Error extracting query info: {str(e)}")
        return {"error": "Failed to extract query info"}

    return query_dict

def extract_with_ocr(image_bytes):
    """Fallback OCR extraction using Tesseract"""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)

        dob = None
        address = None

        # Regex pattern for DOB (Adjust based on Aadhaar format)
        dob_pattern = r"\b(\d{2}/\d{2}/\d{4})\b"
        match = re.search(dob_pattern, text)
        if match:
            dob = match.group(1)

        # Extract address by looking for "Address" keyword
        address_start = text.find("Address")
        if address_start != -1:
            address = text[address_start:].split("\n", 1)[-1].strip()

        return {"DATE OF BIRTH": dob, "ADDRESS": address}
    except Exception as e:
        print(f"Error extracting OCR data: {str(e)}")
        return {"error": "OCR extraction failed"}
    
def aadhaar_queries():
    """Defines queries for extracting Aadhaar details."""
    query_list = [
        {"Text": "What is the Aadhaar number?"},
        {"Text": "What is the name of the Aadhaar cardholder?"},
        {"Text": "What is the date of birth?"},
        {"Text": "What is the DOB?"},
        {"Text": "What is the birth date?"},
        {"Text": "What is the gender?"},
        {"Text": "What is full address?"}
    ]

    quest_dict = {
        "What is the Aadhaar number?": "AADHAAR NUMBER",
        "What is the name of the Aadhaar cardholder?": "NAME",
        "What is the date of birth?": "DATE OF BIRTH",
        "What is the DOB?": "DATE OF BIRTH",
        "What is the birth date?": "DATE OF BIRTH",
        "What is the gender?": "GENDER",
        "What is full address?": "ADDRESS"
    }

    return {"query_list": query_list, "quest_dict": quest_dict}

def process_folder(folder_path, output_path):
    """Processes all documents in a folder, extracts Aadhaar details, and saves to JSON."""
    extracted_data = {}
    queries = aadhaar_queries()
    query_list = queries["query_list"]
    quest_dict = queries["quest_dict"]

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
            try:
                img_bytes = read_img_pdf(file_path)
                if img_bytes:
                    extracted_info = analyze_document(img_bytes, query_list, quest_dict)
                    extracted_data[file_name] = extracted_info
                else:
                    extracted_data[file_name] = {"error": "Unsupported file format or unable to process"}
            except Exception as e:
                extracted_data[file_name] = {"error": str(e)}

    # Save extracted data as JSON
    save_json(extracted_data, output_path)
    
    # Print extracted data in a readable format
    print(json.dumps(extracted_data, indent=4))
    return extracted_data

    print(f"Extracted data saved to: {output_path}")
    return extracted_data

def save_json(data, output_path):
    """Saves extracted data as JSON in the specified output path."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        print(f"JSON file successfully saved: {output_path}")
    except Exception as e:
        print(f"Error saving JSON file: {str(e)}")

# Define paths
folder_path = r"C:\Users\DHANYA MANOJ\Downloads\banking_crew_working\banking\local_id_path"
output_json_path = r"C:\Users\DHANYA MANOJ\Downloads\banking_crew_working\banking\output\extracted_data.json"

# Process documents and save JSON
process_folder(folder_path, output_json_path)
