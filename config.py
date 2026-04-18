import os
import sys
from pathlib import Path

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
TELEGRAM_SESSION = os.environ.get("TELEGRAM_SESSION", "").strip()

if not TELEGRAM_SESSION:
    print("❌ TELEGRAM_SESSION بەتاڵە")
    sys.exit(1)

SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
if not SMTP_PASSWORD:
    print("⚠️ SMTP_PASSWORD دانەنراوە — ناردنی ئیمێل ناکاریگەر دەبێت")

NOTIFY_CHAT = "me"
MIN_SCORE = 70
MIN_TEXT_LENGTH = 40

SEEN_JOBS_FILE = Path(os.environ.get("SEEN_JOBS_FILE", "/tmp/job_seen_jobs.json"))
SEEN_JOBS_TTL_HOURS = 72

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
WHATSAPP_ENABLED = True
