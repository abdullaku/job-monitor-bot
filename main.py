from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
from datetime import datetime

from config import API_ID, API_HASH, TELEGRAM_SESSION, GROUPS, NOTIFY_CHAT, MIN_SCORE
from text_utils import contains_job_keyword, make_job_key
from storage import load_seen_jobs, is_seen, mark_seen
from evaluator import evaluate_job

client = TelegramClient(StringSession(TELEGRAM_SESSION), API_ID, API_HASH)


def register_handlers(app_client):
    @app_client.on(events.NewMessage(chats=GROUPS))
    async def handle_new_message(event):
        message_text = event.raw_text or ""
        group_name = event.chat.title if getattr(event, "chat", None) and getattr(event.chat, "title", None) else "نەزانراو"

        if len(message_text.strip()) < 20:
            return

        if not contains_job_keyword(message_text):
            return

        job_key = make_job_key(message_text, group_name)
        if is_seen(job_key):
            return

        print(f"\n🔍 هەلی کار دۆزراوەتەوە لە: {group_name}")
        print(f"📝 {message_text[:220]}")

        evaluation = evaluate_job(message_text, group_name)

        if evaluation.get("location_ok") is False:
            print(f"❌ شوێن گونجاو نییە - {evaluation.get('location_ku', 'نەزانراو')}")
            return

        if not evaluation.get("suitable", False):
            print(f"❌ گونجاو نییە - {evaluation.get('reason_ku', '')}")
            return

        score = int(evaluation.get("score", 0))
        if score < MIN_SCORE:
            print(f"❌ نمرە کەمە ({score}/100)")
            return

        mark_seen(job_key)

        job_title = evaluation.get("job_title_ku", "نەزانراو")
        company = evaluation.get("company_ku", "نەزانراو")
        location_ku = evaluation.get("location_ku", "نەزانراو")
        gender_ku = evaluation.get("gender_ku", "نەزانراو")
        job_type_ku = evaluation.get("job_type_ku", "نەزانراو")
        reason_ku = evaluation.get("reason_ku", "")
        summary_ku = evaluation.get("summary_ku", "")
        matched_profile = evaluation.get("matched_profile_title", "")
        salary_ku = evaluation.get("salary_ku", "نەزانراو")
        contact_ku = evaluation.get("contact_ku", "نەزانراو")
        requirements_ku = evaluation.get("requirements_ku", [])

        req_text = "\n".join([f"- {x}" for x in requirements_ku[:6]]) if requirements_ku else "- نەزانراو"

        job_link = (
            f"https://t.me/{event.chat.username}/{event.id}"
            if getattr(event.chat, "username", None)
            else "بەردەست نییە"
        )

        notification = f"""🟢 هەلی کاری گونجاو دۆزراوەتەوە!

📌 وەزیفە: {job_title}
🏢 کۆمپانیا: {company}
📍 شار: {location_ku}
🚻 ڕەگەز: {gender_ku}
💼 جۆری کار: {job_type_ku}
⭐ گونجاوی: {score}/100

👤 چوارچێوەی سیڤی: {matched_profile}
💬 هۆکار: {reason_ku}

📋 پوختە:
{summary_ku}

✅ مەرجەکان:
{req_text}

💰 موچە: {salary_ku}
☎️ پەیوەندی: {contact_ku}

📢 گرووپ: {group_name}
🔗 لینک: {job_link}

📄 دەقی سەرەکی:
{message_text[:900]}

⏰ کات: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

        await app_client.send_message(NOTIFY_CHAT, notification)
        print("📨 ئاگادارکردنەوە نێردرا!")


async def main():
    load_seen_jobs()
    register_handlers(client)

    await client.start()
    me = await client.get_me()

    print("🚀 Job Monitor Bot دەستپێدەکات...")
    print(f"👁️ چاودێری {len(GROUPS)} گرووپ دەکات")
    print("==================================================")
    print(f"✅ لۆگین بوو بە: {getattr(me, 'first_name', '')} (@{getattr(me, 'username', 'no_username')})")
    print("✅ تەنها local filter چالاکە (AI ناچالاکە)")
    print("⏳ چاودێری دەکات... (Ctrl+C بکە بۆ وەستان)")

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 وەستێنرا")
