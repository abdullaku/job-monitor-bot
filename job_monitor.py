"""
Job Monitor Bot - Abdulla Ali
Local-only filter (No AI)

Rules:
1) No AI / No fallback / No retry
2) Send only jobs with score >= 70
3) City:
   - Only Erbil / Hawler and Erbil areas are accepted
   - If another city is mentioned -> reject
   - If city is missing -> okay, continue evaluation
4) Gender:
   - Candidate is male
   - Female-only jobs are rejected
   - If gender is missing -> okay, continue evaluation
5) Job role:
   - Must be within CV scope only
"""

from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import json
import os
import sys
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

# ===== ENV =====
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION", "").strip()

if not TELEGRAM_SESSION:
    print("❌ TELEGRAM_SESSION بەتاڵە")
    sys.exit(1)

# ===== SETTINGS =====
NOTIFY_CHAT = "me"
MIN_SCORE = 70
MIN_TEXT_LENGTH = 40

SEEN_JOBS_FILE = Path(os.environ.get("SEEN_JOBS_FILE", "/tmp/job_seen_jobs.json"))
SEEN_JOBS_TTL_HOURS = 72

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
    "هەلی کار", "هەلیکاری", "کارمەند", "پێویستمان", "فرصە", "ئیش", "شوێنی کار",
    "وظيفة", "مطلوب", "فرصة عمل", "توظيف", "وظائف", "شاغر",
    "hiring", "vacancy", "job opportunity", "we are hiring", "we are looking",
    "position available", "opening", "vacancies", "job", "position"
]

SUPPORT_SIGNAL_TERMS = [
    "salary", "experience", "requirements", "qualification", "location", "address",
    "cv", "resume", "apply", "full-time", "part-time", "shift", "contact", "phone",
    "موچە", "ئەزموون", "مەرج", "شوێن", "ناونیشان", "سیڤی", "پەیوەندی", "ژمارە",
    "راتب", "خبرة", "المتطلبات", "العنوان", "السيرة", "التقديم", "رقم"
]

