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
MIN_JOB_LENGTH_FOR_AI = 80
MESSAGE_PRE_DELAY_SECONDS = 2
LLM_SERIAL_DELAY_SECONDS = 1.5

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
        "delivery", "courier", "dispatcher", "messenger",
        "مطعم", "مطبخ", "شيف", "طباخ", "نادل", "تنظيف",
        "سكورتي", "حارس", "خباز", "كوفي", "نانکردن", "چێشتخانە",
        "مەتبەخ", "شێف", "قاپشور", "فاست فود", "خۆراک",
        "گەیاندن", "گەیاندنەوە", "پیک", "دڵیڤەری", "دڵیڤه‌ری", "گەیاندنکار"
    ],
}

# ===== FAST FILTERS =====
REJECT_LOCATION_TERMS = [
    "slimani", "slemani", "sulaymaniyah", "sulaimani", "sulaimaniya",
    "سلێمانی", "سليماني", "السليمانية",
    "duhok", "dohuk", "دهۆک", "دهوك",
    "kirkuk", "kerkuk", "کەرکووک", "كركوك",
    "baghdad", "بغداد",
    "basra", "بصره", "البصرة",
    "mosul", "موصل", "موسڵ"
]

GOOD_FALLBACK_WORDS = [
    "sales", "customer", "reception", "receptionist", "front desk",
    "office", "admin", "crm", "showroom", "cashier", "pos",
    "data entry", "clerk", "storekeeper", "customer service",
    "فرۆش", "فرۆشیار", "پێشواز", "ریسپشن", "ئۆفیس", "ئیداری",
    "کاشێر", "سیستەم", "داتا", "کارمەندی فرۆشتن", "خزمەتگوزاری کڕیار"
]

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
    return text[:1500]

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
        "ai_ok": False,
        "fallback_used": False,
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
        "location_ok": None,
        "reject_reason_code": "ai_failed"
    }

def quick_reject_check(job_text: str) -> dict | None:
    txt = normalize_text(job_text)

    for bad_role in CANDIDATE_PROFILE["rejected_roles"]:
        if normalize_text(bad_role) in txt:
            return {
                "ai_ok": True,
                "fallback_used": False,
                "suitable": False,
                "score": 0,
                "matched_profile_id": "",
                "matched_profile_title": "",
                "job_title_ku": "نەگونجاو",
                "company_ku": "نەزانراو",
                "location_ku": "نەزانراو",
                "reason_ku": f"ڕۆڵەکە پەیوەندیدارە بە: {bad_role}",
                "summary_ku": "",
                "requirements_ku": [],
                "salary_ku": "نەزانراو",
                "contact_ku": "نەزانراو",
                "language": "unknown",
                "location_ok": True,
                "reject_reason_code": "role_rejected"
            }

    for bad_loc in REJECT_LOCATION_TERMS:
        if normalize_text(bad_loc) in txt:
            return {
                "ai_ok": True,
                "fallback_used": False,
                "suitable": False,
                "score": 0,
                "matched_profile_id": "",
                "matched_profile_title": "",
                "job_title_ku": "نەگونجاو",
                "company_ku": "نەزانراو",
                "location_ku": bad_loc,
                "reason_ku": f"شوێنی کار لە ناوچەی دەرەوەی هەولێرە: {bad_loc}",
                "summary_ku": "",
                "requirements_ku": [],
                "salary_ku": "نەزانراو",
                "contact_ku": "نەزانراو",
                "language": "unknown",
                "location_ok": False,
                "reject_reason_code": "location_mismatch"
            }

    return None

