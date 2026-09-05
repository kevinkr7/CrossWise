import os
from pymongo import MongoClient
from pymongo.collection import Collection
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

history_collection: Collection = db.history

class History:
    """
    History model wrapping MongoDB operations for recommendation runs.
    """
    
    @staticmethod
    def save_run(user_id: str, run_data: dict):
        """Save a new recommendation run for a user."""
        doc = {
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "top_hybrid": run_data.get("top_hybrid"),
            "top_score": run_data.get("top_score"),
            "total_pairs": run_data.get("total_pairs"),
            "results": run_data.get("results", [])
        }
        result = history_collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc
        
    @staticmethod
    def get_user_history(user_id: str, limit: int = 20):
        """Retrieve recent recommendation runs for a user, sorted newest first."""
        cursor = history_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results
        
    @staticmethod
    def clear_user_history(user_id: str):
        """Delete all recommendation history for a specific user."""
        result = history_collection.delete_many({"user_id": user_id})
        return result.deleted_count
