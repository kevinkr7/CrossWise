from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import logging

from models.user import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "Missing name, email, or password"}), 400

    try:
        user_doc = User.create(name=name, email=email, password=password)
        
        # Issue token immediately upon registration
        access_token = create_access_token(identity=str(user_doc["_id"]))
        
        return jsonify({
            "status": "success",
            "message": "User registered successfully",
            "access_token": access_token,
            "user": {
                "id": str(user_doc["_id"]),
                "name": user_doc["name"],
                "email": user_doc["email"],
                "is_admin": user_doc.get("is_admin", False)
            }
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error("Registration error: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user_doc = User.find_by_email(email)
    
    if not user_doc or not User.verify_password(user_doc["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = create_access_token(identity=str(user_doc["_id"]))
    
    return jsonify({
        "status": "success",
        "access_token": access_token,
        "user": {
            "id": str(user_doc["_id"]),
            "name": user_doc["name"],
            "email": user_doc["email"],
            "is_admin": user_doc.get("is_admin", False)
        }
    }), 200

@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required()
def get_current_user():
    current_user_id = get_jwt_identity()
    # In a full app you might look up the user in DB again to ensure they still exist, 
    # but for simplicity we return the ID.
    return jsonify({
        "status": "success",
        "user_id": current_user_id
    }), 200
