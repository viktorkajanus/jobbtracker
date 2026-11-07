"""Jobs added by hand from LinkedIn/Indeed pages saved into inbox/.

They live in manual/jobs.json, are merged into the table on every run, and expire
at their deadline or after MAX_AGE_DAYS when no deadline is known.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from .classify import (
    SENIOR,
    strip_senior_alternatives,
    classify_areas,
    classify_type,
    extract_deadline,
    extract_period,
    is_off_target,
    normalize_cities,
)
from .pipeline import _is_duplicate

MAX_AGE_DAYS = 45
SOURCES = ("linkedin", "indeed")


def search_url(source: str, title: str, company: str, city: str) -> str:
    if source == "indeed":
        return "https://se.indeed.com/jobs?" + urlencode({"q": f"{title} {company}", "l": city})
    return "https://www.linkedin.com/jobs/search/?" + urlencode({"keywords": f"{title} {company}", "location": city})


def _job_from_raw(r: dict, today: date) -> tuple[dict | None, str | None]:
    title, company, text = r["title"].strip(), r["company"].strip(), r.get("text", "")
    if is_off_target(title):
        return None, "not a student role"
    job_type = classify_type(title, text)
    if job_type is None:
        # Search results show no description, so trust that a plain title was picked on purpose,
        # unless it is senior or the text we do have rules it out.
        if SENIOR.search(strip_senior_alternatives(title.lower())) or classify_type(title, "") is not None:
            return None, "not a student role"
        job_type = "Junior"
    cities = normalize_cities(r.get("location", ""))
    if not cities:
        return None, "location not tracked"
    url = r.get("url") or search_url(r["source"], title, company, cities[0])
    deadline = r.get("deadline") or (d.isoformat() if (d := extract_deadline(text, today)) else None)
    return {
        "id": hashlib.sha1(f"{r['source']}|{company}|{title}|{cities[0]}".encode()).hexdigest()[:12],
        "company": company,
        "title": title,
        "type": job_type,
        "areas": classify_areas(title, text),
        "cities": cities,
        "period": r.get("period") or extract_period(title, text, today),
        "deadline": deadline,
        "posted": r.get("posted"),
        "first_seen": today.isoformat(),
        "apply_url": url,
        "ad_url": url,
        "source": r["source"],
    }, None


def add_manual_jobs(raws: list[dict], manual: list[dict], existing: list[dict], today: date):
    """Return (new jobs, [(raw, reason)] skipped)."""
    added, skipped = [], []
    for r in raws:
        job, reason = _job_from_raw(r, today)
        if job is None:
            skipped.append((r, reason))
        elif any(_is_duplicate(job, other) for other in [*existing, *manual, *added]):
            skipped.append((r, "already in table"))
        else:
            added.append(job)
    return added, skipped


def still_relevant(jobs: list[dict]) -> list[dict]:
    """Drop stored jobs that the current classification rules would reject."""
    def ok(j):
        raw = {"source": j["source"], "company": j["company"], "title": j["title"], "location": ", ".join(j["cities"])}
        return _job_from_raw(raw, date.today())[0] is not None
    return [j for j in jobs if ok(j)]


def active_manual_jobs(jobs: list[dict], today: date) -> list[dict]:
    cutoff = (today - timedelta(days=MAX_AGE_DAYS)).isoformat()
    return [
        j for j in jobs
        if (j["deadline"] >= today.isoformat() if j["deadline"] else j["first_seen"] >= cutoff)
    ]


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text()) if path.exists() else []


def save(path: Path, jobs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jobs, ensure_ascii=False, indent=1))
