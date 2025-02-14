#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from banking.crew import Banking
from typing import Type
from pymongo import MongoClient
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import json
import os


import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

mongo_connection_string=os.getenv("URL")
database_name=os.getenv("DB")
collection_name=os.getenv("COLLECTION1")
# openai_api_key = os.getenv("OPENAI_API_KEY")

def run():
    """
    Run the crew.
    """
    client = MongoClient(mongo_connection_string)
    db = client[database_name]
    coll = db[collection_name]

    for doc in coll.find({"status_flag": False, "account_id": None}, {"_id": 0}):
        request_id = doc.get("request_id")  
        #print(f"Request ID: {request_id}")
    
    inputs = {
        'request_id': request_id
    }

    Banking().crew().kickoff(inputs=inputs)

def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs"
    }
    try:
        Banking().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        Banking().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs"
    }
    try:
        Banking().crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")
    



