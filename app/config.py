import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
API_KEY = os.getenv("API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

# Path to save processed files temporarily
TEMP_FOLDER = "temp_folder"
os.makedirs(TEMP_FOLDER, exist_ok=True)
