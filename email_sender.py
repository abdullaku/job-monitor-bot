import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

# ئیمێل و پاسوۆردی bk.ru
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "abdulla_ali_abdulla@bk.ru")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")  # پاسوۆردی تایبەت
SMTP_HOST = "smtp.mail.ru"
SMTP_PORT = 465

# نەخشەی CV بەپێی جۆری کار
CV_MAP = {
    "real_estate_property": {
        "file": Path(__file__).parent / "cv_real_estate.pdf",
        "name": "Abdulla_Ali_CV_RealEstate.pdf",
    },
    "sales_crm_customer_service": {
        "file": Path(__file__).parent / "cv_sales.pdf",
        "name": "Abdulla_Ali_CV_Sales.pdf",
    },
    "cashier_pos": {
        "file": Path(__file__).parent / "cv_system.pdf",
        "name": "Abdulla_Ali_CV_System.pdf",
    },
    "office_admin_data_entry": {
        "file": Path(__file__).parent / "cv_system.pdf",
        "name": "Abdulla_Ali_CV_System.pdf",
    },
    "marketing_branding_social_media": {
        "file": Path(__file__).parent / "cv_sales.pdf",
        "name": "Abdulla_Ali_CV_Sales.pdf",
    },
}

DEFAULT_CV = {
    "file": Path(__file__).parent / "cv_real_estate.pdf",
    "name": "Abdulla_Ali_CV.pdf",
}


def get_cv_for_role(role_id: str) -> dict:
    return CV_MAP.get(role_id, DEFAULT_CV)


def build_email_body(job_title: str) -> str:
    return f"""جنابَ المسؤول المحترم،

أتقدم بطلبي للانضمام إلى فريق عملكم في وظيفة {job_title}، إذ أرى أن خبرتي ومهاراتي تتوافق مع متطلبات هذه الوظيفة.

أرفق لكم سيرتي الذاتية للاطلاع عليها، وأنا على أتم الاستعداد لإجراء المقابلة في أي وقت يناسبكم.

مع فائق الاحترام،
عبدالله علي
📞 0780 466 6191"""


def send_cv_email(to_email: str, job_title: str, role_id: str) -> bool:
    """
    CV بنێرە بۆ خاوەنکار
    Returns True ئەگەر سەرکەوتوو بوو
    """
    try:
        cv_info = get_cv_for_role(role_id)
        cv_path = cv_info["file"]
        cv_filename = cv_info["name"]

        if not cv_path.exists():
            print(f"❌ فایلی CV نەدۆزراوەتەوە: {cv_path}")
            return False

        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email
        msg["Subject"] = f"طلب توظيف - {job_title}"

        msg.attach(MIMEText(build_email_body(job_title), "plain", "utf-8"))

        with open(cv_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{cv_filename}"',
            )
            msg.attach(part)

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_bytes())

        print(f"📧 CV نێردرا بۆ: {to_email} ({cv_filename})")
        return True

    except Exception as e:
        print(f"❌ هەڵە لە ناردنی ئیمێل: {e}")
        return False
