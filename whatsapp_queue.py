# whatsapp_queue.py
import json
import os

QUEUE_FILE = "whatsapp_messages.json"

def add_to_whatsapp_queue(phone_number, message, cv_path=None):
    """زیادکردنی نامەیەک بۆ ڕیزی ناردن بە وەتسئاپ"""
    data = []
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                data = []
    
    data.append({
        "phone": phone_number,
        "message": message,
        "cv_path": cv_path,
        "sent": False
    })
    
    with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ داواکاری وەتسئاپ بۆ {phone_number} زیاد کرا.")
