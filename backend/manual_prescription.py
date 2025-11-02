from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from backend.mongo_atlas import db

manual_bp = Blueprint("manual", __name__, url_prefix="/api")

@manual_bp.post("/manual-prescription")
def add_manual_prescription():
    """
    Expects JSON:
    {
      "medicineName": "Dolo 650",
      "dosage":       "650 mg",
      "frequency":    "Twice daily",
      "duration":     "5 days"
    }
    Auth header:  Bearer <token>  (token == user _id for now)
    """
    # Extract and validate the token from the Authorization header
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token or not ObjectId.is_valid(token):
        return jsonify({"error": "Invalid token"}), 401

    # Get the JSON data from the request
    data = request.get_json(force=True)

    # Validate the presence of required fields
    required_fields = ["medicine_name", "dosage", "frequency", "duration"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Create the prescription document
    doc = {
        "user_id": token,
        "medicine_name": data["medicine_name"],
        "dosage": data["dosage"],
        "frequency": data["frequency"],
        "duration": data["duration"],
        "source": "manual",
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    # Attempt to insert the document into the database
    try:
        res = db.prescriptions.insert_one(doc)
        return jsonify({"prescription_id": str(res.inserted_id)}), 201
    except Exception as e:
        # Log the exception for debugging purposes
        print(f"Error inserting prescription: {e}")
        return jsonify({"error": "Failed to create prescription"}), 500