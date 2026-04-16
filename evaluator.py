from config import MIN_TEXT_LENGTH
from profile_data import CANDIDATE_PROFILE
from text_utils import contains_term, detect_language
from extractors import (
    extract_job_title,
    extract_company,
    extract_salary,
    extract_contact,
    extract_contact_type,
    extract_requirements,
    extract_location,
    detect_gender_requirement,
    detect_job_type,
    detect_role_matches,
)


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
    contact_type: str = "none",
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
        "contact_type": contact_type,
        "language": language,
        "location_ok": location_ok,
        "reject_reason_code": reject_reason_code,
    }


def evaluate_job(job_text: str, group_name: str):
    del group_name

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
        location_score = 10

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
    suitable = score >= 70

    job_title = extract_job_title(job_text)
    company = extract_company(job_text)
    salary = extract_salary(job_text)
    contact = extract_contact(job_text)
    contact_type = extract_contact_type(job_text)
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
        contact_type=contact_type,
        language=language,
    )