# ===== PROFILE =====
CANDIDATE_PROFILE = {
    "name": "Abdulla Ali",
    "gender": "male",
    "base_city": "Erbil",
    "preferred_locations": [
        "erbil", "hawler", "hawlêr", "هەولێر", "هاولێر", "ئەربیل", "أربيل",
        "ankawa", "عنكاوه", "عەنکاوە",
        "baharka", "bahrka", "بەحرکە", "بحركة",
        "kasnazan", "kesnazan", "کەسنەزان",
        "rzgari", "rizgari", "ڕزگاری",
        "60 meter", "60m", "60 m", "شەست مەتری", "60 متري",
        "gullan", "golan", "گولەن", "گولان",
        "empire", "ئیمپایەر",
        "italian city", "ئیتاڵی",
        "dream city", "دریم سیتی",
        "english village", "قریەی ئینگلیز", "قرية الإنجليز",
        "new erbil", "هەولێری نوێ",
        "farmanbaran", "فەرمانبەران",
        "mosul road", "ڕێگای مووسڵ", "طريق الموصل",
        "bakhtiary", "بەختیاری",
        "zargata", "زەرگەتە",
        "32 park", "32 پارک",
        "40 meter", "40m", "40 m", "چل مەتری", "40 متري"
    ],
    "role_profiles": [
        {
            "id": "sales_crm_customer_service",
            "title": "فرۆشتن / CRM / خزمەتگوزاری کڕیار",
            "keywords": [
                "sales", "salesman", "sales rep", "sales representative", "sales executive",
                "sales officer", "sales consultant", "customer service", "customer care",
                "customer support", "crm", "client relation", "client relations",
                "front desk", "reception", "receptionist", "call center", "telesales",
                "retail sales", "showroom", "shop assistant", "client service",
                "فرۆش", "فرۆشیار", "فرۆشتن", "پەیوەندی", "پەیوەندی کردن",
                "خزمەتگوزاری کڕیار", "کڕیار", "پێشواز", "ریسپشن", "شوورۆم",
                "مبيعات", "مبيع", "خدمة العملاء", "استقبال", "كول سنتر", "علاقات العملاء"
            ]
        },
        {
            "id": "real_estate_property",
            "title": "خانووبەرە / فرۆشتنی موڵک",
            "keywords": [
                "real estate", "property", "leasing", "lease", "property sales",
                "property consultant", "property advisor", "real estate sales",
                "real estate agent", "real estate consultant",
                "خانووبەرە", "موڵک", "عقارات", "عقار", "ایجار", "كراء",
                "بیع العقارات", "تأجير", "مستشار عقاري"
            ]
        },
        {
            "id": "cashier_pos",
            "title": "کاشێر / POS",
            "keywords": [
                "cashier", "cash", "pos", "point of sale", "billing", "checkout",
                "card payment", "bank card", "till",
                "کاشێر", "کاش", "سیستەمی فرۆشتن", "پۆس", "پارە وەرگرتن",
                "كاشير", "نقطة بيع", "كارت بنكي", "دفع"
            ]
        },
        {
            "id": "office_admin_data_entry",
            "title": "ئۆفیس / ئیداری / داتا ئێنتری",
            "keywords": [
                "admin", "administrator", "administrative", "office", "office assistant",
                "clerk", "data entry", "document control", "documentation", "back office",
                "coordinator", "assistant", "secretary", "operations assistant",
                "microsoft office", "excel", "word",
                "ئیداری", "ئۆفیس", "داتا", "داتا ئێنتری", "نووسەر", "بەڕێوەبەرایەتی",
                "یارمەتیدەری ئۆفیس", "بەڵگەنامە", "کۆردیناتەر",
                "اداري", "ادارة", "مكتب", "ادخال بيانات", "سكرتير", "منسق"
            ]
        },
        {
            "id": "marketing_branding_social_media",
            "title": "مارکێتینگ / براندینگ / سۆشیال میدیا",
            "keywords": [
                "marketing", "branding", "brand", "social media", "digital marketing",
                "content", "content creator", "promotion", "campaign", "media",
                "مارکێتینگ", "براندینگ", "براند", "سۆشیال میدیا", "دیجیتاڵ",
                "ناساندن", "پڕۆمۆشن",
                "تسويق", "علامة تجارية", "سوشيال ميديا", "ميديا", "حملة"
            ]
        }
    ],
    "rejected_roles": [
        "chef", "cook", "kitchen", "waiter", "restaurant", "cleaner", "cleaning",
        "security", "guard", "factory worker", "teacher", "doctor", "nurse",
        "medical", "driver", "construction", "labor", "barista", "dishwasher",
        "housekeeping", "janitor", "delivery", "courier", "messenger", "welder",
        "engineer", "civil engineer", "electrical engineer", "mechanical engineer",
        "accountant", "accounting", "finance", "hr manager", "human resources specialist",
        "مطعم", "مطبخ", "شيف", "طباخ", "نادل", "تنظيف", "سكورتي", "حارس",
        "معلم", "مدرس", "طبيب", "ممرض", "سائق", "بناء", "عامل", "توصيل",
        "كوفي", "قاپشور", "فاست فود", "خۆراک", "گەیاندن", "پیک", "دڵیڤەری",
        "ئەندازیار", "موحاسب", "محاسب", "حاسبات", "هەژمار", "دارایی"
    ]
}

REJECT_LOCATION_TERMS = [
    "slimani", "slemani", "sulaymaniyah", "sulaimani", "sulaimaniya",
    "سلێمانی", "سليماني", "السليمانية",
    "duhok", "dohuk", "دهۆک", "دهوك",
    "kirkuk", "kerkuk", "کەرکووک", "كركوك",
    "baghdad", "بغداد",
    "basra", "بصره", "البصرة",
    "mosul city", "city of mosul", "موصل", "موسڵ"
]

FEMALE_ONLY_TERMS = [
    "female only", "female", "women only", "woman only", "girls only", "lady", "ladies",
    "for women", "for girls",
    "مێ", "مێینە", "کچ", "ئافرەت", "خانم",
    "انثى", "للنساء", "للبنات", "نساء", "بنات", "سيدة"
]

