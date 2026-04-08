import re
import hashlib
from config import JOB_KEYWORDS, SUPPORT_SIGNAL_TERMS


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


def detect_language(text: str) -> str:
    if re.search(r"[\u0600-\u06FF]", text):
        if any(ch in text for ch in ["ە", "ێ", "ۆ", "ڵ", "ڕ"]):
            return "ku"
        return "ar"
    if re.search(r"[A-Za-z]", text):
        return "en"
    return "unknown"


def extract_lines(text: str):
    raw_lines = text.splitlines()
    lines = []
    for line in raw_lines:
        s = line.strip()
        if s:
            lines.append(s)
    return lines
