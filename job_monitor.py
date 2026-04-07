"""
Job Monitor Bot - Abdulla Ali
Two-stage filtering:
1) Local filter
2) AI filter only for unclear posts
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
from datetime import datetime, timedelta

# ===== ENV =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION", "").strip()

if not TELEGRAM_SESSION:
    print("❌ TELEGRAM_SESSION بەتاڵە")
    sys.exit(1)

# ===== SETTINGS =====
NOTIFY_CHAT = "me"
MIN_SCORE = 70
GROQ_MODEL = "llama-3.3-70b-versatile"
MIN_TEXT_LENGTH = 40
MIN_TEXT_LENGTH_FOR_AI = 80

# AI safety controls
AI_ENABLED = bool(GROQ_API_KEY)
AI_STARTUP_COOLDOWN_SECONDS = 90
AI_MAX_CALLS_PER_5_MIN = 3
AI_WINDOW_SECONDS = 300
AI_MAX_ATTEMPTS = 3
AI_BACKOFF_SECONDS = [10, 30, 60]
AI_SERIAL_DELAY_SECONDS = 2.0

BOT_START_TIME = datetime.now()

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

# ===== JOB KEYWORDS =====
JOB_KEYWORDS = [
    "هەلی کار", "هەلیکاری", "کارمەند", "پێویستمان", "فرصە",
    "وظيفة", "مطلوب", "فرصة عمل", "توظيف", "وظائف",
    "hiring", "vacancy", "job opportunity", "we are looking",
    "position available", "apply now", "recruitment", "opening", "vacancies"
]

# ===== PROFILE =====
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
        "Mosul Road", "ڕێگای مووسڵ", "طريق الموصل",
        "Bakhtiary", "بەختیاری", "Zargata", "زەرگەتە", "Zargata"
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
    ]
}

REJECT_LOCATION_TERMS = [
    "slimani", "slemani", "sulaymaniyah", "sulaimani", "sulaimaniya",
    "سلێمانی", "سليماني", "السليمانية",
    "duhok", "dohuk", "دهۆک", "دهوك",
    "kirkuk", "kerkuk", "کەرکووک", "كركوك",
    "baghdad", "بغداد",
    "basra", "بصره", "البصرة",
    "mosul", "موصل", "موسڵ"
]

DIRECT_ACCEPT_WORDS = [
    "sales", "customer service", "customer", "reception", "receptionist",
    "front desk", "admin", "office", "crm", "cashier", "pos", "data entry",
    "showroom", "storekeeper", "clerk", "marketing", "real estate",
    "فرۆش", "فرۆشیار", "پێشواز", "ریسپشن", "ئۆفیس", "ئیداری",
    "کاشێر", "سیستەم", "داتا", "خزمەتگوزاری کڕیار", "شوورۆم"
]

AI_TRIGGER_WORDS = [
    "travel", "travil", "agency", "tourism", "booking",
    "assistant", "coordinator", "staff", "employee",
    "تراڤڵ", "گەشت", "ئاجانس", "سەیران", "کارمەند", "یارمەتیدەر"
]

seen_jobs = set()
llm_lock = asyncio.Lock()
ai_call_timestamps = []

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
    return text[:1800]

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

def make_result(
    *,
    ai_ok: bool,
    fallback_used: bool,
    suitable: bool,
    score: int,
    reason_ku: str,
    location_ok,
    reject_reason_code: str,
    matched_profile_title: str = "",
    matched_profile_id: str = "",
    job_title_ku: str = "نەزانراو",
    company_ku: str = "نەزانراو",
    location_ku: str = "نەزانراو",
    summary_ku: str = "",
    requirements_ku=None,
    salary_ku: str = "نەزانراو",
    contact_ku: str = "نەزانراو",
    language: str = "unknown",
):
    return {
        "ai_ok": ai_ok,
        "fallback_used": fallback_used,
        "suitable": suitable,
        "score": score,
        "matched_profile_id": matched_profile_id,
        "matched_profile_title": matched_profile_title,
        "job_title_ku": job_title_ku,
        "company_ku": company_ku,
        "location_ku": location_ku,
        "reason_ku": reason_ku,
        "summary_ku": summary_ku,
        "requirements_ku": requirements_ku or [],
        "salary_ku": salary_ku,
        "contact_ku": contact_ku,
        "language": language,
        "location_ok": location_ok,
        "reject_reason_code": reject_reason_code
    }

def quick_reject_check(job_text: str):
    txt = normalize_text(job_text)

    for bad_role in CANDIDATE_PROFILE["rejected_roles"]:
        if normalize_text(bad_role) in txt:
            return make_result(
                ai_ok=True,
                fallback_used=False,
                suitable=False,
                score=0,
                reason_ku=f"ڕۆڵەکە پەیوەندیدارە بە: {bad_role}",
                location_ok=True,
                reject_reason_code="role_rejected",
                job_title_ku="نەگونجاو"
            )

    for bad_loc in REJECT_LOCATION_TERMS:
        if normalize_text(bad_loc) in txt:
            return make_result(
                ai_ok=True,
                fallback_used=False,
                suitable=False,
                score=0,
                reason_ku=f"شوێنی کار لە ناوچەی دەرەوەی هەولێرە: {bad_loc}",
                location_ok=False,
                reject_reason_code="location_mismatch",
                location_ku=bad_loc,
                job_title_ku="نەگونجاو"
            )

    return None

def direct_accept_check(job_text: str):
    txt = normalize_text(job_text)

    preferred_location_found = any(
        normalize_text(loc) in txt
        for loc in CANDIDATE_PROFILE["preferred_locations"]
    )

    if not preferred_location_found:
        return None

    matched_good = [
        w for w in DIRECT_ACCEPT_WORDS
        if normalize_text(w) in txt
    ]

    if len(matched_good) >= 2:
        return make_result(
            ai_ok=True,
            fallback_used=False,
            suitable=True,
            score=78,
            reason_ku=f"local match: {', '.join(matched_good[:3])}",
            location_ok=True,
            reject_reason_code="accepted_direct",
            matched_profile_title="Local Match",
            matched_profile_id="local_match",
            job_title_ku="هەلی کار",
            location_ku="هەولێر",
            summary_ku="بڕیار بە شێوەی local filter دراوە، بێ پێویستی بە AI."
        )

    return None

def should_use_ai(job_text: str) -> bool:
    txt = normalize_text(job_text)

    if len(job_text.strip()) < MIN_TEXT_LENGTH_FOR_AI:
        return False

    preferred_location_found = any(
        normalize_text(loc) in txt
        for loc in CANDIDATE_PROFILE["preferred_locations"]
    )

    if not preferred_location_found:
        return False

    strong_signal_count = 0
    for w in DIRECT_ACCEPT_WORDS + AI_TRIGGER_WORDS:
        if normalize_text(w) in txt:
            strong_signal_count += 1

    return strong_signal_count >= 1

def simple_fallback_scoring(job_text: str):
    txt = normalize_text(job_text)

    preferred_location_found = any(
        normalize_text(loc) in txt
        for loc in CANDIDATE_PROFILE["preferred_locations"]
    )

    if not preferred_location_found:
        return None

    score = 0
    matched_words = []

    for w in DIRECT_ACCEPT_WORDS + AI_TRIGGER_WORDS:
        if normalize_text(w) in txt:
            score += 10
            matched_words.append(w)

    if score >= 20:
        return make_result(
            ai_ok=False,
            fallback_used=True,
            suitable=True,
            score=min(score + 20, 68),
            reason_ku=f"fallback بێ AI ({', '.join(matched_words[:4])})" if matched_words else "fallback بێ AI",
            location_ok=True,
            reject_reason_code="fallback_match",
            matched_profile_title="Fallback Match",
            matched_profile_id="fallback",
            job_title_ku="هەلی کار (fallback)",
            location_ku="هەولێر",
            summary_ku="AI بەردەست نەبوو، بڕیار بە شێوەی fallback درا."
        )

    return None

def ai_startup_cooldown_active() -> bool:
    return (datetime.now() - BOT_START_TIME).total_seconds() < AI_STARTUP_COOLDOWN_SECONDS

def ai_rate_window_available() -> bool:
    global ai_call_timestamps
    now = datetime.now()
    ai_call_timestamps = [
        ts for ts in ai_call_timestamps
        if (now - ts).total_seconds() < AI_WINDOW_SECONDS
    ]
    return len(ai_call_timestamps) < AI_MAX_CALLS_PER_5_MIN

def register_ai_call():
    ai_call_timestamps.append(datetime.now())

async def evaluate_with_ai(job_text: str, group_name: str):
    if not AI_ENABLED:
        return None

    if ai_startup_cooldown_active():
        print("⏳ AI startup cooldown چالاکە")
        return None

    if not ai_rate_window_available():
        print("⏳ AI window limit گەیشتووە - fallback بەکاربهێنە")
        return None

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

    for attempt in range(AI_MAX_ATTEMPTS):
        try:
            if attempt > 0:
                wait_time = AI_BACKOFF_SECONDS[min(attempt - 1, len(AI_BACKOFF_SECONDS) - 1)]
                print(f"⏳ چاوەڕوانی {wait_time} چرکە... (هەوڵ {attempt + 1}/{AI_MAX_ATTEMPTS})")
                await asyncio.sleep(wait_time)

            timeout = aiohttp.ClientTimeout(total=60)

            async with llm_lock:
                await asyncio.sleep(AI_SERIAL_DELAY_SECONDS)
                register_ai_call()

                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": GROQ_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.1,
                            "max_tokens": 500
                        }
                    ) as resp:
                        raw = await resp.text()

                        if resp.status == 429:
                            print(f"⏳ Groq rate limit - چاوەڕوانی... (هەوڵ {attempt + 1}/{AI_MAX_ATTEMPTS})")
                            continue

                        if resp.status != 200:
                            print(f"❌ Groq status: {resp.status}")
                            print(f"❌ Groq error: {raw[:400]}")
                            return None

                        try:
                            data = json.loads(raw)
                        except Exception:
                            print("❌ Groq response JSON parse failed")
                            return None

                        if "choices" not in data or not data["choices"]:
                            print("❌ Groq choices missing")
                            return None

                        content = data["choices"][0]["message"]["content"]
                        parsed = extract_json(content)

                        if not parsed:
                            print("❌ JSON parse failed")
                            print(content[:400])
                            return None

                        parsed.setdefault("ai_ok", True)
                        parsed.setdefault("fallback_used", False)
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
                        parsed.setdefault("location_ok", None)
                        parsed.setdefault("reject_reason_code", "unclear")

                        return parsed

        except Exception as e:
            print(f"❌ Groq هەڵە (هەوڵ {attempt + 1}/{AI_MAX_ATTEMPTS}): {e}")

    return None

async def evaluate_job(job_text: str, group_name: str):
    # Stage 1: direct reject
    fast_reject = quick_reject_check(job_text)
    if fast_reject is not None:
        return fast_reject

    # Stage 2: direct accept
    direct_accept = direct_accept_check(job_text)
    if direct_accept is not None:
        return direct_accept

    # short text reject
    if len(job_text.strip()) < MIN_TEXT_LENGTH:
        return make_result(
            ai_ok=True,
            fallback_used=False,
            suitable=False,
            score=0,
            reason_ku="دەقی پۆستەکە زۆر کورتە",
            location_ok=None,
            reject_reason_code="too_short",
            job_title_ku="نەگونجاو"
        )

    # Stage 3: AI only for unclear but promising posts
    if should_use_ai(job_text):
        ai_result = await evaluate_with_ai(job_text, group_name)
        if ai_result is not None:
            return ai_result

    # Stage 4: fallback
    fallback = simple_fallback_scoring(job_text)
    if fallback is not None:
        print("🟡 fallback بەکارهات")
        return fallback

    return make_result(
        ai_ok=False,
        fallback_used=False,
        suitable=False,
        score=0,
        reason_ku="نە AI بەردەست بوو نە local score گونجاو بوو",
        location_ok=None,
        reject_reason_code="unresolved",
        job_title_ku="نەگونجاو"
    )

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

    if evaluation.get("location_ok") is False:
        print(f"❌ شوێن گونجاو نییە - {evaluation.get('location_ku', 'نەزانراو')}")
        return

    if not evaluation.get("suitable", False):
        if not evaluation.get("ai_ok", True) and not evaluation.get("fallback_used", False):
            print(f"⚠️ AI نەتوانی هەڵسەنگاندن تەواو بکات - {evaluation.get('reason_ku', '')}")
        else:
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

    note = ""
    if evaluation.get("fallback_used", False):
        note = "\n⚠️ ئەم بڕیارە بە fallback/local rule دراوە.\n"
    elif evaluation.get("ai_ok", False):
        note = "\n🤖 ئەم پۆستە لە فلتەری AI ـیش دەرچووە.\n"

    notification = f"""🟢 هەلی کاری گونجاو دۆزراوەتەوە!

📌 وەزیفە: {job_title}
🏢 کۆمپانیا: {company}
📍 شوێن: {location_ku}
⭐ گونجاوی: {score}/100
👤 Profile: {matched_profile}
💬 هۆکار: {reason_ku}{note}

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
    if AI_ENABLED:
        print(f"⏳ AI cooldown بۆ {AI_STARTUP_COOLDOWN_SECONDS} چرکە چالاکە")
    else:
        print("⚠️ GROQ_API_KEY نەدۆزرایەوە - AI ناچالاکە")
    print("⏳ چاودێری دەکات... (Ctrl+C بکە بۆ وەستان)")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
