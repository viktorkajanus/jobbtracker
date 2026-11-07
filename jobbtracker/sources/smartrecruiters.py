from __future__ import annotations

from ..models import Posting
from ..text import parse_date

PAGE = 100


def parse(payload: dict, company: str, identifier: str) -> list[Posting]:
    posts = []
    for job in payload.get("content", []):
        loc = job.get("location") or {}
        url = f"https://jobs.smartrecruiters.com/{identifier}/{job['id']}"
        posts.append(Posting(
            source="smartrecruiters",
            company=company,
            title=job.get("name", ""),
            ad_url=url,
            apply_url=url,
            location=loc.get("fullLocation") or ", ".join(x for x in (loc.get("city"), loc.get("country")) if x),
            posted=parse_date(job.get("releasedDate")),
        ))
    return posts


def fetch(company, http) -> list[Posting]:
    identifier = company.feed.rstrip("/").split("/companies/")[1].split("/")[0]
    posts, offset = [], 0
    while True:
        sep = "&" if "?" in company.feed else "?"
        payload = http.get_json(f"{company.feed}{sep}limit={PAGE}&offset={offset}")
        posts += parse(payload, company.name, identifier)
        offset += PAGE
        if offset >= payload.get("totalFound", 0):
            return posts
