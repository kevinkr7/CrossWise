from pymongo import MongoClient
import sys

# Import config assuming it's run from the backend directory
try:
    from config import MONGO_URI
except ImportError:
    print("Error: Could not import config. Make sure you run this from the backend/ directory.")
    sys.exit(1)

def promote_to_admin(email):
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()
    except Exception as e:
        db_name = MONGO_URI.split("/")[-1].split("?")[0]
        if not db_name:
            db_name = "hybrid_crop"
        db = client[db_name]

    result = db.users.update_one(
        {"email": email.lower().strip()},
        {"$set": {"is_admin": True}}
    )

    if result.matched_count > 0:
        if result.modified_count > 0:
            print(f"Successfully promoted {email} to admin!")
        else:
            print(f"User {email} is already an admin.")
    else:
        print(f"Error: User with email '{email}' not found.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python promote_admin.py <user_email>")
        sys.exit(1)
    
    promote_to_admin(sys.argv[1])
