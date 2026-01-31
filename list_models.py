import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    try:
        from backend.config import settings
        api_key = settings.gemini_api_key
        print(f"Using API key from settings")
    except ImportError:
        print("Could not find API key.")
        exit(1)

genai.configure(api_key=api_key)

print("Listing available models...")
try:
    for m in genai.list_models():
        print(f"Name: {m.name}, Supported Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
