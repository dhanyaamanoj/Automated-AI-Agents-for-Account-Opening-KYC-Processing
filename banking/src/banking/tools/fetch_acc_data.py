from crewai.tools import BaseTool

from typing import Type, List, Dict, Any

from pydantic import BaseModel, Field

from pymongo import MongoClient

from dotenv import load_dotenv

import os



load_dotenv()



class RequestDetailsInput(BaseModel):

    """Input schema for FetchDataTool."""

    request_id: str = Field(..., description="The claim_id to fetch all related data.")



class RequestDetailsTool(BaseTool):
    name: str = "fetch_data_tool"
    description: str = (
        "Fetches all documents from the 'claim_final' collection "
        "in the 'insurance_ai_agent' database based on a given claim_id."
    )

    args_schema: Type[BaseModel] = RequestDetailsInput

    collection_name: str = "test_account_data"  # Default collection name



    def _run(self, request_id: str) -> List[Dict[str, Any]]:

        uri = os.getenv("URL")

        try:

            client = MongoClient(uri)

            db = client['banking_ai_agent']

            collection = db[self.collection_name]



            # Fetch all documents matching the given claim_id

            document = collection.find_one({"request_id": request_id})



            if document:

                # Remove '_id' field for clean output

                document.pop('_id', None)

                return document

            else:

                return [{"error": f"No documents found for claim_id '{request_id}' in '{self.collection_name}'."}]

        except Exception as e:

            return [{"error": f"Error fetching data: {e}"}]





# Example usage:

# request_id = 'REQ000008' # Replace with an actual claim_id
# fetch_tool = RequestDetailsTool()
# fetched_data = fetch_tool._run(request_id)
# print(fetched_data)