MALE_ONLY_TERMS = [
    "male only", "male", "men only", "for men",
    "نێر", "پیاو",
    "ذكر", "للرجال", "رجال"
]

BOTH_GENDERS_TERMS = [
    "both genders", "male and female", "men and women", "all genders",
    "هەردوو ڕەگەز", "بۆ هەردوو ڕەگەز", "نێر و مێ",
    "للجنسين", "للذكور والاناث", "ذكر وانثى"
]

FULL_TIME_TERMS = [
    "full-time", "full time", "permanent", "office hours",
    "کاتی تەواو", "تمام کات", "کامل", "دوام کامل",
    "دوام كامل", "fulltime"
]

PART_TIME_TERMS = [
    "part-time", "part time",
    "پارت تایم", "نیمەکات", "دوام جزيي",
    "دوام جزئي", "parttime"
]

SHIFT_TERMS = [
    "shift", "evening shift", "night shift", "morning shift", "rotational",
    "شەفت", "شێفت", "ئێواران", "بەیانیان",
    "ورديه", "ورديات", "مسائي", "صباحي"
]

CONTRACT_TERMS = [
    "contract", "temporary", "project-based", "project based",
    "گرێبەست", "کاتی", "پڕۆژە", "پروژه",
    "عقد", "مؤقت"
]

INTERNSHIP_TERMS = [
    "internship", "intern", "trainee", "training",
    "ڕاهێنان", "فێرخواز", "ستاج", "انترن",
    "تدريب", "متدرب"
]

# ===== RUNTIME =====
seen_jobs = {}


# ===== HELPERS =====
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    replacements = {
        "أ": "ا", "إ": "ا", "آ": "ا",
        "ة": "ه", "ى": "ی", "ؤ": "و",
        "\n": " ", "\r": " ", "\t": " ",
        "–": "-", "—": "-", "_": " "
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_term(text: str, term: str) -> bool:
    txt = normalize_text(text)
    t = normalize_text(term)
    if not txt or not t:
        return False

    # safer matching for short English terms like POS
    if re.fullmatch(r"[a-z0-9 /+\-\.]+", t):
        pattern = r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])"
        return re.search(pattern, txt) is not None

    return t in txt


def find_terms(text: str, terms):
    matched = []
    seen = set()
    for term in terms:
        if contains_term(text, term):
            key = normalize_text(term)
            if key not in seen:
                matched.append(term)
                seen.add(key)
    return matched


def contains_job_keyword(text: str) -> bool:
    keyword_hits = len(find_terms(text, JOB_KEYWORDS))
    support_hits = len(find_terms(text, SUPPORT_SIGNAL_TERMS))
    return keyword_hits >= 2 or (keyword_hits >= 1 and support_hits >= 1)


def make_job_key(message_text: str, group_name: str) -> str:
    base = f"{group_name}|{message_text[:1800]}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def cleanup_seen_jobs(save=False):
    global seen_jobs
    now = datetime.now()
    cutoff = now - timedelta(hours=SEEN_JOBS_TTL_HOURS)

    cleaned = {}
    for key, dt_str in seen_jobs.items():
        try:
            dt = datetime.fromisoformat(dt_str)
            if dt >= cutoff:
                cleaned[key] = dt_str
        except Exception:
            continue

    seen_jobs = cleaned

    if save:
        save_seen_jobs()


def load_seen_jobs():
    global seen_jobs
    if not SEEN_JOBS_FILE.exists():
        seen_jobs = {}
        return

    try:
        seen_jobs = json.loads(SEEN_JOBS_FILE.read_text(encoding="utf-8"))
        if not isinstance(seen_jobs, dict):
            seen_jobs = {}
    except Exception:
        seen_jobs = {}

    cleanup_seen_jobs(save=False)


