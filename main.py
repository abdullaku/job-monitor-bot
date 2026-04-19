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


def extract_phones(text: str) -> list:
    return re.findall(r"(?:\+?964|0)7\d{9}", text)


def build_notification(result: dict, email_sent: bool, emails: list, phones: list, msg_link: str) -> str:
    score       = result["score"]
    title       = result["job_title_ku"]
    company     = result["company_ku"]
    location    = result["location_ku"]
    role        = result["matched_profile_title"]
    job_type    = result["job_type_ku"]
    contact_raw = result["contact_ku"]

    # ستاتەسی ئیمێڵ
    if email_sent:
        email_status = f"✅ CV نێردرا بۆ: {emails[0]}"
    elif emails:
        email_status = f"⚠️ CV نەنێردرا (هەڵە): {emails[0]}"
    else:
        email_status = "📭 ئیمێڵی خاوەنکار نییە"

    # ژمارەی مۆبایل
    if phones:
        phone_lines = "\n".join(f"  📞 {p}" for p in phones[:3])
        phone_status = f"ژمارەی پەیوەندی:\n{phone_lines}"
    else:
        phone_status = "📵 ژمارەی مۆبایل نییە"

    return (
        f"🎯 **هەلی کاری گونجاو دۆزرایەوە!**\n"
        f"{'─' * 30}\n"
        f"📌 **پۆست:** {title}\n"
        f"🏢 **کۆمپانیا:** {company}\n"
        f"📍 **شوێن:** {location}\n"
        f"💼 **جۆری کار:** {job_type}\n"
        f"🎭 **ڕۆڵ:** {role}\n"
        f"⭐ **نمرە:** {score}/100\n"
        f"{'─' * 30}\n"
        f"{email_status}\n"
        f"{phone_status}\n"
        f"{'─' * 30}\n"
        f"🔗 [سەیری پۆستەکە بکە]({msg_link})"
    )


@client.on(events.NewMessage(chats=GROUPS))
async def handler(event):
    text = event.message.message
    if not text or not is_job_post(text):
        return

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
        f"Contact={result['contact_type']}"
    )

    emails = extract_emails(text)
    phones = extract_phones(text)

    # --- ناردنی ئیمێڵ ---
    email_sent = False
    if EMAIL_ENABLED and emails:
        try:
            email_sent = send_cv_email(
                to_email=emails[0],
                job_title=result["job_title_ku"],
                role_id=result["matched_profile_id"]
            )
            if email_sent:
                logger.info(f"📧 CV نێردرا بۆ: {emails[0]}")
            else:
                logger.error(f"❌ CV نەنێردرا بۆ: {emails[0]}")
        except Exception as e:
            logger.error(f"❌ هەڵەی ئیمێڵ: {e}")

    # --- ئاگادارکردنەوەی تێلیگرام ---
    try:
        chat = await event.get_chat()
        username = getattr(chat, "username", None)
        msg_link = (
            f"https://t.me/{username}/{event.message.id}"
            if username
            else f"(پەیامی ژمارە {event.message.id})"
        )

        notification = build_notification(result, email_sent, emails, phones, msg_link)
        await client.send_message("me", notification, parse_mode="md")
        logger.info("📨 ئاگادارکردنەوە نێردرا بۆ تێلیگرام")
    except Exception as e:
        logger.error(f"❌ هەڵەی ئاگادارکردنەوەی تێلیگرام: {e}")

    save_seen_job(job_id)


async def main():
    logger.info("🚀 Job Monitor Bot دەستی پێکرد...")
    logger.info(f"📧 ئیمەیڵ: {'چالاک' if EMAIL_ENABLED else 'ناچالاک'}")
    await client.start()
    logger.info(f"✅ {len(GROUPS)} گروپ چاودێری دەکرێت — چاوەڕوانی پۆستی نوێ...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
