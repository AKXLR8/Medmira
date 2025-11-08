"""
Vision OCR → GLiNER NER → MongoDB
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime

# Silence TensorFlow & ONEDNN warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# Global logging format
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
    force=True
)

from src.vision_client import VisionApiClient
from src.prescription_parser import PrescriptionParser
from src.mongo_client import insert_ner_prescription, MongoDBClient
from utils.validators import FileValidator, DataValidator


# ------------------------- PrescriptionReader -------------------------
class PrescriptionReader:
    logger = logging.getLogger("PrescriptionReader")

    def __init__(self):
        self.logger.info("Initializing Prescription Reader...")
        self.vision_client = VisionApiClient()
        self.parser = PrescriptionParser()
        self.mongo_client = MongoDBClient()
        self.file_validator = FileValidator()
        self.data_validator = DataValidator()
        self.logger.info("Prescription Reader Ready")

    def process(self, image_path: str, store_in_db: bool) -> dict:
        start_time = datetime.utcnow()

        ok, err = self.file_validator.validate_image(image_path)
        if not ok:
            return {"success": False, "error": f"Invalid image: {err}"}

        processed_path = self.file_validator.preprocess_image(image_path)
        self.logger.info(f"Processing image: {processed_path}")

        ocr = self.vision_client.extract_text_from_image(str(processed_path))
        if "error" in ocr:
            return {"success": False, "error": f"OCR failed: {ocr['error']}"}

        lines = [ln.strip() for ln in ocr.get("full_text", "").splitlines() if ln.strip()]
        if not lines:
            return {"success": False, "error": "No text extracted"}

        ner_dict = self.parser.extract_entities(lines)
        response = {
            "success": True,
            "raw_text": "\n".join(lines),
            "ner": ner_dict,
            "confidence_score": ocr.get("confidence", 0.0),
            "processing_time": (datetime.utcnow() - start_time).total_seconds()
        }

        # Optional DB insert
        if store_in_db:
            pid = insert_ner_prescription(image_path, response["raw_text"], ner_dict)
            response["prescription_id"] = pid

        return response

    def close(self):
        try:
            self.mongo_client.close_connection()
        except:
            pass

    # Context manager for auto-cleanup
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ------------------------- CLI -------------------------
def build_cli():
    p = argparse.ArgumentParser(description="Vision → GLiNER → Mongo Pipeline")
    p.add_argument("image_path", help="Path to prescription image")
    p.add_argument("--no-store", action="store_true", help="Do NOT store results in MongoDB")
    p.add_argument("--scan-only", action="store_true", help="OCR only (skip GLiNER + Mongo)")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    return p


# ------------------------- MAIN -------------------------
def main():
    args = build_cli().parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    with PrescriptionReader() as reader:
        # OCR only mode
        if args.scan_only:
            ocr = reader.vision_client.extract_text_from_image(args.image_path)
            print(json.dumps({
                "success": True,
                "raw_text": ocr.get("full_text", "").strip(),
                "confidence": ocr.get("confidence", 0.0)
            }, indent=2, default=str))
            sys.exit(0)

        # Full pipeline
        result = reader.process(args.image_path, store_in_db=not args.no_store)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
