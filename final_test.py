from google import genai
import os

# --- PASTE YOUR NEW KEY HERE ---
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))

print("Attempting to connect to Gemini 1.5 Flash...")

try:
    # We explicitly use the specific stable version to avoid "Not Found" errors
    response = client.models.generate_content(
        model="gemini-1.5-flash-002", 
        contents="Explain what SQL is in one sentence."
    )
    print("\n✅ SUCCESS! The AI is working.")
    print(f"Response: {response.text}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    
    # If that failed, try the generic name as a backup
    try:
        print("\nTrying backup model...")
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents="Explain what SQL is."
        )
        print("\n✅ SUCCESS (Backup worked)!")
        print(f"Response: {response.text}")
    except Exception as e2:
        print(f"❌ Backup failed too: {e2}")