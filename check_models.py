from google import genai

# Paste your key here again
client = genai.Client(api_key="AIzaSyAYF0PvO484gPU5KLRG2-1NB31FML0U8eg")

print("Checking available models...")
try:
    # The new library uses .display_name or .name
    for m in client.models.list():
        print(f" - {m.name}")
except Exception as e:
    print(f"Error: {e}")