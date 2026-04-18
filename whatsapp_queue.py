# whatsapp_queue.py
import requests
import os

# ئەم لینکە دواتر دروستی دەکەین
WHATSAPP_API_URL = os.environ.get("WHATSAPP_API_URL", "http://localhost:3000/send")

def add_to_whatsapp_queue(phone_number, message, cv_path=None, job_title=""):
    """
    داواکاری ناردنی نامە دەنێرێت بۆ بۆتی وەتسئاپ
    """
    try:
        payload = {
            "phone": phone_number,
            "message": message,
            "cv_path": cv_path,
            "job_title": job_title
        }
        response = requests.post(WHATSAPP_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ [وەتسئاپ] داواکاری نێردرا بۆ {phone_number}")
        return True
    except Exception as e:
        print(f"❌ [وەتسئاپ] هەڵە لە ناردنی داواکاری بۆ {phone_number}: {e}")
        return False
