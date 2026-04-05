"""
Job Monitor Bot - Abdulla Ali
چاودێری هەڵی کار لە گرووپەکانی تیلیگرام
"""

from telethon import TelegramClient, events
import asyncio
import aiohttp
import json
import os
from datetime import datetime

# ===== زانیاریەکان =====
API_ID = 38746926
API_HASH = "38dc23beaecc586ba785883b57e966ff"
GROQ_API_KEY = "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"

# ===== ئەکاونتی خۆت (بۆ وەرگرتنی ئاگادارکردنەوە) =====
YOUR_TELEGRAM_ID = None  # دەتووریتەوە دوای دەستپێکردن

# ===== گرووپەکان =====
GROUPS = [
    "fjkurdistan10",
    "allkurdistanjobs",
    "job_ira",
    "oil_jobs_kurdistan_Iraq",
    "halykar0",
    "awezajobs",
    "IJobsIQ",
    "kwrjobs",
    "halekarlakurdistan",
    "jobtargett",
    "kurd24job",
    "taniajob",
    "krdjobs",
    "dozar_jobs",
    "sunjobsorganization",
    "job123opportunity",
    "RD_HaliKar",
    "negakantt",
]

# ===== کەلمەی کار =====
JOB_KEYWORDS = [
    # کوردی
    "درکاوە", "هەڵی کار", "کارمەند", "فرصە", "پێویستمان",
    "کارەکە", "وەزیفە", "دامەزراندن", "کرێکار",
    # عەرەبی
    "وظيفة", "مطلوب", "فرصة عمل", "نبحث عن", "تعيين",
    "توظيف", "عمل", "وظائف", "مطلوب موظف",
    # ئینگلیزی
    "hiring", "vacancy", "job opportunity", "we are looking",
    "position available", "join our team", "apply now",
    "required", "wanted", "recruitment",
]

# ===== زانیاری سیڤی =====
CV_SUMMARY = """
ناو: Abdulla Ali
پیشە: پسپۆری نێوەندگیری خانووبەرە و عەقارات
شوێن: هەولێر، عێراق

ئەزموون:
- نێوەندگیری فرۆشتنی خانووبەرە و لایف تاوەر
- پەیوەندیکردن لەگەڵ کڕیار و فرۆشیارەکان
- ئامادەکردن و پێشکەشکردنی پیشنیار تایبەت
- بەڕێوەبردنی قابلەکانی کرێن و فرۆشتن
- کاشێری سیستەم ٢٠٢٢-٢٠٢٤
- بەڕێوەبردنی CRM

زمانەکان: کوردی (دایک)، عەرەبی (زۆر باش)، ئینگلیزی (ناوەڕاست)

خوێندن: بەکالۆریۆس - زانکۆی سەلاحەدین هەولێر - ٢٠٢٥

لێهاتووی تەکنیکی: Microsoft Office، CRM، POS، بەڕێوەبردنی تۆڕ
"""

# ===== هەڵسەنگاندن بە Groq AI =====
async def evaluate_job(job_text: str) -> dict:
    """هەڵسەنگاندنی هەڵی کار ئایا لەگەڵ سیڤی دەگونجێت"""
    
    prompt = f"""
سیڤی کاندیدات:
{CV_SUMMARY}

هەڵی کاری دۆزراوەتەوە:
{job_text}

پرسیار: ئایا ئەم هەڵی کارە لەگەڵ ئەم کاندیداتە دەگونجێت؟

وەڵامت بدەرەوە تەنها بە JSON فۆرمات:
{{
  "suitable": true/false,
  "score": 0-100,
  "reason": "هۆکاری کورت بە کوردی",
  "job_title": "ناوی وەزیفەکە",
  "company": "ناوی کۆمپانیاکە ئەگەر هەبوو"
}}
"""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.1
                }
            ) as resp:
                data = await resp.json()
                text = data["choices"][0]["message"]["content"]
                # پاککردنەوەی JSON
                text = text.strip()
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return json.loads(text.strip())
    except Exception as e:
        print(f"Groq هەڵە: {e}")
        return {"suitable": True, "score": 50, "reason": "هەڵسەنگاندن سەرکەوتوو نەبوو", "job_title": "نەزانراو", "company": "نەزانراو"}


# ===== تەکست چاودێری =====
def contains_job_keyword(text: str) -> bool:
    """بینینی ئایا پەیامەکە هەڵی کار دەگەیەنێت"""
    text_lower = text.lower()
    for keyword in JOB_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    return False


# ===== دەستپێکردنی بۆت =====
client = TelegramClient("job_session", API_ID, API_HASH)

@client.on(events.NewMessage(chats=GROUPS))
async def handle_new_message(event):
    """کاتێک پەیامی نوێ دێت"""
    
    message_text = event.message.text or ""
    
    if len(message_text) < 20:
        return
    
    if not contains_job_keyword(message_text):
        return
    
    print(f"\n🔍 هەڵی کار دۆزراوەتەوە لە: {event.chat.title if hasattr(event.chat, 'title') else 'نەزانراو'}")
    print(f"📝 پەیام: {message_text[:100]}...")
    
    # هەڵسەنگاندن بە AI
    evaluation = await evaluate_job(message_text)
    
    if not evaluation.get("suitable", False):
        print(f"❌ گونجاو نییە - {evaluation.get('reason', '')}")
        return
    
    score = evaluation.get("score", 0)
    if score < 40:
        print(f"❌ نمرە کەمە ({score}/100)")
        return
    
    print(f"✅ گونجاوە! نمرە: {score}/100")
    
    # ئاگادارکردنەوە
    group_name = event.chat.title if hasattr(event.chat, "title") else "نەزانراو"
    job_link = f"https://t.me/{event.chat.username}/{event.id}" if hasattr(event.chat, "username") else "بەردەست نییە"
    
    notification = f"""
🟢 هەڵی کاری نوێ دۆزراوەتەوە!

📌 وەزیفە: {evaluation.get('job_title', 'نەزانراو')}
🏢 کۆمپانیا: {evaluation.get('company', 'نەزانراو')}
⭐ گونجاوی: {score}/100
💬 هۆکار: {evaluation.get('reason', '')}

📢 گرووپ: {group_name}
🔗 لینک: {job_link}

📄 پەیامی تەواو:
{message_text[:500]}

⏰ کات: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    
    # ناردنی پەیام بۆ خۆت
    await client.send_message("me", notification)
    print(f"📨 ئاگادارکردنەوە نێردرا!")


async def main():
    print("🚀 Job Monitor Bot دەستپێدەکات...")
    print(f"👁️ چاودێری {len(GROUPS)} گرووپ دەکات")
    print("=" * 50)
    
    await client.start()
    
    me = await client.get_me()
    print(f"✅ لۆگین بوو بە: {me.first_name} (@{me.username})")
    print("⏳ چاودێری دەکات... (Ctrl+C بکە بۆ وەستان)")
    
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
