# main.py
import asyncio
import logging
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from config import (
    API_ID, API_HASH, TELEGRAM_SESSION,
    GROUPS, JOB_KEYWORDS, MIN_TEXT_LENGTH,
    EMAIL_ENABLED
)
from evaluator import evaluate_job
from storage import load_seen_jobs, save_seen_job
from email_sender import send_cv_email

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


def extract_emails(text: str) -> list:
    return re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)


@client.on(events.NewMessage(chats=GROUPS))
async def handler(event):
    text = event.message.message
    if not text or not is_job_post(text):
        return

    # ئارزیابی تەواوی پۆست
    result = evaluate_job(text, group_name="")

    if not result["suitable"]:
        logger.debug(f"❌ گونجاو نییە (Score: {result['score']}) — {result['reason_ku']}")
        return

    job_id = str(event.message.id)
    if job_id in load_seen_jobs():
        return

    logger.info(
        f"🎯 هەلی کاری گونجاو! Score={result['score']} | "
        f"Role={result['matched_profile_title']} | "
        f"Title={result['job_title_ku']} | "
        f"Contact={result['contact_type']}"
    )

    # ئیمێڵ دەدۆزینەوە لە ناوی پۆستەکە
    emails = extract_emails(text)

    if EMAIL_ENABLED and emails:
        contact_email = emails[0]
        try:
            success = send_cv_email(
                to_email=contact_email,
                job_title=result["job_title_ku"],
                role_id=result["matched_profile_id"]
            )
            if success:
                logger.info(f"📧 CV نێردرا بۆ: {contact_email} ({result['matched_profile_title']})")
            else:
                logger.error(f"❌ CV نەنێردرا بۆ: {contact_email}")
        except Exception as e:
            logger.error(f"❌ هەڵەی ئیمێڵ: {e}")

    elif EMAIL_ENABLED and not emails:
        logger.info(
            f"ℹ️ هەلی کار گونجاوە بەڵام ئیمێڵی خاوەنکار نەدۆزرایەوە "
            f"| Contact: {result['contact_ku']}"
        )

    save_seen_job(job_id)


async def main():
    logger.info("🚀 Job Monitor Bot دەستی پێکرد...")
    logger.info(f"📧 ئیمەیڵ: {'چالاک' if EMAIL_ENABLED else 'ناچالاک'}")
    await client.start()
    logger.info(f"✅ {len(GROUPS)} گروپ چاودێری دەکرێت — چاوەڕوانی پۆستی نوێ...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
