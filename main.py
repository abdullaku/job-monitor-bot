# main.py
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events
from config import (
    API_ID, API_HASH, TELEGRAM_SESSION,
    GROUPS, JOB_KEYWORDS, MIN_TEXT_LENGTH,
    EMAIL_ENABLED, WHATSAPP_ENABLED
)
from evaluator import evaluate_job_match
from storage import load_seen_jobs, save_seen_job
from email_sender import send_email_notification
from profile_data import USER_NAME, USER_CV_PATH, USER_PHONE
from whatsapp_queue import add_to_whatsapp_queue
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

client = TelegramClient('session', API_ID, API_HASH)

def is_job_post(text):
    if len(text.strip()) < MIN_TEXT_LENGTH:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in JOB_KEYWORDS)

def extract_phone_from_job(job):
    import re
    text = job.get('description', '') + ' ' + job.get('content', '')
    patterns = [
        r'07[0-9]{9}',
        r'\+9647[0-9]{9}',
        r'009647[0-9]{9}',
        r'07\d{2}\s?\d{3}\s?\d{4}'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = re.sub(r'[\s\+]', '', match.group())
            if phone.startswith('00964'):
                phone = '0' + phone[5:]
            elif phone.startswith('+964'):
                phone = '0' + phone[4:]
            return phone
    return None

def generate_whatsapp_message(job):
    return f"""بەڕێز خاوەن کار،

سڵاو. من {USER_NAME}ـم.
ئەم هەلی کارەم لە ڕێگەی بۆتێکی چاودێری هەلی کارەوە بینی و زۆر بەدڵم بوو.

📌 ناونیشانی کار: {job.get('title', 'نادیار')}
📍 شوێن: {job.get('location', 'نادیار')}
🏢 کۆمپانیا: {job.get('company', 'نادیار')}

تکایە فایلی CVـی من لە پەیوەستکراو بخوێنەرەوە.
بە هیوای سەرکەوتنی هەردوولامان.

سوپاس،
{USER_NAME}
📞 {USER_PHONE}"""

def generate_email_body(job):
    return f"""Subject: Application for {job.get('title', 'Position')}

Dear Hiring Manager,

I am writing to express my interest in the {job.get('title')} position at {job.get('company')}.

Best regards,
{USER_NAME}"""

@client.on(events.NewMessage(chats=GROUPS))
async def handler(event):
    text = event.message.message
    if not text or not is_job_post(text):
        return

    job = {
        'description': text,
        'content': text,
        'title': 'نادیار',
        'company': 'نادیار',
        'link': str(event.message.id)
    }

    score, is_match = evaluate_job_match(job)
    if not is_match:
        logger.debug(f"❌ گونجاو نییە (Score: {score})")
        return

    job_id = str(event.message.id)
    if job_id in load_seen_jobs():
        return

    logger.info(f"🎯 هەلی کاری گونجاو دۆزرایەوە! Score: {score}")

    phone_number = extract_phone_from_job(job)

    if EMAIL_ENABLED and job.get('contact_email'):
        try:
            send_email_notification(
                to_email=job['contact_email'],
                subject=f"Application for {job.get('title')}",
                body=generate_email_body(job),
                attachment_path=USER_CV_PATH
            )
            logger.info(f"📧 ئیمەیڵ نێردرا بۆ {job.get('contact_email')}")
        except Exception as e:
            logger.error(f"❌ ئیمەیڵ: {e}")

    if WHATSAPP_ENABLED and phone_number:
        try:
            add_to_whatsapp_queue(
                phone_number=phone_number,
                message=generate_whatsapp_message(job),
                cv_path=USER_CV_PATH,
                job_title=job.get('title', 'نادیار')
            )
            logger.info(f"📱 وەتسئاپ نێردرا بۆ {phone_number}")
        except Exception as e:
            logger.error(f"❌ وەتسئاپ: {e}")

    save_seen_job(job_id)

async def main():
    logger.info("🚀 Job Monitor Bot دەستی پێکرد...")
    logger.info(f"📧 ئیمەیڵ: {'چالاک' if EMAIL_ENABLED else 'ناچالاک'}")
    logger.info(f"📱 وەتسئاپ: {'چالاک' if WHATSAPP_ENABLED else 'ناچالاک'}")
    await client.start()
    logger.info(f"✅ {len(GROUPS)} گروپ چاودێری دەکرێت — چاوەڕوانی پۆستی نوێ...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
