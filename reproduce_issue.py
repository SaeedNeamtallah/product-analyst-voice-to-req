import os
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
    # Try to read from config.py default if not in env
    try:
        from backend.config import settings
        api_key = settings.gemini_api_key
        print(f"Using API key from settings: {api_key[:5]}...")
    except ImportError:
        print("Could not import settings to fallback.")
        exit(1)

genai.configure(api_key=api_key)

async def test_model(model_name):
    print(f"Testing model: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        # Run in executor to match provider implementation behavior, though simple generate is sync-ish in some versions
        # but let's just call it directly for simplicity of the script
        response = model.generate_content("Hello")
        print(f"Success! Response: {response.text}")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

async def main():
    print("--- Reproducing Issue ---")
    await test_model("gemma-3-12b-it")

    print("\n--- Verifying Fix ---")
    await test_model("gemma-3-12b-it")

if __name__ == "__main__":
    asyncio.run(main())
