import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "walk")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")

# Pipeline configuration
PIPELINE_STAGES = [
    "requirements_gathering",
    "knowledge_gathering",
    "implementation_planning",
    "implementation_writing",
    "review",
]

# Vector search configuration
VECTOR_SIMILARITY_THRESHOLD = float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.7"))
MAX_CONTEXT_ITEMS = int(os.getenv("MAX_CONTEXT_ITEMS", "10"))