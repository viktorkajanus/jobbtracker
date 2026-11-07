from __future__ import annotations

from ..models import Posting
from ..text import parse_date, strip_html


def parse(payload: dict, company: str) -> list[Posting]:
    posts = []
    for job in payload.get("jobs", []):
        posts.append(Posting(
            source="workable",
            company=company,
            title=job.get("title", ""),
            ad_url=job["url"],
            apply_url=job.get("application_url") or job["url"],
            location=", ".join(x for x in (job.get("city"), job.get("country")) if x),
            text=strip_html(job.get("description")),
            posted=parse_date(job.get("published_on")),
        ))
    return posts


def fetch(company, http) -> list[Posting]:
    feed = company.feed if "details=" in company.feed else company.feed + "?details=true"
    return parse(http.get_json(feed), company.name)
