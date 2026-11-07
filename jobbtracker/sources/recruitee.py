from __future__ import annotations

from ..models import Posting
from ..text import parse_date, strip_html


def parse(payload: dict, company: str) -> list[Posting]:
    posts = []
    for job in payload.get("offers", []):
        locations = [job.get("location") or "", *(l.get("name", "") for l in job.get("locations") or [])]
        text = "\n".join(strip_html(job.get(k)) for k in ("description", "requirements") if job.get(k))
        posts.append(Posting(
            source="recruitee",
            company=company,
            title=job.get("title", ""),
            ad_url=job["careers_url"],
            apply_url=job.get("careers_apply_url") or job["careers_url"],
            location="; ".join(x for x in locations if x),
            text=text,
            posted=parse_date(job.get("published_at") or job.get("created_at")),
        ))
    return posts


def fetch(company, http) -> list[Posting]:
    return parse(http.get_json(company.feed), company.name)
