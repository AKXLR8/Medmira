#backend/alarm.py
import schedule
import subprocess
from datetime import datetime, timedelta
from backend.models import alarms
from twilio.rest import Client
import os
from backend.models import db

_twilio = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
TWILIO_WHATSAPP = os.getenv("TWILIO_WHATSAPP")   # +14155238886

def send_guardian_welcome(guardian_whatsapp: str, user_name: str):
    """Send guardian a WhatsApp message after registration."""
    if not guardian_whatsapp:
        return
    # ensure number starts with “+”
    if not guardian_whatsapp.startswith("+"):
        guardian_whatsapp = f"+{guardian_whatsapp}"

    body = (
        f"Thank you for registering your ward *{user_name}* with our service. "
        "We will send medicine reminders on this number when required."
    )
    _twilio.messages.create(
        from_=f"whatsapp:{TWILIO_WHATSAPP}",
        to=f"whatsapp:{guardian_whatsapp}",
        body=body
    )



