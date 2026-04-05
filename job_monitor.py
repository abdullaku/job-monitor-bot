"""
Job Monitor Bot - Abdulla Ali
چاودێری هەڵی کار لە گرووپەکانی تیلیگرام
"""

from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import aiohttp
import json
import os
import sys
import re
import hashlib
from datetime import datetime

# ===== زانیاریەکان =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION", "").strip()

if not TELEGRAM_SESSION:
    print("❌ TELEGRAM_SESSION بەتاڵە")
    sys.exit(1)

# ===== ڕێکخستن =====
NOTIFY_CHAT = "me"
MIN_SCORE = 65

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

# ===== کەلمە سەرەتاییەکان =====
JOB_KEYWORDS = [
    "درکاوە", "هەڵی کار", "کارمەند", "فرصە", "پێویستمان", "کارەکە", "وەزیفە",
    "دامەزراندن", "کرێکار", "وظيفة", "مطلوب", "فرصة عمل", "نبحث عن", "تعيين",
    "توظيف", "عمل", "وظائف", "مطلوب موظف", "hiring", "vacancy", "job opportunity",
    "we are looking", "position available", "join our team", "apply now", "required",
    "wanted", "recruitment", "job title", "location", "reports to"
]

# ===== تەنها هەولێر / Hawler =====
PREFERRED_LOCATIONS = [
    "هەولێر", "هه‌ولێر", "hawler", "erbil", "اربيل", "أربيل",
    "بەحرکە", "بحركة", "baharka", "عەنکاوە", "عنكاوه", "ankawa",
    "کەس نەزان", "kesnazan", "kasnazan"
]

EXCLUDED_LOCATIONS = [
    "سلێمانی", "سليمانية", "slemani", "sulaimani", "sulaymaniyah",
    "دهۆک", "duhok", "dohuk", "بغداد", "baghdad", "basra", "البصرة",
    "بصره", "mosul", "ninawa", "kirkuk", "کرکوك", "karbala", "najaf"
]

# ===== کارە ڕەتکراوەکان =====
REJECT_KEYWORDS = [
    "restaurant", "kitchen", "chef", "cook", "waiter", "waitress",
    "cleaner", "dishwasher", "security", "guard", "سكورتي", "حراسة",
    "مطعم", "مطبخ", "طباخ", "نادل", "cleaning", "خانەخواردن", "چێشتخانە",
    "شێف", "مەتبەخ", "نانوایی", "فاست فود", "حارس", "سكويرتى"
]

# ===== 3 profile ـی CV =====
CV_PROFILES = [
    {
        "id": "real_estate",
        "name_ku": "نێوەندگیری خانووبەرە و عەقارات",
        "summary": """
شوێن: هەولێر - بەحرکە
ئەزموون:
- نێوەندگیری خانووبەرە و عەقارات
- فرۆشتنی موڵک و پڕۆژەکانی خانووبەرە
- شیکردنەوەی بازاڕ
- ئامادەکردنی پێشنیار و کۆنتراکت
- مامەڵەکردن لەگەڵ کڕیار و فرۆشیار
بەهرەکان:
- Real Estate Sales
- Negotiation
- Client Relationship
- Market Analysis
- Documentation
- Microsoft Office
- Marketing
- Branding
- Social Media
"""
    },
    {
        "id": "sales_crm",
        "name_ku": "فرۆشتن و CRM",
        "summary": """
شوێن: هەولێر - بەحرکە
ئەزموون:
- Sales Specialist
- CRM
- Customer Relationship
- Marketing & Branding
- Social Media Management
- Sales Reports
- Direct Sales / Retail Sales
- Persuasion and negotiation
بەهرەکان:
- Sales
- CRM
- Customer Service
- Marketing
- Branding
- Reporting
- Microsoft Office
- Communication
- Driver License
"""
    },
    {
        "id": "system_cashier",
        "name_ku": "سیستەم / کاشێر / POS",
        "summary": """
شوێن: هەولێر - بەحرکە
ئەزموون:
- Cashier
- POS
- System Management
- Record Keeping
- Dealing with cash and bank cards
- Customer Service
- Daily reports
بەهرەکان:
- POS
- Cashier
- Microsoft Office
- System Management
- Registration / Records
- Customer Service
- Problem Solving
- Accuracy
- Driver License
"""
    }
]

# ===== memory =====
seen_jobs = set()

# ===== helper =====
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ى": "ی", "ؤ": "و", "ئ": "ی",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return text.strip()

def contains_job_keyword(text: str) -> bool:
    text_lower = normalize_text(text)
    return any(normalize_text(k) in text_lower for k in JOB_KEYWORDS)

def contains_reject_keyword(text: str) -> bool:
    text_lower = normalize_text(text)
    return any(normalize_text(k) in text_lower for k in REJECT_KEYWORDS)

