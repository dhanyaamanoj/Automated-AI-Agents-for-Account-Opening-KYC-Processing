from crewai.tools import BaseTool
import os
import base64
from PyPDF2 import PdfReader
from pymongo import MongoClient
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI

# Environment Variables
os.environ["AZURE_OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_API_KEY")
os.environ["AZURE_OPENAI_ENDPOINT"] = os.getenv("AZURE_OPENAI_ENDPOINT")

# Initialize LLM
llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_version="2024-02-15-preview",
    temperature=0,
    max_retries=2,
)

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017")
db = client["crew"]

class IdExtractionTool(BaseTool):
    name: str = "IdExtractionTool"
    description: str = "Extracts ID details from images or PDFs."
    
    # **Hardcoded file path**
    file_pathid = r"C:/Users/DHANYA MANOJ/Downloads/banking_crew_working/banking/kyc_path/Adhar Card.jpg" # Change to the actual file path

    def extract_text_from_pdf(self, file_pathid):
        """Extracts text from a PDF file."""
        text = ''
        try:
            with open(file_pathid, 'rb') as file:
                pdf_reader = PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() or ''
            print(f"Extracted Text from PDF: {text}")  # Debug print
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
        return text

    def encode_image(self, file_pathid):
        """Encodes an image file as base64."""
        try:
            with open(file_pathid, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
            print(f"Encoded image successfully: {file_pathid}")  # Debug print
            return encoded
        except Exception as e:
            print(f"Error encoding image: {e}")
            return None

    def extract_text_from_image(self, file_pathid):
        """Extracts text from an image using Azure LLM."""
        base64_image = self.encode_image(file_pathid)
        if not base64_image:
            return "Failed to encode image."

        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": "Extract all data in the image"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}
        ]

        try:
            ai_message = llm.invoke(messages)
            print(f"AI Response for Image Extraction: {ai_message.content}")  # Debug print
            return ai_message.content
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return "Failed to extract text from image."

    def extract_id_details(self, file_pathid):
        """Determines file type and extracts text accordingly."""
        print(f"Processing file: {file_pathid}")  # Debug print
        if file_pathid.endswith('.pdf'):
            return self.extract_text_from_pdf(file_pathid)
        elif file_pathid.lower().endswith(('.jpg', '.jpeg', '.png')):
            return self.extract_text_from_image(file_pathid)
        else:
            raise ValueError("Unsupported file type. Provide a PDF or image file.")

    def parse_id_details(self, extracted_text):
        """Processes extracted text using LLM for structured ID details."""
        messages = [HumanMessage(content=f"Extract structured ID details from text: {extracted_text}")]
        
        try:
            response = llm.invoke(messages)
            print(f"Parsed ID Details: {response.content}")  # Debug print
            return response.content
        except Exception as e:
            print(f"Error parsing ID details: {e}")
            return "Failed to parse ID details."

    def _run(self):
        """Runs the ID extraction tool on the hardcoded file path."""
        print(f"Starting ID extraction process for: {self.file_pathid}")  # Debug print

        if not os.path.exists(self.file_pathid):
            print(f"File does not exist: {self.file_pathid}")  # Debug print
            return "Error: File not found."

        extracted_text = self.extract_id_details(self.file_pathid)
        parsed_details = self.parse_id_details(extracted_text)

        print(f"Final Parsed Output: {parsed_details}")  # Debug print
        return parsed_details

# **Testing the Code**
if __name__ == "__main__":
    tool = IdExtractionTool()
    result = tool._run()
    print(f"Test Result: {result}")  # Final debug print
