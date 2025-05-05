import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

# LLM Configuration
LLM_CONFIG = {
    "temperature": 0.0,
    "max_tokens": 512,
    "top_p": 1,
    "stream": True,
    "stop": None,
}

# Server Configuration
HOST = "0.0.0.0"
PORT = 8000