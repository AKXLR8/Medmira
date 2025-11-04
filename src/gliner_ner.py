"""
GLiNER inference – zero-download version.
API 100 % identical to your old module so *no* caller code changes.
"""
import os
import joblib
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

MEDICAL_LABELS = [
    "Drug", "Strength", "Dosage", "Frequency", "Duration",
    "Route", "Form", "Patient", "Doctor", "Date", "Age"
]

# ---------- singleton ----------
_MODEL = None

def _load_model():
    global _MODEL
    if _MODEL is None:
        pkl = Path(__file__).with_name("gliner_model.pkl")
        if not pkl.exists():
            raise FileNotFoundError("gliner_model.pkl not found – run create_pkl.py first")
        print("Loading GLiNER from gliner_model.pkl …")   # ← NEW
        _MODEL = joblib.load(pkl)
        print("GLiNER pickle ready – model id:", id(_MODEL))  # ← NEW
    return _MODEL

# ---------- public helper ----------
def extract_entities(text: str, labels: List[str] = MEDICAL_LABELS) -> Dict[str, List[Dict]]:
    """
    Identical signature & return shape as before.
    """
    model = _load_model()
    entities = model.predict_entities(text, labels, threshold=0.30)

    # ---- your original de-duplication & sorting ----
    best: Dict[tuple, float] = defaultdict(float)
    for ent in entities:
        key = (ent["label"], ent["text"])
        best[key] = max(best[key], ent["score"])

    out = {lbl: [] for lbl in labels}
    for (label, txt), score in best.items():
        out[label].append({"text": txt, "score": round(score, 3)})
    for lst in out.values():
        lst.sort(key=lambda x: x["score"], reverse=True)

    return out