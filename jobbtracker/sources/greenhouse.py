from __future__ import annotations

from ..models import Posting
from ..text import parse_date, strip_html


def parse(payload: dict, company: str) -> list[Posting]:
    posts = []
    for job in payload.get("jobs", []):
        offices = [o.get("location") or o.get("name") or "" for o in job.get("offices", [])]
        location = "; ".join(x for x in [(job.get("location") or {}).get("name", ""), *offices] if x)
        posts.append(Posting(
            source="greenhouse",
            company=company,
            title=job.get("title", ""),
            ad_url=job["absolute_url"],
            apply_url=job["absolute_url"],
            location=location,
            text=strip_html(job.get("content")),
            posted=parse_date(job.get("first_published") or job.get("updated_at")),
        ))
    return posts


def fetch(company, http) -> list[Posting]:
    return parse(http.get_json(company.feed), company.name)
