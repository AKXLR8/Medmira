import os

print("SID:", os.getenv("TWILIO_SID"), "TOKEN?", bool(os.getenv("TWILIO_TOKEN")))
