import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from datetime import datetime
import logging

load_dotenv()  # reads .env if it exists

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1️⃣  use the Atlas string from .env (fallback = localhost)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DATABASE_NAME", "akshayDB")

class Database:
    _instance = None

    @staticmethod
    def get_client():
        if Database._instance is None:
            Database._instance = MongoClient(
                MONGO_URI,
                server_api=ServerApi('1')
            )
            try:
                Database._instance.admin.command('ping')
                logger.info("✅  MongoDB reachable: %s", MONGO_URI.split('@')[-1].split('/')[0])
            except Exception as e:
                logger.error("❌  MongoDB connection failed: %s", e)
                raise
        return Database._instance

client = Database.get_client()
db = client[DB_NAME]
users = db["users"]
prescriptions = db["prescriptions"]
alarms = db["alarms"]

class User:
    """
    Represents a User in the database.
    """

    @staticmethod
    def create(name, email, password_hash, guardian_name, guardian_whatsapp):
        """
        Creates a new user in the database.

        Args:
            name (str): The user's name.
            email (str): The user's email.
            password_hash (str): The user's password hash.
            guardian_name (str): The guardian's name.
            guardian_whatsapp (str): The guardian's WhatsApp number.

        Returns:
            str: The ID of the newly created user.
        """
        doc = {
            "name": name,
            "email": email,
            "password": password_hash,
            "guardian_name": guardian_name,
            "guardian_whatsapp": guardian_whatsapp,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        return str(users.insert_one(doc).inserted_id)

    @staticmethod
    def find_by_email(email):
        """
        Finds a user by their email.

        Args:
            email (str): The user's email.

        Returns:
            dict: The user document if found, otherwise None.
        """
        return users.find_one({"email": email})

    @staticmethod
    def list_all():
        """
        Lists all users.

        Returns:
            list: A list of all user documents.
        """
        return list(users.find({}))

    @staticmethod
    def update(user_id, updates):
        """
        Updates a user document.

        Args:
            user_id (str): The ID of the user to update.
            updates (dict): The updates to apply.

        Returns:
            dict: The result of the update operation.
        """
        return users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})

    @staticmethod
    def delete(user_id):
        """
        Deletes a user document.

        Args:
            user_id (str): The ID of the user to delete.

        Returns:
            dict: The result of the delete operation.
        """
        return users.delete_one({"_id": ObjectId(user_id)})


class Prescription:
    """
    Represents a Prescription in the database.
    """

    @staticmethod
    def create(user_id, filename: str, raw_text: str, ner: dict):
        """
        Creates a new prescription in the database.

        Args:
            user_id (str): The ID of the user who owns the prescription.
            filename (str): The filename associated with the prescription.
            raw_text (str): The raw text of the prescription.
            ner (dict): The named entity recognition results.

        Returns:
            ObjectId: The ID of the newly created prescription.
        """
        doc = {
            "user_id": user_id,
            "filename": filename,
            "raw_text": raw_text,
            "ner": ner,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return prescriptions.insert_one(doc).inserted_id

    @staticmethod
    def list_all():
        """
        Lists all prescriptions.

        Returns:
            list: A list of all prescription documents.
        """
        return list(prescriptions.find({}))