def simple_fallback_scoring(text: str) -> dict | None:
    txt = normalize_text(text)
    score = 0

    matched_words = []
    for w in GOOD_FALLBACK_WORDS:
        if normalize_text(w) in txt:
            score += 12
            matched_words.append(w)

    # شوێنی هەولێر بۆ fallback زۆر گرنگە
    preferred_location_found = False
    for loc in CANDIDATE_PROFILE["preferred_locations"]:
        if normalize_text(loc) in txt:
            preferred_location_found = True
            score += 20
            break

    if not preferred_location_found:
        return None

    if score >= 32:
        reason = "fallback بێ AI: وشە گونجاوەکان دۆزرایەوە"
        if matched_words:
            reason += f" ({', '.join(matched_words[:4])})"

        return {
            "ai_ok": False,
            "fallback_used": True,
            "suitable": True,
            "score": min(score, 65),
            "matched_profile_id": "fallback",
            "matched_profile_title": "Fallback Match",
            "job_title_ku": "هەلی کار (fallback)",
            "company_ku": "نەزانراو",
            "location_ku": "هەولێر",
            "reason_ku": reason,
            "summary_ku": "AI بەردەست نەبوو، بڕیار بە شێوەی fallback درا.",
            "requirements_ku": [],
            "salary_ku": "نەزانراو",
            "contact_ku": "نەزانراو",
            "language": "unknown",
            "location_ok": True,
            "reject_reason_code": "fallback_match"
        }

    return None

