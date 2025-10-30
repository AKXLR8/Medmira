import os
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from bson import ObjectId
from pathlib import Path
from config.config import Config

logger = logging.getLogger(__name__)


class MongoDBClient:
    def __init__(self, retries: int = 5, delay: int = 5):
        """Initialize MongoDB connection with retries"""
        mongo_url = os.getenv("MONGO_URI", Config.MONGO_URL)
        db_name = os.getenv("MONGO_DB", Config.DATABASE_NAME)

        for attempt in range(1, retries + 1):
            try:
                self.client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
                self.db = self.client[db_name]

                # Separate collections
                self.collection = self.db["prescriptions"]
                self.users_collection = self.db["users"]

                # Create indexes
                self._create_prescription_indexes()
                self._create_user_indexes()

                # Test connection
                self.client.admin.command("ping")
                logger.info(f"MongoDB connected successfully to {mongo_url}/{db_name}")
                break
            except ConnectionFailure as e:
                logger.warning(f"MongoDB connection attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(delay)
                else:
                    logger.error("Exceeded maximum retries for MongoDB connection")
                    raise
            except Exception as e:
                logger.error(f"MongoDB initialization error: {str(e)}")
                raise

    def _create_prescription_indexes(self):
        try:
            self.collection.create_index([("parsed_at", DESCENDING)])
            self.collection.create_index([("prescription_date", DESCENDING)])
            self.collection.create_index([("doctor_name", ASCENDING)])
            self.collection.create_index([("medications.name", ASCENDING)])
            logger.info("Prescription indexes created successfully")
        except Exception as e:
            logger.warning(f"Could not create prescription indexes: {str(e)}")

    def _create_user_indexes(self):
        try:
            self.users_collection.create_index([("email", ASCENDING)], unique=True)
            self.users_collection.create_index([("created_at", DESCENDING)])
            logger.info("User indexes created successfully")
        except Exception as e:
            logger.warning(f"Could not create user indexes: {str(e)}")

    # ---------------------------
    # Prescription methods
    # ---------------------------
    def store_prescription(self, prescription_data: Dict) -> Optional[str]:
        try:
            prescription_data["created_at"] = datetime.utcnow()
            prescription_data["updated_at"] = datetime.utcnow()
            result = self.collection.insert_one(prescription_data)
            logger.info(f"Prescription stored with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except DuplicateKeyError:
            logger.error("Duplicate prescription detected")
            return None
        except Exception as e:
            logger.error(f"Error storing prescription: {str(e)}")
            return None

    def get_prescription(self, prescription_id: str) -> Optional[Dict]:
        try:
            document = self.collection.find_one({"_id": ObjectId(prescription_id)})
            if document:
                document["_id"] = str(document["_id"])
                return document
            return None
        except Exception as e:
            logger.error(f"Error retrieving prescription {prescription_id}: {str(e)}")
            return None

    def search_prescriptions(self, query: Dict, limit: int = 10) -> List[Dict]:
        try:
            cursor = self.collection.find(query).limit(limit).sort("parsed_at", DESCENDING)
            results = []
            for document in cursor:
                document["_id"] = str(document["_id"])
                results.append(document)
            return results
        except Exception as e:
            logger.error(f"Error searching prescriptions: {str(e)}")
            return []

    def get_prescription_stats(self) -> Dict:
        try:
            total_count = self.collection.count_documents({})
            medication_pipeline = [
                {"$unwind": "$medications"},
                {"$group": {"_id": "$medications.name", "count": {"$sum": 1}}},
                {"$sort": {"count": DESCENDING}},
                {"$limit": 10},
            ]
            top_medications = list(self.collection.aggregate(medication_pipeline))

            date_pipeline = [
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                        },
                        "count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id": DESCENDING}},
                {"$limit": 30},
            ]
            prescriptions_by_date = list(self.collection.aggregate(date_pipeline))

            return {
                "total_prescriptions": total_count,
                "top_medications": top_medications,
                "prescriptions_by_date": prescriptions_by_date,
                "last_updated": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}

    def update_prescription(self, prescription_id: str, update_data: Dict) -> bool:
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": ObjectId(prescription_id)}, {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating prescription {prescription_id}: {str(e)}")
            return False

    def delete_prescription(self, prescription_id: str) -> bool:
        try:
            result = self.collection.delete_one({"_id": ObjectId(prescription_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting prescription {prescription_id}: {str(e)}")
            return False

    def close_connection(self):
        try:
            self.client.close()
            logger.info("MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {str(e)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()


# ---------------------------
# Singleton instance
# ---------------------------
mongo_client = MongoDBClient()
db = mongo_client.db
users_collection = db["users"]


# ---------------------------
# Helper functions
# ---------------------------
def insert_ner_prescription(file_path: str, raw_text: str, ner: dict) -> str:
    doc = {
        "file_name": Path(file_path).name,
        "raw_text": raw_text,
        "ner": ner,
        "created_at": datetime.utcnow(),
    }

    with MongoDBClient() as client:
        res = client.collection.insert_one(doc)
        return str(res.inserted_id)


def build_ner_prescription_doc(image_path: str, lines: list, ner: dict) -> dict:
    return {
        "file_name": Path(image_path).name,
        "raw_lines": lines,
        "ner": ner,
        "created_at": datetime.utcnow(),
    }