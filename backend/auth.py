
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from backend.mongo_atlas import User
from src.mongo_client import users_collection,db
import datetime
from backend.mongo_atlas import User
from backend.alarm import send_guardian_welcome
from bson import ObjectId

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

users_collection = db["users"]

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

from backend.mongo_atlas import db   # Mongo handle

pres_bp = Blueprint("prescription", __name__, url_prefix="/api")

# -------------  NEW  -------------
@pres_bp.get("/prescriptions")
def get_my_prescriptions():
    """
    Header:  Authorization: Bearer <user_id>
    Returns: list[PrescriptionDto]
    """
    token = request.headers.get("Authorization","").replace("Bearer","").strip()
    if not ObjectId.is_valid(token):
        return jsonify({"error": "Invalid token"}), 401

    docs = list(db.prescriptions.find(
        {"user_id": token},           # string _id you stored
        {"_id": 1, "medicine_name": 1, "dosage": 1,
         "frequency": 1, "duration": 1, "source": 1,"ner_dict": 1, "created_at": 1}
    ).sort("created_at", -1))

    # ObjectId → string
    for d in docs:
        d["id"] = str(d.pop("_id"))

    return jsonify(docs), 200

@auth_bp.post("/register")
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    guardian_name = data.get("guardian_name")
    guardian_whatsapp = data.get("guardian_whatsapp")

    if not name or not email or not password:
        return {"error": "Missing required fields"}, 400

    if User.find_by_email(email):
        return {"error": "Email already registered"}, 400

    user_id = User.create(
        name,
        email,
        generate_password_hash(password),
        guardian_name,
        guardian_whatsapp,
    )

#whatsapp
    
    send_guardian_welcome(guardian_whatsapp, name)

    return {
        "user_id": user_id,
        "message": "✅ User registered successfully"
    }, 201

#login
@auth_bp.post("/login")
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user_doc = users_collection.find_one({"email": email})
    if not user_doc or not check_password_hash(user_doc["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "message": "Login successful",
        "token": str(user_doc["_id"])  # mock token
    }), 200

