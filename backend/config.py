import os

from dotenv import load_dotenv

load_dotenv()

AZURE_AI_PROJECT_ENDPOINT: str = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
AZURE_AI_MODEL_DEPLOYMENT_NAME: str = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]

COSMOS_ENDPOINT: str = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY: str = os.environ["COSMOS_KEY"]
COSMOS_DATABASE_NAME: str = os.environ["COSMOS_DATABASE_NAME"]
COSMOS_CONTAINER_NAME: str = os.environ["COSMOS_CONTAINER_NAME"]
