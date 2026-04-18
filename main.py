# main.py
import time
import logging
from datetime import datetime

# هاوردەکردنی مۆدیولەکانی پڕۆژەکەت
from config import (
    CHECK_INTERVAL_MINUTES, 
    SEARCH_SOURCES, 
    EMAIL_ENABLED, 
    WHATSAPP_ENABLED
)
from extractors import extract_jobs_from_sources
from evaluator import evaluate_job_match
from storage import load_seen_jobs, save_seen_job
from email_sender import send_email_notification
from profile_data import USER_NAME, USER_CV_PATH, USER_PHONE  # دڵنیابە کە ئەمە لە profile_data.py زیاد دەکەیت

# ⭐ هاوردەکردنی مۆدیولی وەتسئاپ
from whatsapp_queue import add_to_whatsapp_queue

# ڕێکخستنی لۆگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_whatsapp_message(job):
    """
    دروستکردنی نامەی تایبەتمەندی وەتسئاپ بۆ هەر کارێک.
    """
    message = f"""بەڕێز خاوەن کار،

سڵاو. من {USER_NAME}ـم.
ئەم هەلی کارەم لە ڕێگەی بۆتێکی چاودێری هەلی کارەوە بینی و زۆر بەدڵم بوو.

📌 **ناونیشانی کار:** {job.get('title', 'نادیار')}
📍 **شوێن:** {job.get('location', 'نادیار')}
🏢 **کۆمپانیا:** {job.get('company', 'نادیار')}

تکایە فایلی CVـی من لە پەیوەستکراو بخوێنەرەوە.
بە هیوای سەرکەوتنی هەردوولامان.

سوپاس،
{USER_NAME}
📞 {USER_PHONE}"""
    return message

def generate_email_body(job):
    """
    دروستکردنی نامەی تایبەتمەندی ئیمەیڵ.
    """
    # هەمان شێوازی پێشوو، بەڵام دەتوانیت لێرە بیگۆڕیت
    return f"""Subject: Application for {job.get('title', 'Position')}

Dear Hiring Manager,

I am writing to express my interest in the {job.get('title')} position at {job.get('company')}.

Best regards,
{USER_NAME}"""

def process_job(job, source_name):
    """
    پرۆسێسکردنی هەر هەلی کارێک.
    """
    job_id = job.get('link') or job.get('title') + job.get('company', '')
    
    # 1. هەڵسەنگاندنی گونجانی کارەکە
    score, is_match = evaluate_job_match(job)
    
    if not is_match:
        logger.debug(f"❌ کارەکە گونجاو نییە (Score: {score}): {job.get('title')}")
        return
    
    # 2. پشکنینی ئەوەی کە پێشتر نەنێردراوە
    if job_id in load_seen_jobs():
        logger.debug(f"⏩ کارەکە پێشتر پرۆسێس کراوە: {job.get('title')}")
        return
    
    logger.info(f"🎯 هەلی کاری گونجاو دۆزرایەوە (Score: {score}): {job.get('title')} لە {source_name}")
    
    # 3. دەرهێنانی ژمارەی وەتسئاپ (ئەگەر هەبێت)
    phone_number = extract_phone_from_job(job)
    
    # 4. ناردنی ئیمەیڵ (ئەگەر چالاک بێت)
    if EMAIL_ENABLED and job.get('contact_email'):
        try:
            email_body = generate_email_body(job)
            send_email_notification(
                to_email=job['contact_email'],
                subject=f"Application for {job.get('title')}",
                body=email_body,
                attachment_path=USER_CV_PATH
            )
            logger.info(f"📧 ئیمەیڵ نێردرا بۆ {job.get('contact_email')}")
        except Exception as e:
            logger.error(f"❌ هەڵە لە ناردنی ئیمەیڵ: {e}")
    
    # 5. ناردنی وەتسئاپ (ئەگەر ژمارە هەبێت و چالاک بێت) ⭐
    if WHATSAPP_ENABLED and phone_number:
        try:
            message = generate_whatsapp_message(job)
            add_to_whatsapp_queue(
                phone_number=phone_number,
                message=message,
                cv_path=USER_CV_PATH,
                job_title=job.get('title', 'نادیار')
            )
            logger.info(f"📱 داواکاری وەتسئاپ زیاد کرا بۆ {phone_number}")
        except Exception as e:
            logger.error(f"❌ هەڵە لە زیادکردنی داواکاری وەتسئاپ: {e}")
    
    # 6. پاشەکەوتکردنی کارەکە وەک نێردراو
    save_seen_job(job_id)
    logger.info(f"💾 کارەکە پاشەکەوت کرا: {job_id}")

def extract_phone_from_job(job):
    """
    هەوڵدەدات ژمارەی مۆبایل لە ناوەڕۆکی کارەکە بدۆزێتەوە.
    """
    import re
    # گەڕان بەدوای ژمارە عێراقییەکان (٠٧xx xxx xxxx)
    text = job.get('description', '') + ' ' + job.get('content', '')
    
    # چەندین شێوازی ژمارەی مۆبایل
    patterns = [
        r'07[0-9]{9}',           # 07701234567
        r'\+9647[0-9]{9}',       # +9647701234567
        r'009647[0-9]{9}',       # 009647701234567
        r'07\d{2}\s?\d{3}\s?\d{4}' # 0770 123 4567
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # پاککردنەوە و گەڕاندنەوەی تەنها ژمارە
            phone = re.sub(r'[\s\+]', '', match.group())
            if phone.startswith('00964'):
                phone = '0' + phone[5:]
            elif phone.startswith('+964'):
                phone = '0' + phone[4:]
            return phone
    return None

def main_loop():
    """
    لوپی سەرەکی بۆ چاودێری بەردەوام.
    """
    logger.info("🚀 Job Monitor Bot دەستی پێکرد...")
    logger.info(f"📧 ئیمەیڵ: {'چالاک' if EMAIL_ENABLED else 'ناچالاک'}")
    logger.info(f"📱 وەتسئاپ: {'چالاک' if WHATSAPP_ENABLED else 'ناچالاک'}")
    
    while True:
        try:
            logger.info(f"🔍 پشکنین بۆ هەلی کاری نوێ لە {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            # دەرهێنانی کارەکان لە هەموو سەرچاوەکان
            all_jobs = extract_jobs_from_sources(SEARCH_SOURCES)
            logger.info(f"📊 {len(all_jobs)} کار دۆزرانەوە.")
            
            # پرۆسێسکردنی هەر کارێک
            for job in all_jobs:
                process_job(job, source_name="Web")
            
            # چاوەڕوانی بۆ خولی داهاتوو
            wait_minutes = CHECK_INTERVAL_MINUTES
            logger.info(f"⏳ چاوەڕوانی {wait_minutes} خولەک بۆ پشکنینی داهاتوو...")
            time.sleep(wait_minutes * 60)
            
        except KeyboardInterrupt:
            logger.info("🛑 بەرنامەکە وەستێندرا.")
            break
        except Exception as e:
            logger.error(f"❌ هەڵەیەکی چاوەڕواننەکراو ڕوویدا: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
