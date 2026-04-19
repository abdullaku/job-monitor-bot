import json
from datetime import datetime, timedelta
from config import SEEN_JOBS_FILE, SEEN_JOBS_TTL_HOURS

seen_jobs = {}


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
        return seen_jobs  # ✅ FIX 1: return instead of bare return

    try:
        seen_jobs = json.loads(SEEN_JOBS_FILE.read_text(encoding="utf-8"))
        if not isinstance(seen_jobs, dict):
            seen_jobs = {}
    except Exception:
        seen_jobs = {}

    cleanup_seen_jobs(save=False)
    return seen_jobs  # ✅ FIX 1: always return seen_jobs


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

def save_seen_job(job_id: str):
    load_seen_jobs()  # ✅ FIX 2: load into global, don't assign return value
    seen_jobs[job_id] = datetime.now().isoformat()  # ✅ use global directly
    save_seen_jobs()  # ✅ no argument needed
