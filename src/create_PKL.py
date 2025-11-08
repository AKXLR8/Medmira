
import os
import joblib
from gliner import GLiNER

print("Downloading urchade/gliner_large_bio-v0.1 …")
model = GLiNER.from_pretrained("urchade/gliner_large_bio-v0.1")

pkl_path = "gliner_model.pkl"
print(f"Serialising to {pkl_path} …")
joblib.dump(model, pkl_path, compress=3)
print("✅  Done add gliner_model.pkl to Docker context.")