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
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# MongoDB connection
mongo_client = MongoClient(os.getenv("URL"))
db = mongo_client["banking_ai_agent"]
collection = db["test_enquiry_documents"]  # Collection storing document paths

# S3 Configuration
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)
s3_bucket = os.getenv("BUCKET_NAME")

# AWS Textract Region
region_name = os.getenv("AWS_REGION_NAME")

# Paths for processing
POPPLER_PATH = os.getenv("POPPLER_PATH")
TESSERACT_PATH = os.getenv("TESSERACT_PATH")

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


class DocumentExtractionInput(BaseModel):
    """Input schema for AadhaarExtractionTool."""
    request_id: str = Field(..., description="Request ID to fetch document path from MongoDB.")
    output_path: str = Field(..., description="Path where extracted data JSON should be saved.")


class DocumentExtractionTool(BaseTool):
    """Tool for extracting Aadhaar details from documents using AWS Textract & OCR."""

    name: str = "Aadhaar Extraction Tool"
    description: str = (
        "Fetches Aadhaar documents from MongoDB based on request_id, downloads them from S3, "
        "and extracts Aadhaar details using AWS Textract and OCR."
    )
    args_schema: Type[BaseModel] = DocumentExtractionInput

    def _run(self, request_id: str, output_path: str = None) -> str:
        """Fetch document path from MongoDB, download from S3, extract Aadhaar details, and save back to MongoDB."""
        file_path = self.fetch_document_from_mongo(request_id)
        if not file_path:
            return json.dumps({"error": f"No document found for request_id: {request_id}"})

        # Download from S3
        local_file_path = self.download_from_s3(file_path)
        if not local_file_path:
            return json.dumps({"error": "Failed to download file from S3"})

        # Process document
        extracted_data = self.process_document(local_file_path)

        # Save extracted data to MongoDB
        self.save_to_mongo(request_id, extracted_data)

        return json.dumps({"message": "Extracted details saved to MongoDB", "request_id": request_id}, indent=4)

    

        

    def fetch_document_from_mongo(self, request_id: str) -> str:
        """Fetches the document path from MongoDB based on request_id."""
        document = collection.find_one({"request_id": request_id}, {"Document_Path": 1})
        if document and "Document_Path" in document:
            return document["Document_Path"]
        return ""

    def download_from_s3(self, s3_full_path: str) -> str:
        """Downloads the file from S3 to a temporary directory."""
        try:
            s3_key = s3_full_path.replace(f"s3://{s3_bucket}/", "", 1)
            temp_file_path = os.path.join(os.getcwd(), os.path.basename(s3_key))
            s3_client.download_file(s3_bucket, s3_key, temp_file_path)
            return temp_file_path
        except Exception as e:
            print(f"Error downloading file from S3: {e}")
            return ""

    def process_document(self, file_path: str) -> dict:
        """Extracts Aadhaar details from the document."""
        img_bytes = self.read_img_pdf(file_path)
        if not img_bytes:
            return {"error": "Invalid file format or unable to process"}

        queries = self.aadhaar_queries()
        extracted_info = self.analyze_document(img_bytes, queries["query_list"], queries["quest_dict"])

        if not extracted_info.get("DATE OF BIRTH") or not extracted_info.get("ADDRESS"):
            ocr_data = self.extract_with_ocr(img_bytes)
            extracted_info.update({k: v for k, v in ocr_data.items() if v})

        return extracted_info

    def read_img_pdf(self, filepath):
        """Extracts image bytes from a PDF or image file."""
        try:
            if filepath.endswith(".pdf"):
                images = convert_from_path(filepath, dpi=200, poppler_path=POPPLER_PATH)
                if images:
                    with io.BytesIO() as output:
                        images[0].save(output, format="JPEG")
                        return output.getvalue()
            elif filepath.endswith((".png", ".jpg", ".jpeg")):
                with open(filepath, "rb") as img_file:
                    return img_file.read()
        except Exception as e:
            print(f"Error processing {filepath}: {str(e)}")
            return None
        return None

    def analyze_document(self, image_bytes, query_list, quest_dict):
        """Uses AWS Textract for extraction with OCR fallback."""
        textract_client = boto3.client(
            "textract",
            region_name=region_name,
            aws_access_key_id=os.getenv("ACCESS_KEY"),
            aws_secret_access_key=os.getenv("SECRET_ACCESS_KEY"),
        )

        try:
            response = textract_client.analyze_document(
                Document={"Bytes": image_bytes},
                FeatureTypes=["QUERIES"],
                QueriesConfig={"Queries": query_list},
            )

            return self.extract_query_info(response, quest_dict)
        except Exception as e:
            print(f"Error analyzing document: {str(e)}")
            return {"error": "AWS Textract failed"}

    def extract_query_info(self, response, quest_dict):
        """Extracts key-value pairs from Textract response."""
        query_dict = {}
        try:
            doc = t2.TDocumentSchema().load(response)
            page = doc.pages[0]
            query_answers = doc.get_query_answers(page=page)

            for answers in query_answers:
                key_ = quest_dict.get(answers[0], answers[0])
                query_dict[key_] = answers[-1]
        except Exception as e:
            print(f"Error extracting query info: {str(e)}")
            return {"error": "Failed to extract query info"}
        return query_dict

    def extract_with_ocr(self, image_bytes):
        """Fallback OCR extraction using Tesseract."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)

            dob_pattern = r"\b(\d{2}/\d{2}/\d{4})\b"
            dob_match = re.search(dob_pattern, text)
            dob = dob_match.group(1) if dob_match else None

            address_start = text.find("Address")
            address = text[address_start:].split("\n", 1)[-1].strip() if address_start != -1 else None

            return {"DATE OF BIRTH": dob, "ADDRESS": address}
        except Exception as e:
            print(f"Error extracting OCR data: {str(e)}")
            return {"error": "OCR extraction failed"}
        
    def save_to_mongo(self, request_id, extracted_data):
        """Saves extracted Aadhaar details back to MongoDB under 'Extracted_Details'."""
        try:
            result = collection.update_one(
                {"request_id": request_id},  # Find the document by request_id
                {"$set": {"Extracted_Details": extracted_data}} ,
                 upsert=True 
            )

            if result.modified_count > 0:
                print(f"✅ Successfully updated MongoDB for request_id: {request_id}")
            else:
                print(f"⚠️ No document updated. Check if request_id '{request_id}' exists.")
        
        except Exception as e:
            print(f"❌ Error saving extracted data to MongoDB: {str(e)}")


    def aadhaar_queries(self):
        """Defines queries for extracting Aadhaar details."""
        query_list = [
            {"Text": "What is the Aadhaar number?"},
            {"Text": "What is the name of the Aadhaar cardholder?"},
            {"Text": "What is the date of birth?"},
            {"Text": "What is the gender?"},
            {"Text": "What is full address?"}
        ]
        quest_dict = {
            "What is the Aadhaar number?": "AADHAAR NUMBER",
            "What is the name of the Aadhaar cardholder?": "NAME",
            "What is the date of birth?": "DATE OF BIRTH",
            "What is the gender?": "GENDER",
            "What is full address?": "ADDRESS"
        }
        return {"query_list": query_list, "quest_dict": quest_dict}



# test_input = AadhaarExtractionInput(
#     request_id="REQ000008"  # Replace with an actual request_id from MongoDB
# )

# # Instantiate the tool
# aadhaar_tool = AadhaarExtractionTool()

# # Run the tool with test input
# result_json = aadhaar_tool._run(test_input.request_id)

# # Print output
# print("MongoDB Update Status:\n", json.loads(result_json))