def save_seen_jobs():
    try:
        SEEN_JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SEEN_JOBS_FILE.write_text(
            json.dumps(seen_jobs, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"⚠️ نەتوانرا seen_jobs پاشەکەوت بکرێت: {e}")


def is_seen(job_key: str) -> bool:
    cleanup_seen_jobs(save=False)
    return job_key in seen_jobs


def mark_seen(job_key: str):
    seen_jobs[job_key] = datetime.now().isoformat()
    cleanup_seen_jobs(save=True)


def detect_language(text: str) -> str:
    if re.search(r"[\u0600-\u06FF]", text):
        if any(ch in text for ch in ["ە", "ێ", "ۆ", "ڵ", "ڕ"]):
            return "ku"
        return "ar"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def make_result(
    *,
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
    gender_ku: str = "نەزانراو",
    job_type_ku: str = "نەزانراو",
    summary_ku: str = "",
    requirements_ku=None,
    salary_ku: str = "نەزانراو",
    contact_ku: str = "نەزانراو",
    language: str = "unknown",
):
    return {
        "suitable": suitable,
        "score": score,
        "matched_profile_id": matched_profile_id,
        "matched_profile_title": matched_profile_title,
        "job_title_ku": job_title_ku,
        "company_ku": company_ku,
        "location_ku": location_ku,
        "gender_ku": gender_ku,
        "job_type_ku": job_type_ku,
        "reason_ku": reason_ku,
        "summary_ku": summary_ku,
        "requirements_ku": requirements_ku or [],
        "salary_ku": salary_ku,
        "contact_ku": contact_ku,
        "language": language,
        "location_ok": location_ok,
        "reject_reason_code": reject_reason_code
    }


def extract_lines(text: str):
    raw_lines = text.splitlines()
    lines = []
    for line in raw_lines:
        s = line.strip()
        if s:
            lines.append(s)
    return lines


def extract_job_title(text: str) -> str:
    lines = extract_lines(text)

    patterns = [
        r"(?:job title|position|title)\s*[:\-]\s*(.+)",
        r"(?:ناوی پۆست|پۆست|وەزیفە)\s*[:\-]\s*(.+)",
        r"(?:المسمى الوظيفي|الوظيفة)\s*[:\-]\s*(.+)",
    ]

    for line in lines[:12]:
        for pattern in patterns:
            m = re.search(pattern, normalize_text(line), re.IGNORECASE)
            if m:
                title = m.group(1).strip(" -:|")
                if len(title) >= 2:
                    return line.split(":")[-1].strip()

    for line in lines[:10]:
        if len(line) <= 90 and any(contains_term(line, kw) for kw in JOB_KEYWORDS):
            continue
        if len(line) <= 90:
            for profile in CANDIDATE_PROFILE["role_profiles"]:
                if find_terms(line, profile["keywords"]):
                    return line

    return "نەزانراو"


def extract_company(text: str) -> str:
    lines = extract_lines(text)

    patterns = [
        r"(?:company|company name)\s*[:\-]\s*(.+)",
        r"(?:کۆمپانیا|ناوی کۆمپانیا)\s*[:\-]\s*(.+)",
        r"(?:شركة|اسم الشركة)\s*[:\-]\s*(.+)",
    ]

    for line in lines[:20]:
        nline = normalize_text(line)
        for pattern in patterns:
            m = re.search(pattern, nline, re.IGNORECASE)
            if m:
                raw = line.split(":")[-1].strip(" -")
                if raw:
                    return raw

    for line in lines[:15]:
        if "company" in normalize_text(line) or "کۆمپانیا" in normalize_text(line) or "شركة" in normalize_text(line):
            return line

    return "نەزانراو"


def extract_salary(text: str) -> str:
    patterns = [
        r"(\$+\s?\d[\d,\.]*)",
        r"(\d[\d,\.]*\s?(?:usd|iqd|dollar|dinar))",
        r"(?:salary|راتب|موچە)\s*[:\-]?\s*([^\n]{1,50})",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    return "نەزانراو"


def extract_contact(text: str) -> str:
    phones = re.findall(r"(?:\+?964|0)7\d{9}", text)
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)

    parts = []
    if phones:
        parts.extend(list(dict.fromkeys(phones))[:2])
    if emails:
        parts.extend(list(dict.fromkeys(emails))[:2])

    if parts:
        return " | ".join(parts)

    return "نەزانراو"


def extract_requirements(text: str):
    lines = extract_lines(text)
    out = []

    markers = [
        "requirements", "qualification", "qualifications", "skills", "responsibilities",
        "مەرج", "مەرجەکان", "تواناکان", "ئەرکەکان",
        "المتطلبات", "المؤهلات", "المهارات", "المسؤوليات"
    ]

    capture = False
    for line in lines:
        nline = normalize_text(line)

        if any(marker in nline for marker in markers):
            capture = True
            continue

        if capture:
            if len(out) >= 6:
                break
            if line.startswith(("•", "-", "*", "▪", "🔹", "✔")) or len(line) <= 120:
                out.append(line)

        if not capture and line.startswith(("•", "-", "*", "▪", "🔹", "✔")):
            if len(out) < 6:
                out.append(line.lstrip("•-*▪🔹✔ ").strip())

    cleaned = []
    for item in out:
        s = item.strip().lstrip("•-*▪🔹✔ ").strip()
        if s and s not in cleaned:
            cleaned.append(s)

    return cleaned[:6]


def extract_location(job_text: str):
    txt = normalize_text(job_text)

    # protect Erbil areas like Mosul Road
    protected = [
        "mosul road", "ڕێگای مووسڵ", "طريق الموصل"
    ]
    protected_found = any(contains_term(txt, p) for p in protected)

    rejected = []
    for bad in REJECT_LOCATION_TERMS:
        if bad in ["mosul city", "city of mosul", "موصل", "موسڵ"] and protected_found:
            continue
        if contains_term(txt, bad):
            rejected.append(bad)

    if rejected:
        return "rejected", rejected[0]

    preferred = find_terms(txt, CANDIDATE_PROFILE["preferred_locations"])
    if preferred:
        return "preferred", preferred[0]

    return "unknown", "نەنووسراو"


def detect_gender_requirement(job_text: str):
    txt = normalize_text(job_text)

    both = find_terms(txt, BOTH_GENDERS_TERMS)
    if both:
        return "any", "هەردوو ڕەگەز"

    female = find_terms(txt, FEMALE_ONLY_TERMS)
    male = find_terms(txt, MALE_ONLY_TERMS)

    if female and not male:
        return "female_only", "تەنها مێ"
    if male and not female:
        return "male_only", "تەنها نێر"
    if female and male:
        return "any", "هەردوو ڕەگەز"

    return "unknown", "نەنووسراو"


def detect_job_type(job_text: str):
    txt = normalize_text(job_text)

    if find_terms(txt, FULL_TIME_TERMS):
        return "full_time", "کاتی تەواو"
    if find_terms(txt, PART_TIME_TERMS):
        return "part_time", "نیمەکات"
    if find_terms(txt, SHIFT_TERMS):
        return "shift", "شەفت"
    if find_terms(txt, CONTRACT_TERMS):
        return "contract", "گرێبەست"
    if find_terms(txt, INTERNSHIP_TERMS):
        return "internship", "ڕاهێنان"

    return "unknown", "نەنووسراو"


def detect_role_matches(job_text: str):
    matches = []

    for profile in CANDIDATE_PROFILE["role_profiles"]:
        hits = find_terms(job_text, profile["keywords"])
        if hits:
            matches.append((profile["id"], profile["title"], hits))

    matches.sort(key=lambda x: len(x[2]), reverse=True)
    return matches


def evaluate_job(job_text: str, group_name: str):
    del group_name  # local filter does not depend on group name

    if len(job_text.strip()) < MIN_TEXT_LENGTH:
        return make_result(
            suitable=False,
            score=0,
            reason_ku="دەقی پۆستەکە زۆر کورتە",
            location_ok=None,
            reject_reason_code="too_short",
            job_title_ku="نەگونجاو"
        )

    for bad_role in CANDIDATE_PROFILE["rejected_roles"]:
        if contains_term(job_text, bad_role):
            return make_result(
                suitable=False,
                score=0,
                reason_ku=f"ڕۆڵەکە دەرەوەی چوارچێوەی سیڤییە: {bad_role}",
                location_ok=True,
                reject_reason_code="role_rejected",
                job_title_ku="نەگونجاو"
            )

    role_matches = detect_role_matches(job_text)
    if not role_matches:
        return make_result(
            suitable=False,
            score=0,
            reason_ku="جۆری کار لەگەڵ چوارچێوەی سیڤی ناگونجێت",
            location_ok=None,
            reject_reason_code="role_outside_cv",
            job_title_ku="نەگونجاو"
        )

    location_status, location_label = extract_location(job_text)
    if location_status == "rejected":
        return make_result(
            suitable=False,
            score=0,
            reason_ku=f"شوێنی کار لە دەرەوەی هەولێرە: {location_label}",
            location_ok=False,
            reject_reason_code="location_mismatch",
            location_ku=location_label,
            job_title_ku="نەگونجاو"
        )

    gender_status, gender_label = detect_gender_requirement(job_text)
    if CANDIDATE_PROFILE["gender"] == "male" and gender_status == "female_only":
        return make_result(
            suitable=False,
            score=0,
            reason_ku="داواکاری ڕەگەز تەنها بۆ مێیە",
            location_ok=(location_status != "rejected"),
            reject_reason_code="gender_mismatch",
            location_ku=location_label,
            gender_ku=gender_label,
            job_title_ku="نەگونجاو"
        )

    job_type_id, job_type_label = detect_job_type(job_text)

    primary_role_id, primary_role_title, primary_hits = role_matches[0]
    role_keyword_count = min(len(primary_hits), 4)
    extra_role_bonus = min(len(role_matches) - 1, 2) * 5
    role_score = 35 + (role_keyword_count * 7) + extra_role_bonus

    if location_status == "preferred":
        location_score = 25
    else:
        location_score = 10  # city missing is okay

    if gender_status in {"male_only", "any", "unknown"}:
        gender_score = 10
    else:
        gender_score = 0

    job_type_score_map = {
        "full_time": 10,
        "part_time": 8,
        "shift": 7,
        "contract": 7,
        "internship": 6,
        "unknown": 5,
    }
    job_type_score = job_type_score_map.get(job_type_id, 5)

    score = min(role_score + location_score + gender_score + job_type_score, 100)
    suitable = score >= MIN_SCORE

    job_title = extract_job_title(job_text)
    company = extract_company(job_text)
    salary = extract_salary(job_text)
    contact = extract_contact(job_text)
    requirements = extract_requirements(job_text)
    language = detect_language(job_text)

    if location_status == "preferred":
        city_text = location_label
        city_reason = "شار گونجاوە"
    else:
        city_text = "نەنووسراو"
        city_reason = "شار نەنووسراوە، بەڵام لە چوارچێوەی سیڤیدایە"

    if gender_status == "unknown":
        gender_reason = "ڕەگەز نەنووسراوە"
    else:
        gender_reason = f"ڕەگەز: {gender_label}"

    reason = f"{primary_role_title} + {city_reason} + {gender_reason} + جۆری کار: {job_type_label}"
    summary = (
        f"فلتەری local-only ئەم پۆستەی هەڵسەنگاند. "
        f"role={primary_role_title}، city={city_text}، gender={gender_label}، job_type={job_type_label}."
    )

    return make_result(
        suitable=suitable,
        score=score,
        reason_ku=reason,
        location_ok=(location_status != "rejected"),
        reject_reason_code="accepted" if suitable else "low_score",
        matched_profile_title=primary_role_title,
        matched_profile_id=primary_role_id,
        job_title_ku=job_title,
        company_ku=company,
        location_ku=city_text,
        gender_ku=gender_label,
        job_type_ku=job_type_label,
        summary_ku=summary,
        requirements_ku=requirements,
        salary_ku=salary,
        contact_ku=contact,
        language=language,
    )


# ===== TELEGRAM CLIENT =====
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