async def evaluate_job(job_text: str, group_name: str) -> dict:
    fast_reject = quick_reject_check(job_text)
    if fast_reject is not None:
        return fast_reject

    # پۆستە زۆر بچووکەکان مەهێنە بۆ AI
    if len(job_text.strip()) < MIN_JOB_LENGTH_FOR_AI:
        return {
            "ai_ok": True,
            "fallback_used": False,
            "suitable": False,
            "score": 0,
            "matched_profile_id": "",
            "matched_profile_title": "",
            "job_title_ku": "نەگونجاو",
            "company_ku": "نەزانراو",
            "location_ku": "نەزانراو",
            "reason_ku": "دەقی پۆستەکە زۆر کورتە بۆ هەڵسەنگاندنی AI",
            "summary_ku": "",
            "requirements_ku": [],
            "salary_ku": "نەزانراو",
            "contact_ku": "نەزانراو",
            "language": "unknown",
            "location_ok": None,
            "reject_reason_code": "too_short"
        }

    safe_job_text = clean_for_llm(job_text)
    safe_group_name = clean_for_llm(group_name)

    locations_str = ", ".join(CANDIDATE_PROFILE["preferred_locations"][:20])

    prompt = (
        "You are a strict job-matching assistant.\n\n"
        "Evaluate whether this Telegram job post matches the candidate.\n\n"
        f"Candidate base city: Erbil.\n"
        f"Preferred locations: {locations_str}\n\n"
        "Accepted career directions:\n"
        "1. Sales / CRM / Customer Service / Front Desk / Reception\n"
        "2. Real Estate / Property Sales / Leasing\n"
        "3. Cashier / POS / Data Entry / Office Clerk\n\n"
        "Rejected roles include restaurant, kitchen, cleaner, security, guard, medical, teacher, construction, driver-only, delivery and courier.\n\n"
        "Rules:\n"
        "1. Accept only if location is in Erbil or nearby preferred areas.\n"
        "2. If location missing or unclear: suitable=false, location_ok=false.\n"
        "3. If role does not match accepted directions: reject.\n"
        "4. Output valid JSON only. No markdown.\n"
        "5. Always include ai_ok=true in the JSON.\n"
        "6. Add reject_reason_code with one of these values only:\n"
        '   "accepted", "location_mismatch", "role_rejected", "low_score", "unclear".\n\n'
        "Score rules:\n"
        "- 90-100: perfect match\n"
        "- 70-89: good match\n"
        "- below 70: poor match\n\n"
        f"Group: {safe_group_name}\n\n"
        f"Job post:\n{safe_job_text}\n\n"
        "Return valid JSON only. Example:\n"
        '{"ai_ok":true,"suitable":true,"score":85,"matched_profile_id":"sales_crm","matched_profile_title":"Sales and CRM","job_title_ku":"فرۆشیار","company_ku":"کۆمپانیا","location_ku":"هەولێر","reason_ku":"هۆکار","summary_ku":"پوختە","requirements_ku":["مەرج١"],"salary_ku":"موچە","contact_ku":"پەیوەندی","language":"ku","location_ok":true,"reject_reason_code":"accepted"}'
    )

    max_attempts = 5
    backoff_seconds = [5, 10, 20, 40, 60]

    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                wait_time = backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)]
                print(f"⏳ چاوەڕوانی {wait_time} چرکە... (هەوڵ {attempt + 1}/{max_attempts})")
                await asyncio.sleep(wait_time)

            timeout = aiohttp.ClientTimeout(total=60)

            async with llm_lock:
                await asyncio.sleep(LLM_SERIAL_DELAY_SECONDS)

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
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.1,
                            "max_tokens": 500
                        }
                    ) as resp:
                        raw = await resp.text()

                        if resp.status == 429:
                            print(f"⏳ Groq rate limit - چاوەڕوانی... (هەوڵ {attempt + 1}/{max_attempts})")
                            continue

                        if resp.status != 200:
                            print(f"❌ Groq status: {resp.status}")
                            print(f"❌ Groq error: {raw[:500]}")
                            break

                        try:
                            data = json.loads(raw)
                        except Exception:
                            print("❌ Groq response JSON parse failed")
                            break

                        if "choices" not in data or not data["choices"]:
                            print("❌ Groq choices missing")
                            break

                        content = data["choices"][0]["message"]["content"]
                        parsed = extract_json(content)

                        if not parsed:
                            print("❌ JSON parse failed")
                            print(content[:500])
                            break

                        parsed.setdefault("ai_ok", True)
                        parsed.setdefault("fallback_used", False)
                        parsed.setdefault("reject_reason_code", "unclear")
                        parsed.setdefault("location_ok", None)
                        parsed.setdefault("suitable", False)
                        parsed.setdefault("score", 0)
                        parsed.setdefault("matched_profile_id", "")
                        parsed.setdefault("matched_profile_title", "")
                        parsed.setdefault("job_title_ku", "نەزانراو")
                        parsed.setdefault("company_ku", "نەزانراو")
                        parsed.setdefault("location_ku", "نەزانراو")
                        parsed.setdefault("reason_ku", "نەزانراو")
                        parsed.setdefault("summary_ku", "")
                        parsed.setdefault("requirements_ku", [])
                        parsed.setdefault("salary_ku", "نەزانراو")
                        parsed.setdefault("contact_ku", "نەزانراو")
                        parsed.setdefault("language", "unknown")

                        if parsed.get("suitable", False):
                            parsed["reject_reason_code"] = "accepted"
                        elif parsed.get("location_ok") is False:
                            parsed["reject_reason_code"] = "location_mismatch"
                        elif int(parsed.get("score", 0)) < MIN_SCORE:
                            parsed["reject_reason_code"] = "low_score"

                        return parsed

        except Exception as e:
            print(f"❌ Groq هەڵە (هەوڵ {attempt + 1}/{max_attempts}): {e}")

    # AI failed -> fallback
    fallback = simple_fallback_scoring(job_text)
    if fallback:
        print("🟡 fallback بەکارهات بەهۆی AI failure")
        return fallback

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

    # کەمکردنەوەی هێرشی داواکارییەکان
    await asyncio.sleep(MESSAGE_PRE_DELAY_SECONDS)

    print(f"\n🔍 هەلی کار دۆزراوەتەوە لە: {group_name}")
    print(f"📝 {message_text[:220]}")

    evaluation = await evaluate_job(message_text, group_name)

    if not evaluation.get("ai_ok", False) and not evaluation.get("fallback_used", False):
        print(f"⚠️ AI نەتوانی هەڵسەنگاندن تەواو بکات - {evaluation.get('reason_ku', '')}")
        return

    if evaluation.get("location_ok") is False:
        print(f"❌ شوێن گونجاو نییە - {evaluation.get('location_ku', 'نەزانراو')}")
        return

    if not evaluation.get("suitable", False):
        print(f"❌ گونجاو نییە - {evaluation.get('reason_ku', '')}")
        return

    score = int(evaluation.get("score", 0))
    if score < MIN_SCORE and not evaluation.get("fallback_used", False):
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

    fallback_note = ""
    if evaluation.get("fallback_used", False):
        fallback_note = "\n⚠️ ئەم بڕیارە بە fallback دراوە چونکە AI بەردەست نەبوو.\n"

    notification = f"""🟢 هەلی کاری گونجاو دۆزراوەتەوە!

📌 وەزیفە: {job_title}
🏢 کۆمپانیا: {company}
📍 شوێن: {location_ku}
⭐ گونجاوی: {score}/100
👤 Profile: {matched_profile}
💬 هۆکار: {reason_ku}{fallback_note}

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