def has_preferred_location(text: str) -> bool:
    text_lower = normalize_text(text)
    return any(normalize_text(k) in text_lower for k in PREFERRED_LOCATIONS)

def has_excluded_location(text: str) -> bool:
    text_lower = normalize_text(text)
    return any(normalize_text(k) in text_lower for k in EXCLUDED_LOCATIONS)

def make_job_key(message_text: str, group_name: str) -> str:
    base = f"{group_name}|{message_text[:1200]}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def extract_json(text: str) -> dict | None:
    if not text:
        return None

    cleaned = text.strip()

    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                try:
                    return json.loads(part)
                except Exception:
                    pass

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    return None

# ===== هەڵسەنگاندن بە Groq =====
async def evaluate_job(job_text: str, group_name: str) -> dict:
    profiles_text = "\n\n".join(
        [f"PROFILE {i+1} - {p['name_ku']}:\n{p['summary']}" for i, p in enumerate(CV_PROFILES)]
    )

    prompt = f"""
تۆ سیستەمی هەڵبژاردنی هەلی کاریت بۆ کاندیداتێکی لە هەولێر.
پێویستە تەنها JSON بگەڕێنیتەوە، بێ هیچ قسەی زیاتر.

ڕێساکان:
1) تەنها ئەو job ـانە گونجاون کە لەگەڵ یەکێک لە ئەم 3 profile ـەی خوارەوە دەگونجن.
2) شوێن گرنگە: ئەگەر job ـەکە لە هەولێر / Hawler / Erbil / Baharka / Ankawa نەبێت، suitable = false بکە.
3) ئەگەر شوێن دیار نەبێت، suitable = false بکە.
4) ئەگەر job ـەکە restaurant / kitchen / chef / cook / waiter / cleaner / security / guard و هاوشێوە بێت، suitable = false بکە.
5) ئەگەر job ـەکە گونجاو بوو، ناونیشان و پوختەی کوردی بدەرەوە.
6) ئەگەر پۆستەکە ئینگلیزی یان عەرەبی بێت، بە کوردی وەرگێڕەوە.
7) score لە 0 تا 100 بێت.
8) matched_profile_id تەنها یەکێک بێت لەمە: real_estate, sales_crm, system_cashier
9) matched_skills بریتی بێت لە لیستێکی کورت.
10) تەنها JSON بگەڕێنەوە.

PROFILES:
{profiles_text}

GROUP:
{group_name}

JOB POST:
{job_text}

JSON FORMAT:
{{
  "suitable": true,
  "score": 0,
  "reason_ku": "هۆکار بە کوردی",
  "job_title_ku": "ناوی وەزیفە بە کوردی",
  "company_ku": "ناوی کۆمپانیا بە کوردی یان هەر وەک خۆی",
  "city_ku": "شوێنی کار",
  "matched_profile_id": "real_estate",
  "matched_profile_name_ku": "ناوی profile",
  "matched_skills": ["skill1", "skill2"],
  "summary_ku": "پوختەی کوردی لە job ـەکە",
  "requirements_ku": ["req1", "req2"],
  "salary_ku": "موچە یان نەزانراو",
  "contact_ku": "پەیوەندی یان نەزانراو",
  "language": "ku/ar/en",
  "location_ok": true
}}
"""

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "Return valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 900,
                    "response_format": {"type": "json_object"}
                }
            ) as resp:
                raw = await resp.text()

                if resp.status != 200:
                    print(f"❌ Groq status: {resp.status}")
                    print(raw[:500])
                    return {
                        "suitable": False,
                        "score": 0,
                        "reason_ku": "هەڵسەنگاندن سەرکەوتوو نەبوو",
                        "job_title_ku": "نەزانراو",
                        "company_ku": "نەزانراو",
                        "city_ku": "نەزانراو",
                        "matched_profile_id": "",
                        "matched_profile_name_ku": "",
                        "matched_skills": [],
                        "summary_ku": "",
                        "requirements_ku": [],
                        "salary_ku": "نەزانراو",
                        "contact_ku": "نەزانراو",
                        "language": "unknown",
                        "location_ok": False
                    }

                data = json.loads(raw)
                content = data["choices"][0]["message"]["content"]
                parsed = extract_json(content)

                if not parsed:
                    print("❌ JSON parse failed")
                    print(content[:500])
                    return {
                        "suitable": False,
                        "score": 0,
                        "reason_ku": "هەڵسەنگاندن سەرکەوتوو نەبوو",
                        "job_title_ku": "نەزانراو",
                        "company_ku": "نەزانراو",
                        "city_ku": "نەزانراو",
                        "matched_profile_id": "",
                        "matched_profile_name_ku": "",
                        "matched_skills": [],
                        "summary_ku": "",
                        "requirements_ku": [],
                        "salary_ku": "نەزانراو",
                        "contact_ku": "نەزانراو",
                        "language": "unknown",
                        "location_ok": False
                    }

                return parsed

    except Exception as e:
        print(f"❌ Groq هەڵە: {e}")
        return {
            "suitable": False,
            "score": 0,
            "reason_ku": "هەڵسەنگاندن سەرکەوتوو نەبوو",
            "job_title_ku": "نەزانراو",
            "company_ku": "نەزانراو",
            "city_ku": "نەزانراو",
            "matched_profile_id": "",
            "matched_profile_name_ku": "",
            "matched_skills": [],
            "summary_ku": "",
            "requirements_ku": [],
            "salary_ku": "نەزانراو",
            "contact_ku": "نەزانراو",
            "language": "unknown",
            "location_ok": False
        }

