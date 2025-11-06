#!/usr/bin/env python3
"""
Vision OCR → GLiNER NER → MongoDB
"""
import re
import json
import argparse
import logging
import sys
from datetime import datetime
from typing import Optional
import os, sys
import os, sys, logging
# 1. kill TF spam
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
# 2. force every logger to stderr and level WARNING
logging.basicConfig(
    level=logging.WARNING,          # INFO → WARNING
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
    force=True                      # override any previous setup
)
# 3. lower your own module if you really need it
logging.getLogger("PrescriptionReader").setLevel(logging.INFO)
# ------------------------- IMPORTS -------------------------
from src.vision_client import VisionApiClient
from src.prescription_parser import PrescriptionParser
from src.mongo_client import insert_ner_prescription, MongoDBClient
from utils.validators import FileValidator, DataValidator


# ------------------------- CLI ARGUMENTS -------------------------
parser = argparse.ArgumentParser(description="Vision → GLiNER → Mongo")
parser.add_argument("image_path", help="Path to prescription image")
parser.add_argument("--no-store", action="store_true", help="Skip DB insert")
parser.add_argument("--scan-only", action="store_true", help="OCR only, no Mongo")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")


# ------------------------- PrescriptionReader CLASS -------------------------
class PrescriptionReader:
    logger = logging.getLogger("PrescriptionReader")

    def __init__(self):
        self.logger = PrescriptionReader.logger
        self.vision_client = VisionApiClient()
        self.parser = PrescriptionParser()
        self.mongo_client = MongoDBClient()
        self.file_validator = FileValidator()
        self.data_validator = DataValidator()
        self.logger.info("Prescription reading system initialized")

def main():
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    reader = PrescriptionReader()
    start_time = datetime.utcnow()

    def process_prescription(self, image_path: str, store_in_db: bool = True) -> dict:
        start_time = datetime.utcnow()
        try:
            # 1.  File check
            ok, err = self.file_validator.validate_image(image_path)
            if not ok:
                return {"success": False, "error": f"File validation failed: {err}"}

            processed_path = self.file_validator.preprocess_image(image_path)
            self.logger.info(f"Processing image: {processed_path}")

            # 2.  Vision OCR
            ocr = self.vision_client.extract_text_from_image(str(processed_path))
            if "error" in ocr:
                return {"success": False, "error": f"OCR failed: {ocr['error']}"}

            lines = [ln.strip() for ln in ocr.get("full_text", "").splitlines() if ln.strip()]
            if not lines:
                return {"success": False, "error": "No text found in image"}

            # 3.  GLiNER NER
            ner_dict = self.parser.extract_entities(lines)

            # ---------- decide what to return ----------
            if args.scan_only:
                # Vision only → no Mongo
                results = {
                    "success": True,
                    "raw_text": "\n".join(lines),
                    "confidence": ocr.get("confidence", 0.0)
                }
                print(json.dumps(results, indent=2, default=str))
                sys.exit(0)

            # Normal pipeline (Vision + GLiNER + Mongo)
            prescription_id = None
            if not args.no_store:
                prescription_id = insert_ner_prescription(
                    file_path=image_path,
                    raw_text="\n".join(lines),
                    ner=ner_dict
                )
                if prescription_id:
                    self.logger.info(f"Mongo NER ID: {prescription_id}")

            return {
                "success": True,
                "prescription_id": prescription_id,
                "raw_text": "\n".join(lines),
                "ner": ner_dict,
                "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                "confidence_score": ocr.get("confidence", 0.0)
            }

        except Exception as e:
            self.logger.exception(f"Unexpected error: {e}")
            return {"success": False, "error": str(e)}

    def close(self):
        self.mongo_client.close_connection()
        self.logger.info("MongoDB connection closed")


# ------------------------- MAIN -------------------------
def main():
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    reader = PrescriptionReader()
    start_time = datetime.utcnow()

    try:
        # 1.  File check
        ok, err = reader.file_validator.validate_image(args.image_path)
        if not ok:
            results = {"success": False, "error": f"File validation failed: {err}"}
            print(json.dumps(results, indent=2, default=str))
            sys.exit(1)

        processed_path = reader.file_validator.preprocess_image(args.image_path)
        reader.logger.info(f"Processing image: {processed_path}")

        # 2.  Vision OCR
        ocr = reader.vision_client.extract_text_from_image(str(processed_path))
        if "error" in ocr:
            results = {"success": False, "error": f"OCR failed: {ocr['error']}"}
            print(json.dumps(results, indent=2, default=str))
            sys.exit(1)

        lines = [ln.strip() for ln in ocr.get("full_text", "").splitlines() if ln.strip()]
        if not lines:
            results = {"success": False, "error": "No text found in image"}
            print(json.dumps(results, indent=2, default=str))
            sys.exit(1)

        # 3.  GLiNER NER
        ner_dict = reader.parser.extract_entities(lines)

        # ---------- decide what to return ----------
        if args.scan_only:
            # Vision only → no Mongo
            results = {
                "success": True,
                "raw_text": "\n".join(lines),
                "confidence": ocr.get("confidence", 0.0)
            }
            print(json.dumps(results, indent=2, default=str))
            sys.exit(0)

        # Normal pipeline (Vision + GLiNER + Mongo)
        prescription_id = None
        if not args.no_store:
            prescription_id = insert_ner_prescription(
                file_path=args.image_path,
                raw_text="\n".join(lines),
                ner=ner_dict
            )
            if prescription_id:
                reader.logger.info(f"Mongo NER ID: {prescription_id}")

        results = {
            "success": True,
            "prescription_id": prescription_id,
            "raw_text": "\n".join(lines),
            "ner": ner_dict,
            "processing_time": (datetime.utcnow() - start_time).total_seconds(),
            "confidence_score": ocr.get("confidence", 0.0)
        }
        print(json.dumps(results, indent=2, default=str))
        if not results["success"]:
            sys.exit(1)

    except Exception as e:
        reader.logger.exception(f"Unexpected error: {e}")
        results = {"success": False, "error": str(e)}
        print(json.dumps(results, indent=2, default=str))
        sys.exit(1)
    finally:
        reader.close()

if __name__ == "__main__":
    main()