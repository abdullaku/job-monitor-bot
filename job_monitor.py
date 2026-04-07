"""
Job Monitor Bot - Abdulla Ali
AI-first Telegram Job Monitor
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

# ===== ENV =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION", "").strip()

if not TELEGRAM_SESSION:
    print("❌ TELEGRAM_SESSION بەتاڵە")
    sys.exit(1)

# ===== SETTINGS =====
NOTIFY_CHAT = "me"
MIN_SCORE = 70
GROQ_MODEL = "llama-3.3-70b-versatile"

# ===== GROUPS =====
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

# ===== KEYWORDS =====
JOB_KEYWORDS = [
    "هەلی کار", "هەلیکاری", "کارمەند", "پێویستمان", "فرصە",
    "وظيفة", "مطلوب", "فرصة عمل", "توظيف", "وظائف",
    "hiring", "vacancy", "job opportunity", "we are looking",
    "position available", "apply now", "recruitment",
    "job title", "location", "opening", "vacancies"
]

# ===== STRUCTURED CANDIDATE PROFILE =====
CANDIDATE_PROFILE = {
    "name": "Abdulla Ali",
    "base_city": "Erbil",
    "preferred_locations": [
        "Erbil", "Hawler", "هەولێر", "هاولێر", "ئەربیل", "أربيل",
        "Ankawa", "عنكاوه", "عەنکاوە", "Baharka", "بەحرکە", "بحركة",
        "Kasnazan", "کەسنەزان", "Kesnazan",
        "Rzgari", "Rizgari", "ڕزگاری",
        "60 Meter", "60m", "شەست مەتری", "60 متري",
        "Gullan", "گولەن", "گولان",
        "Empire", "ئیمپایەر",
        "Italian City", "ئیتاڵی",
        "Dream City", "دریم سیتی",
        "English Village", "قریەی ئینگلیز", "قرية الإنجليز",
        "New Erbil", "هەولێری نوێ",
        "Farmanbaran", "فەرمانبەران",
        "Mosul Road", "ڕێگای مووسڵ", "طريق الموصل"
    ],
    "languages": {
        "kurdish": "native",
        "arabic": "good",
        "english": "intermediate"
    },
    "education": [
        "Bachelor - Salahaddin University - 2025"
    ],
    "driver_license": True,
    "core_profiles": [
        {
            "id": "sales_crm",
            "title": "Sales and CRM",
            "priority": 1,
            "skills": [
                "sales", "direct sales", "customer service", "crm",
                "client relationship", "marketing", "branding",
                "social media", "reporting", "negotiation",
                "showroom", "front desk", "computer sales",
                "sales and accounting", "retail sales"
            ],
            "accepted_roles": [
                "sales representative", "sales executive", "sales staff",
                "crm officer", "customer service", "marketing assistant",
                "showroom staff", "admin sales", "front desk sales",
                "computer sales", "sales and accounting",
                "sales coordinator", "sales admin", "customer care",
                "call center", "receptionist", "front desk",
                "customer service", "warehouse clerk", "storekeeper"
            ]
        },
        {
            "id": "real_estate",
            "title": "Real Estate and Property Relations",
            "priority": 2,
            "skills": [
                "real estate", "property sales", "client handling",
                "negotiation", "property presentation", "contracts",
                "market analysis", "lead follow-up", "leasing",
                "broker", "property consultant"
            ],
            "accepted_roles": [
                "real estate agent", "property consultant",
                "sales consultant", "leasing assistant",
                "property coordinator", "broker",
                "property sales", "real estate sales"
            ]
        },
        {
            "id": "system_cashier",
            "title": "Cashier POS and System Handling",
            "priority": 3,
            "skills": [
                "cashier", "pos", "system handling", "microsoft office",
                "record keeping", "payment handling", "daily reports",
                "customer support", "computer skills", "data entry",
                "office clerk", "system operator"
            ],
            "accepted_roles": [
                "cashier", "pos operator", "store cashier",
                "computer operator", "data entry", "office clerk",
                "system operator", "reception", "front desk",
                "admin assistant", "computer clerk"
            ]
        }
    ],
    "rejected_roles": [
        "chef", "cook", "kitchen", "waiter", "restaurant", "cleaner",
        "security", "guard", "factory worker", "teacher", "doctor",
        "nurse", "medical specialist", "driver only", "construction labor",
        "baker", "barista", "dishwasher", "housekeeping", "janitor",
        "مطعم", "مطبخ", "شيف", "طباخ", "نادل", "تنظيف",
        "سكورتي", "حارس", "خباز", "كوفي", "نانکردن", "چێشتخانە",
        "مەتبەخ", "شێف", "قاپشور", "فاست فود", "خۆراک"
    ],
}

seen_jobs = set()
llm_lock = asyncio.Lock()

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ى": "ی", "ؤ": "و", "ئ": "ی",
        "\n": " ", "\r": " ", "\t": " "
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text)
    return text

def clean_for_llm(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2500]

def contains_job_keyword(text: str) -> bool:
    txt = normalize_text(text)
    return any(normalize_text(k) in txt for k in JOB_KEYWORDS)

def make_job_key(message_text: str, group_name: str) -> str:
    base = f"{group_name}|{message_text[:1500]}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def extract_json(text: str):
    if not text:
        return None
    cleaned = text.strip()

    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts:
            p = part.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{") and p.endswith("}"):
                try:
                    return json.loads(p)
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

def fallback_result(reason: str = "هەڵسەنگاندن سەرکەوتوو نەبوو") -> dict:
    return {
        "suitable": False,
        "score": 0,
        "matched_profile_id": "",
        "matched_profile_title": "",
        "job_title_ku": "نەزانراو",
        "company_ku": "نەزانراو",
        "location_ku": "نەزانراو",
        "reason_ku": reason,
        "summary_ku": "",
        "requirements_ku": [],
        "salary_ku": "نەزانراو",
        "contact_ku": "نەزانراو",
        "language": "unknown",
        "location_ok": False
    }

async def evaluate_job(job_text: str, group_name: str) -> dict:
    safe_job_text = clean_for_llm(job_text)
    safe_group_name = clean_for_llm(group_name)

    prompt = f"""
