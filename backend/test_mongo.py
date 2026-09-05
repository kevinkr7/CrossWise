import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("❌ Error: MONGO_URI is not set in your .env file!")
    exit(1)

print(f"Attempting to connect to: {MONGO_URI.split('@')[-1] if '@' in MONGO_URI else 'Local MongoDB'}")

try:
    # Set a short timeout (5 seconds) so it doesn't hang forever if it fails
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # The ismaster command is cheap and does not require auth.
    client.admin.command('ismaster')
    
    print("✅ SUCCESS! Connected to MongoDB Atlas successfully.")
except Exception as e:
    print("❌ FAILED to connect to MongoDB Atlas.")
    print("Error Details:", str(e))
