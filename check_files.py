import os

folder = r"C:\Users\Sukku\OneDrive\Desktop\P1"
print(f"📂 Scanning folder: {folder}\n")

found_db = False

# Loop through all files in the folder
for filename in os.listdir(folder):
    # Check if it looks like a database file
    if filename.endswith(".db") or filename.endswith(".sqlite"):
        filepath = os.path.join(folder, filename)
        size = os.path.getsize(filepath)
        
        print(f"Found: {filename}")
        print(f"   Size: {size / 1024:.2f} KB")
        
        if size < 5:
            print("   ⚠️  WARNING: This file is empty! (This is the ghost)")
        else:
            print("   ✅  SUCCESS: This looks like the real database!")
            found_db = True
            
if not found_db:
    print("\n❌ No database files found. Check if the file is zipped or named differently.")