from __future__ import annotations

from ..models import Posting
from ..text import parse_date


def parse(payload: dict, company: str) -> list[Posting]:
    posts = []
    for job in payload.get("jobs", []):
        locations = [job.get("location") or "", *(l.get("location", "") for l in job.get("secondaryLocations", []))]
        posts.append(Posting(
            source="ashby",
            company=company,
            title=job.get("title", ""),
            ad_url=job["jobUrl"],
            apply_url=job.get("applyUrl") or job["jobUrl"],
            location="; ".join(x for x in locations if x),
            text=job.get("descriptionPlain") or "",
            posted=parse_date(job.get("publishedAt")),
        ))
    return posts


def fetch(company, http) -> list[Posting]:
    return parse(http.get_json(company.feed), company.name)
