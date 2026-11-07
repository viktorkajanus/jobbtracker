from __future__ import annotations

from ..models import Posting
from ..text import parse_date


def parse(payload: list, company: str) -> list[Posting]:
    posts = []
    for job in payload:
        cats = job.get("categories") or {}
        locations = cats.get("allLocations") or [cats.get("location") or ""]
        text = "\n".join(x for x in (job.get("descriptionPlain"), job.get("additionalPlain")) if x)
        posts.append(Posting(
            source="lever",
            company=company,
            title=job.get("text", ""),
            ad_url=job["hostedUrl"],
            apply_url=job.get("applyUrl") or job["hostedUrl"],
            location="; ".join(locations),
            text=text,
            posted=parse_date(job.get("createdAt")),
        ))
    return posts


def fetch(company, http) -> list[Posting]:
    return parse(http.get_json(company.feed), company.name)
