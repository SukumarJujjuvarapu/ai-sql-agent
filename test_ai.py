import google.generativeai as genai
import os

# 1. SETUP: Paste your Key here
MY_API_KEY = os.getenv("GOOGLE_API_KEY", "")

genai.configure(api_key=MY_API_KEY)

# 2. MODEL: Use the standard Flash model
# This library is smarter and will find the right version automatically
model = genai.GenerativeModel('gemini-1.5-flash')

print("Contacting Gemini...")

try:
    # 3. TEST
    response = model.generate_content("Explain what SQL is in one sentence.")
    
    # 4. RESULT
    print("\n✅ Success! AI Response:")
    print(response.text)

except Exception as e:
    print(f"\n❌ Error: {e}")