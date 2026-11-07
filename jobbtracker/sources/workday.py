"""Workday career sites (used by many large banks and industrials).

Boards can hold thousands of jobs, so we search for student-relevant terms and only
load the full description for postings whose title passes the cheap prefilter.
"""

from __future__ import annotations

import re

from ..classify import normalize_cities
from ..models import Posting
from ..prefilter import title_is_candidate
from ..text import parse_date, strip_html

SEARCH_TERMS = [
    "intern", "internship", "summer", "graduate", "trainee", "thesis", "junior",
    "analyst", "associate", "entry level", "praktik", "examensarbete", "logistics",
]
PAGE = 20
MAX_PAGES = 5


def public_base(feed: str) -> str:
    m = re.match(r"(https://[^/]+)/wday/cxs/[^/]+/([^/]+)/jobs", feed)
    if not m:
        raise ValueError(f"Unexpected Workday feed URL: {feed}")
    return f"{m.group(1)}/{m.group(2)}"


def location_may_match(locations_text: str) -> bool:
    """Workday lists one city, or "N Locations" when there are several."""
    if not locations_text or re.search(r"\d+\s+locations", locations_text, re.I):
        return True
    return bool(normalize_cities(locations_text))


def fetch(company, http) -> list[Posting]:
    api_base = company.feed.rsplit("/jobs", 1)[0]
    base = public_base(company.feed)
    listings: dict[str, dict] = {}
    for term in SEARCH_TERMS:
        for page in range(MAX_PAGES):
            body = {"limit": PAGE, "offset": page * PAGE, "searchText": term, "appliedFacets": {}}
            payload = http.post_json(company.feed, body)
            jobs = payload.get("jobPostings") or []
            for job in jobs:
                if job.get("externalPath"):
                    listings.setdefault(job["externalPath"], job)
            if len(jobs) < PAGE:
                break

    posts = []
    for path, job in listings.items():
        if not title_is_candidate(job.get("title", "")) or not location_may_match(job.get("locationsText", "")):
            continue
        info = (http.get_json(api_base + path) or {}).get("jobPostingInfo") or {}
        locations = [info.get("location") or job.get("locationsText") or "", *info.get("additionalLocations", [])]
        ad_url = base + path
        posts.append(Posting(
            source="workday",
            company=company.name,
            title=info.get("title") or job.get("title", ""),
            ad_url=ad_url,
            apply_url=ad_url + "/apply",
            location="; ".join(x for x in locations if x),
            text=strip_html(info.get("jobDescription")),
            posted=parse_date(info.get("startDate")),
        ))
    return posts
