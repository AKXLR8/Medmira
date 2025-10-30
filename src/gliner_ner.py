from gliner import GLiNER
from typing import Dict, List
from collections import defaultdict
import os            

ner = GLiNER.from_pretrained("urchade/gliner_large_bio-v0.1")

MEDICAL_LABELS = [
    "Drug", "Strength", "Dosage", "Frequency", "Duration",
    "Route", "Form", "Patient", "Doctor", "Date", "Age"
]

# ---------- singleton holder ----------
_ner_model = None

def _get_gliner() -> GLiNER:
    """Load once per container; reuse forever."""
    global _ner_model
    if _ner_model is None:
        cache_dir = os.getenv("TRANSFORMERS_CACHE", "/app/models")
        _ner_model = GLiNER.from_pretrained(
            "urchade/gliner_large_bio-v0.1",
            cache_dir=cache_dir
        )
    return _ner_model

# ---------- public helper ----------
def extract_entities(text: str, labels: List[str] = MEDICAL_LABELS) -> Dict[str, List[Dict]]:
    print("Extracting text:", text)
    model = _get_gliner()          # first call triggers download
    entities = model.predict_entities(text, labels, threshold=0.30)
    print("Extracted raw entities:", entities)

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