You are a strict job-matching assistant.

Evaluate whether this Telegram job post matches the candidate.

Candidate base city: Erbil.

Preferred locations:
{", ".join(CANDIDATE_PROFILE["preferred_locations"][:25])}

Main accepted career directions:
1. Sales / CRM / Customer Service / Front Desk / Reception
2. Real Estate / Property Sales / Leasing / Client Relations
3. Cashier / POS / Office Clerk / Data Entry / System Handling

Rejected career directions:
restaurant, kitchen, food service, cleaner, security, guard, medical specialist, teacher, construction, driver-only.

Rules:
1. Accept only if location is clearly in Erbil or nearby preferred areas.
2. If location is missing or unclear, set suitable=false and location_ok=false.
3. If role does not match the accepted career directions, reject.
4. If role matches rejected directions, reject.
5. If post is English or Arabic, summarize in Kurdish Sorani.
6. If unsure, reject.
7. Output valid JSON only.

Group:
{safe_group_name}

Job post:
{safe_job_text}

Return exactly this JSON format:
{{
  "suitable": true,
  "score": 0,
  "matched_profile_id": "",
  "matched_profile_title": "",
  "job_title_ku": "",
  "company_ku": "",
  "location_ku": "",
  "reason_ku": "",
  "summary_ku": "",
  "requirements_ku": [],
  "salary_ku": "",
  "contact_ku": "",
  "language": "",
  "location_ok": true
}}
""".strip()

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with llm_lock:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": [
                            {"role": "system", "content": "Return valid JSON only. No markdown."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 700
                    }
                ) as resp:
                    raw = await resp.text()

                    if resp.status != 200:
                        print(f"❌ Groq status: {resp.status}")
                        print(raw[:1000])
                        return fallback_result(f"Groq request failed: {resp.status}")

                    try:
                        data = json.loads(raw)
                    except Exception:
                        print("❌ Groq response JSON parse failed")
                        print(raw[:1000])
                        return fallback_result("Groq response parse failed")

                    if "choices" not in data or not data["choices"]:
                        print("❌ Groq choices missing")
                        print(raw[:1000])
                        return fallback_result("Groq choices missing")

                    content = data["choices"][0]["message"]["content"]
                    parsed = extract_json(content)

                    if not parsed:
                        print("❌ JSON parse failed")
                        print(content[:1000])
                        return fallback_result("JSON parse failed")

                    return parsed

    except Exception as e:
        print(f"❌ Groq هەڵە: {e}")
        return fallback_result("هەڵسەنگاندنی AI سەرکەوتوو نەبوو")

client = TelegramClient(StringSession(TELEGRAM_SESSION), API_ID, API_HASH)

@client.on(events.NewMessage(chats=GROUPS))
async def handle_new_message(event):
    message_text = event.raw_text or ""
    group_name = event.chat.title if getattr(event, "chat", None) and getattr(event.chat, "title", None) else "نەزانراو"

    if len(message_text.strip()) < 20:
        return

    if not contains_job_keyword(message_text):
        return

    job_key = make_job_key(message_text, group_name)
    if job_key in seen_jobs:
        return

    print(f"\n🔍 هەلی کار دۆزراوەتەوە لە: {group_name}")
    print(f"📝 {message_text[:220]}")

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
    location_ku = evaluation.get("location_ku", "نەزانراو")
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
📍 شوێن: {location_ku}
⭐ گونجاوی: {score}/100
👤 Profile: {matched_profile}
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
