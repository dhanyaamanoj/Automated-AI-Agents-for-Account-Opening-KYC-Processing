from crewai.tools import BaseTool
from typing import Type, Dict, Any
from pydantic import BaseModel, Field
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import random

# Load environment variables
load_dotenv()

class AccountNumberInsertInput(BaseModel):
    """Input schema for AccountNumberInsertTool."""
    request_id: str = Field(..., description="The request ID for which the account number should be inserted.")

class AccountNumberInsertTool(BaseTool):
    name: str = "account_number_insert_tool"
    description: str = (
        "Fetches a document based on request_id from 'test_account_data' and inserts an account number into 'test_account_final'."
    )

    args_schema: Type[BaseModel] = AccountNumberInsertInput

    source_collection: str = "test_account_data"  # Source collection to fetch request details
    target_collection: str = "test_account_final"  # Target collection to insert account number

    def _run(self, request_id: str) -> Dict[str, Any]:
        uri = os.getenv("URL")  # MongoDB URL from environment variables

        try:
            # Connect to MongoDB
            client = MongoClient(uri)
            db = client["banking_ai_agent"]
            source_col = db[self.source_collection]
            target_col = db[self.target_collection]

            # Fetch document based on request_id
            document = source_col.find_one({"request_id": request_id})

            if not document:
                return {"error": f"No document found for request_id '{request_id}' in '{self.source_collection}'."}

            # Generate a random account number
            account_no = f"ACCT-{random.randint(10000000, 99999999)}"

            # Insert account number into the target collection
            update_result = target_col.update_one(
                {"request_id": request_id},
                {"$set": {"account_no": account_no}},
                upsert=True  # Insert if it doesn't exist
            )

            if update_result.modified_count > 0 or update_result.upserted_id:
                return {"success": f"Account number {account_no} inserted for request_id '{request_id}'."}
            else:
                return {"error": "Failed to insert account number."}

        except Exception as e:
            return {"error": f"Error updating data: {e}"}
