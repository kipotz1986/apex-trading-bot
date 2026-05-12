import os
import google.generativeai as genai
from dotenv import load_dotenv

def check_gemini_key():
    # 1. Load API Key from .env or prompt user
    load_dotenv()
    api_key = os.getenv("AI_API_KEY")
    
    if not api_key or api_key == "your_google_api_key":
        print("❌ Error: AI_API_KEY not found in .env file.")
        api_key = input("Please enter your Gemini API Key to test: ").strip()

    if not api_key:
        print("❌ No API key provided. Exiting.")
        return

    print(f"--- Testing Gemini API Key ---")
    
    try:
        # 2. Configure the SDK
        genai.configure(api_key=api_key)
        
        # 3. List available models (quickest way to verify key without spending tokens)
        print("🔄 Verifying connection...")
        models = genai.list_models()
        print("Available models:")
        for m in models:
            print(f" - {m.name}")
        
        # 4. Attempt a simple generation
        model = genai.GenerativeModel("gemini-2.0-flash")
        print("🔄 Testing text generation...")
        response = model.generate_content("Say 'API Key is Valid' in 3 words.")
        
        print(f"\n✅ SUCCESS!")
        print(f"Response: {response.text.strip()}")
        print(f"--- Verification Complete ---")

    except Exception as e:
        print(f"\n❌ FAILED!")
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "400" in error_msg:
            print("Reason: The API key provided is invalid.")
        elif "quota" in error_msg.lower() or "429" in error_msg:
            print("Reason: API quota exceeded or rate limited.")
        else:
            print(f"Reason: {error_msg}")
        print(f"-----------------------------")

if __name__ == "__main__":
    check_gemini_key()
