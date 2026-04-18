import re
from text_utils import normalize_text, contains_term, find_terms, extract_lines
from profile_data import CANDIDATE_PROFILE
from config import (
    REJECT_LOCATION_TERMS,
    FEMALE_ONLY_TERMS,
    MALE_ONLY_TERMS,
    BOTH_GENDERS_TERMS,
    FULL_TIME_TERMS,
    PART_TIME_TERMS,
    SHIFT_TERMS,
    CONTRACT_TERMS,
    INTERNSHIP_TERMS,
)


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
                if len(m.group(1).strip(" -:|")) >= 2:
                    return line.split(":")[-1].strip()

    for line in lines[:10]:
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

    phones = list(dict.fromkeys(phones))[:2]
    emails = list(dict.fromkeys(emails))[:2]

    if phones:
        return " | ".join(phones)

    if emails:
        return " | ".join(emails)

    return "نەزانراو"


def extract_contact_type(text: str) -> str:
    """
    Returns:
      'phone'      - only phone found
      'email'      - only email found
      'both'       - phone + email found
      'none'       - nothing found
    """
    phones = re.findall(r"(?:\+?964|0)7\d{9}", text)
    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)

    has_phone = bool(phones)
    has_email = bool(emails)

    if has_phone and has_email:
        return "both"
    if has_phone:
        return "phone"
    if has_email:
        return "email"
    return "none"


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

def extract_jobs_from_sources(sources):
    all_jobs = []
    for source in sources:
        if source.get("type") == "telegram":
            # ئەمە placeholder ە، کۆدی ڕاستەقینەی تێلیگرامت لێرە دەنووسیت
            pass
    return all_jobs
