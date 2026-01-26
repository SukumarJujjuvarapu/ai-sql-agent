import os
from google import genai

# Set GOOGLE_API_KEY in environment
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))

print("Checking available models...")
try:
    # The new library uses .display_name or .name
    for m in client.models.list():
        print(f" - {m.name}")
except Exception as e:
    print(f"Error: {e}")