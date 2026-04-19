# main.py
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import (
    API_ID, API_HASH, TELEGRAM_SESSION,
    GROUPS, JOB_KEYWORDS, MIN_TEXT_LENGTH,
    EMAIL_ENABLED
)
from evaluator import evaluate_job_match
from storage import load_seen_jobs, save_seen_job
from email_sender import send_email_notification
from profile_data import USER_NAME, USER_CV_PATH

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

client = TelegramClient(StringSession(TELEGRAM_SESSION), API_ID, API_HASH)


def is_job_post(text):
    if len(text.strip()) < MIN_TEXT_LENGTH:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in JOB_KEYWORDS)


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

    save_seen_job(job_id)


async def main():
    logger.info("🚀 Job Monitor Bot دەستی پێکرد...")
    logger.info(f"📧 ئیمەیڵ: {'چالاک' if EMAIL_ENABLED else 'ناچالاک'}")
    await client.start()
    logger.info(f"✅ {len(GROUPS)} گروپ چاودێری دەکرێت — چاوەڕوانی پۆستی نوێ...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
