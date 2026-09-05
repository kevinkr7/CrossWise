import os
from pymongo import MongoClient
from pymongo.collection import Collection
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from config import MONGO_URI

# Initialize MongoDB client
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_default_database()
except Exception as e:
    # Fallback to parsing DB name from URI if default is not available
    db_name = MONGO_URI.split("/")[-1].split("?")[0]
    if not db_name:
        db_name = "hybrid_crop"
    db = client[db_name]

users_collection: Collection = db.users

class User:
    """
    User model wrapping MongoDB operations.
    """
    
    @staticmethod
    def create(name, email, password, is_admin=False):
        """Create a new user with hashed password."""
        if users_collection.find_one({"email": email.lower()}):
            raise ValueError("User with this email already exists.")
            
        user_doc = {
            "name": name.strip(),
            "email": email.lower().strip(),
            "password_hash": generate_password_hash(password),
            "created_at": datetime.datetime.utcnow(),
            "is_admin": is_admin
        }
        
        result = users_collection.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        return user_doc
        
    @staticmethod
    def find_by_email(email):
        """Find a user by email."""
        return users_collection.find_one({"email": email.lower().strip()})
        
    @staticmethod
    def verify_password(password_hash, password):
        """Verify a password against its hash."""
        return check_password_hash(password_hash, password)
