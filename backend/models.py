# backend/models.py
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env if it exists

# 1️⃣  use the Atlas string from .env (fallback = localhost)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = os.getenv("DATABASE_NAME", "akshayDB")

client = MongoClient(
    MONGO_URI,
    server_api=ServerApi('1')
)

# quick ping
try:
    client.admin.command('ping')
    print("✅  MongoDB reachable:", MONGO_URI.split('@')[-1].split('/')[0])
except Exception as e:
    print("❌  MongoDB connection failed:", e)
    raise

db = client[DB_NAME]
users         = db["users"]
prescriptions = db["prescriptions"]
alarms        = db["alarms"]
# --------------------  your existing classes  --------------------
class User:
    @staticmethod
    def create(name, email, password_hash, guardian_name, guardian_whatsapp):
        doc = {
            "name": name,
            "email": email,
            "password": password_hash,
            "guardian_name": guardian_name,
            "guardian_whatsapp": guardian_whatsapp,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        return str(db.users.insert_one(doc).inserted_id)

    @staticmethod
    def find_by_email(email):
        return db.users.find_one({"email": email})

    @staticmethod
    def list_all():
        return list(db.users.find({}))


class Prescription:
    @staticmethod
    def create(user_id, filename: str, raw_text: str, ner: dict):
        doc = {
            "user_id": user_id,
            "filename": filename,
            "raw_text": raw_text,
            "ner": ner,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return db.prescriptions.insert_one(doc).inserted_id

    @staticmethod
    def list_all():
        return list(db.prescriptions.find({}))