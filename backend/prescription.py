
"""
Prescription end-points
  POST /api/upload   – image  →  Vision  →  GLiNER  →  Mongo
  POST /api/manual   – raw text only
  GET  /api/history  – list prescriptions
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
import pymongo
from flask import Blueprint, request, jsonify
from backend.mongo_atlas import Prescription
from main import main
from bson import ObjectId
import base64
from io import BytesIO
from PIL import Image
from src.mongo_client import db


# ------------------------------------------------------------------
# blueprint & constants
# ------------------------------------------------------------------
pres_bp = Blueprint("upload", __name__, url_prefix="/api")
UPLOAD_FOLDER = Path("images")                      # relative to backend/
CLI_ENTRY     = Path(__file__).resolve().parent.parent / "main.py"  # your script


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _run_model(image_path: Path) -> dict[str, Any]:
    """
    Run the external pipeline (main.py) and safely extract the final JSON output.
    """
    out = subprocess.run(
        [sys.executable, str(CLI_ENTRY), str(image_path)],
        cwd=CLI_ENTRY.parent,
        capture_output=True,
        text=True,
        check=False,
    )

    if out.returncode != 0:
        raise RuntimeError(out.stderr or "Vision/GLiNER pipeline failed")

    if not out.stdout.strip():
        raise RuntimeError("pipeline produced no stdout")

    # Debug log
    print("=== PIPELINE STDOUT ===")
    print(out.stdout)
    print("=== END STDOUT ===")

    import re

    # Find all {...} blocks (non-greedy so we don’t swallow too much)
    matches = re.findall(r"\{[\s\S]*?\}", out.stdout)
    if not matches:
        raise RuntimeError(f"invalid JSON from pipeline: {out.stdout}")

    # Scan from the last block backwards and try parsing
    for candidate in reversed(matches):
        if '"' in candidate:   # JSON must have double quotes
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    # If nothing works → show full stdout for debugging
    raise RuntimeError(f"Could not find valid JSON in pipeline output: {out.stdout}")



from bson import ObjectId
from src.mongo_client import insert_ner_prescription
from src.prescription_parser import PrescriptionParser   # GLiNER wrapper
from werkzeug.utils import secure_filename
# ---------- Session 1 : Vision only ----------


@pres_bp.post("/upload")
def upload_image() -> tuple[dict, int]:
    """
    1.  multipart image
    2.  save to disk
    3.  return absolute path
    (no Vision, no GLiNER, no Mongo)
    """
    if "file" not in request.files:
        return {"error": "no file part"}, 400

    file = request.files["file"]
    if file.filename == "":
        return {"error": "no selected file"}, 400

    UPLOAD_FOLDER.mkdir(exist_ok=True)
    filename = secure_filename(file.filename)
    file_path = UPLOAD_FOLDER / filename
    file.save(file_path)

    return {
        "message": "Image saved",
        "file_path": str(file_path.absolute())
    }, 201


@pres_bp.post("/scan")
def scan() -> tuple[dict, int]:
    """
    1. Receive multipart image
    2. Vision OCR (main.py --scan-only)
    3. GLiNER NER on the OCR text
    4. Store to MongoDB
    5. Return {prescription_id, raw_text, ner}
    """
    if "file" not in request.files:
        return {"error": "no file part"}, 400

    file = request.files["file"]
    if file.filename == "":
        return {"error": "no selected file"}, 400

    # 1. save image
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    image_path = UPLOAD_FOLDER / secure_filename(file.filename)
    file.save(image_path)

    # 2. OCR via CLI
    out = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "main.py"),
         str(image_path), "--scan-only"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True, text=True, check=False,
    )
    if out.returncode != 0:
        return {"error": out.stderr or "Vision failed"}, 500

    stdout = out.stdout.strip()

    # 3. extract raw_text (JSON or plain fallback)
    try:
        data = json.loads(stdout)
        raw_text = data.get("raw_text", "")
    except json.JSONDecodeError:
        raw_text = stdout

    if not raw_text:
        return {"error": "OCR returned empty text"}, 500

    # 4. GLiNER NER
    parser = PrescriptionParser()
    ner_dict = parser.extract_entities(raw_text.splitlines())

    # 5. Mongo insert
    pid = insert_ner_prescription(
        file_path=image_path.name,
        raw_text=raw_text,
        ner=ner_dict,
    )

    # 6. response
    return {
        "prescription_id": pid,
        "raw_text": raw_text,
        "ner": ner_dict,
    }, 201


# ------------------------------------------------------------------
# routes
# ------------------------------------------------------------------


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


# @pres_bp.get("auth/history")
# def history() -> dict[str, Any]:
#     # return all prescriptions (since user_id filtering removed)
#     return jsonify(Prescription.list_all())




@pres_bp.get("/history")
def history() -> dict[str, Any]:
    docs = Prescription.list_all()          # list[dict] with ObjectId
    for d in docs:
        if "_id" in d and isinstance(d["_id"], ObjectId):
            d["_id"] = str(d["_id"])        # JSON-safe string
    return jsonify(docs)