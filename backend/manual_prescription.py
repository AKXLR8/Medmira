# backend/manual_prescription.py
from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from backend.models import db   # gives you the Mongo handle

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
    token = request.headers.get("Authorization","").replace("Bearer ","").strip()
    if not token or not ObjectId.is_valid(token):
        return jsonify({"error": "Invalid token"}), 401

    data = request.get_json(force=True)
    doc = {
        "user_id"     : token,                # we store the raw string _id
        "medicine_name": data.get("medicine_name"),
        "dosage"      : data.get("dosage"),
        "frequency"   : data.get("frequency"),
        "duration"    : data.get("duration"),
        "source"      : "manual",
        "created_at"  : datetime.utcnow().isoformat() + "Z"
    }
    try:
        res = db.prescriptions.insert_one(doc)
        return jsonify({"prescription_id": str(res.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500