# ===== Telegram client =====
try:
    client = TelegramClient(StringSession(TELEGRAM_SESSION), API_ID, API_HASH)
except Exception:
    print("❌ TELEGRAM_SESSION دروست نییە")
    sys.exit(1)

@client.on(events.NewMessage(chats=GROUPS))
async def handle_new_message(event):
    message_text = event.message.text or ""
    group_name = event.chat.title if hasattr(event.chat, "title") and event.chat.title else "نەزانراو"

    if len(message_text.strip()) < 20:
        return

    if not contains_job_keyword(message_text):
        return

    if contains_reject_keyword(message_text):
        print(f"❌ ڕەتکرا لەبەر وشەی ناگونجاو: {group_name}")
        return

    if has_excluded_location(message_text):
        print(f"❌ ڕەتکرا لەبەر شارێکی ناخواستراو: {group_name}")
        return

    job_key = make_job_key(message_text, group_name)
    if job_key in seen_jobs:
        print(f"⚠️ دووبارە بوو، نەنێردرا: {group_name}")
        return

    print(f"\n🔍 هەلی کار دۆزراوەتەوە لە: {group_name}")
    print(f"📝 {message_text[:160]}")

    evaluation = await evaluate_job(message_text, group_name)

    if not evaluation.get("location_ok", False):
        print("❌ شوێن گونجاو نییە")
        return

    if not evaluation.get("suitable", False):
        print(f"❌ گونجاو نییە - {evaluation.get('reason_ku', '')}")
        return

    score = int(evaluation.get("score", 0))
    if score < MIN_SCORE:
        print(f"❌ نمرە کەمە ({score}/100)")
        return

    seen_jobs.add(job_key)

    job_title = evaluation.get("job_title_ku", "نەزانراو")
    company = evaluation.get("company_ku", "نەزانراو")
    city = evaluation.get("city_ku", "نەزانراو")
    reason = evaluation.get("reason_ku", "")
    matched_profile = evaluation.get("matched_profile_name_ku", "نەزانراو")
    matched_skills = evaluation.get("matched_skills", [])
    summary_ku = evaluation.get("summary_ku", "")
    requirements_ku = evaluation.get("requirements_ku", [])
    salary_ku = evaluation.get("salary_ku", "نەزانراو")
    contact_ku = evaluation.get("contact_ku", "نەزانراو")

    job_link = (
        f"https://t.me/{event.chat.username}/{event.id}"
        if hasattr(event.chat, "username") and event.chat.username
        else "بەردەست نییە"
    )

    requirements_text = "\n".join([f"- {x}" for x in requirements_ku[:6]]) if requirements_ku else "- نەزانراو"
    skills_text = "، ".join(matched_skills[:6]) if matched_skills else "نەزانراو"

    notification = f"""🟢 هەلی کاری گونجاو دۆزراوەتەوە!

📌 وەزیفە: {job_title}
🏢 کۆمپانیا: {company}
📍 شوێن: {city}
⭐ گونجاوی: {score}/100
👤 profile ی گونجاو: {matched_profile}
🧠 بەهرەی هاوشێوە: {skills_text}
💬 هۆکار: {reason}

📋 پوختە:
{summary_ku}

✅ مەرجە گرنگەکان:
{requirements_text}

💰 موچە: {salary_ku}
☎️ پەیوەندی: {contact_ku}

📢 گرووپ: {group_name}
🔗 لینک: {job_link}

📄 دەقی سەرەکی:
{message_text[:900]}

⏰ کات: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

    await client.send_message(NOTIFY_CHAT, notification)
    print("📨 ئاگادارکردنەوە نێردرا!")

async def main():
    print("🚀 Job Monitor Bot دەستپێدەکات...")
    print(f"👁️ چاودێری {len(GROUPS)} گرووپ دەکات")
    print("=" * 50)

    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError("Telegram session is not authorized")

    me = await client.get_me()
    print(f"✅ لۆگین بوو بە: {me.first_name} (@{me.username})")
    print("⏳ چاودێری دەکات... (Ctrl+C بکە بۆ وەستان)")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
