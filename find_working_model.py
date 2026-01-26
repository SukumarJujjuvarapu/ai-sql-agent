import google.generativeai as genai
import os

# --- PASTE YOUR KEY HERE ---
MY_API_KEY = "AIzaSyAYF0PvO484gPU5KLRG2-1NB31FML0U8eg"
genai.configure(api_key=MY_API_KEY)

# List of all common model names to try
candidate_models = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
    "gemini-1.5-pro-002",
    "gemini-2.0-flash-exp",
    "gemini-1.0-pro",
    "gemini-pro"
]

print("🔎 Testing models to find one that works for you...\n")

for model_name in candidate_models:
    try:
        print(f"Testing: {model_name}...", end=" ")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello.")
        
        # If we get here, it worked!
        print("✅ SUCCESS!")
        print(f"\n🎉 WE FOUND A WORKING MODEL: {model_name}")
        print(f"AI Said: {response.text}")
        break  # Stop checking
    except Exception as e:
        # If it fails, just print a small x and continue
        if "404" in str(e) or "not found" in str(e).lower():
            print("❌ (Not Found)")
        else:
            print(f"❌ Error: {e}")

print("\n--- Test Complete ---")