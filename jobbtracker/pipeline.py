from __future__ import annotations

import hashlib
import re
from datetime import date

from .classify import (
    classify_areas,
    classify_type,
    extract_deadline,
    extract_period,
    is_off_target,
    normalize_cities,
)
from .models import Posting


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None


def build_job(p: Posting, today: date) -> dict | None:
    """Classify a raw posting into a table row, or None if it is not relevant."""
    if is_off_target(p.title):
        return None
    job_type = classify_type(p.title, p.text)
    if job_type is None:
        return None
    cities = normalize_cities(p.location)
    if not cities:
        return None
    # Programme titles rarely name the area, so let the ad text decide for those.
    use_text = p.source == "jobtech" and job_type == "Graduate"
    areas = classify_areas(p.title, p.text, p.segment, use_text=use_text)
    # JobTech covers every employer in Sweden, so without a matching area it is noise.
    if p.source == "jobtech" and not areas:
        return None
    deadline = p.deadline or extract_deadline(p.text, today)
    if deadline and deadline < today:
        return None
    return {
        "id": hashlib.sha1(p.ad_url.encode()).hexdigest()[:12],
        "company": p.company,
        "title": p.title.strip(),
        "type": job_type,
        "areas": areas,
        "cities": cities,
        "period": extract_period(p.title, p.text, today),
        "deadline": _iso(deadline),
        "posted": _iso(p.posted),
        "first_seen": today.isoformat(),
        "apply_url": p.apply_url,
        "ad_url": p.ad_url,
        "source": p.source,
    }


COMPANY_NOISE = re.compile(r"\b(ab|publ|sverige|sweden|group|asa|as|a/s|oyj|plc|ltd|inc|gmbh)\b")


def _norm_company(name: str) -> str:
    s = COMPANY_NOISE.sub(" ", re.sub(r"[^\w\s/]", " ", name.lower()))
    return " ".join(s.split())


def _norm_title(title: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", title.lower()).split())


def _same_company(a: str, b: str) -> bool:
    a, b = _norm_company(a), _norm_company(b)
    return bool(a and b) and (a == b or a.startswith(b + " ") or b.startswith(a + " "))


def _is_duplicate(a: dict, b: dict) -> bool:
    return (
        _norm_title(a["title"]) == _norm_title(b["title"])
        and bool(set(a["cities"]) & set(b["cities"]))
        and _same_company(a["company"], b["company"])
    )


def dedupe(jobs: list[dict]) -> list[dict]:
    """Collapse the same ad found via several sources, preferring the company's own site."""
    kept: list[dict] = []
    for j in sorted(jobs, key=lambda j: j["source"] == "jobtech"):
        dup = next((k for k in kept if _is_duplicate(k, j)), None)
        if dup is None:
            kept.append(dict(j))
            continue
        for field in ("deadline", "period", "posted"):
            dup[field] = dup[field] or j[field]
    return kept


def source_key(job: dict) -> str:
    return "JobTech" if job["source"] == "jobtech" else job["company"]


def merge_with_previous(jobs: list[dict], previous: list[dict], failed_sources: set[str], today: date) -> list[dict]:
    """Carry over first_seen dates, and keep last known jobs for sources that failed this run."""
    prev_by_id = {j["id"]: j for j in previous}
    merged = []
    for j in jobs:
        if old := prev_by_id.get(j["id"]):
            j = {**j, "first_seen": old["first_seen"]}
        merged.append(j)
    ids = {j["id"] for j in merged}
    for old in previous:
        if old["id"] not in ids and source_key(old) in failed_sources:
            merged.append(old)
    return [j for j in merged if not j["deadline"] or j["deadline"] >= today.isoformat()]
