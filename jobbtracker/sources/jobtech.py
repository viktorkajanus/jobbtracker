"""Arbetsförmedlingen JobSearch API (covers virtually all Swedish job ads)."""

from __future__ import annotations

from urllib.parse import urlencode

from ..models import Posting
from ..text import parse_date

API = "https://jobsearch.api.jobtechdev.se/search"
REGIONS = {"01": "Stockholm", "14": "Gothenburg"}
QUERIES = [
    "praktik", "praktikant", "internship", "intern", "sommarjobb", "summer", "trainee",
    "traineeprogram", "graduate", "examensarbete", "exjobb", "thesis", "nyexaminerad",
    "junior", "entry level",
]
PAGE = 100
MAX_OFFSET = 500


def parse(payload: dict) -> list[Posting]:
    posts = []
    for hit in payload.get("hits", []):
        addr = hit.get("workplace_address") or {}
        place = addr.get("municipality") or addr.get("city") or ""
        location = ", ".join(x for x in (place, addr.get("region")) if x)
        apply = (hit.get("application_details") or {}).get("url") or hit["webpage_url"]
        posts.append(Posting(
            source="jobtech",
            company=(hit.get("employer") or {}).get("name") or "",
            title=hit.get("headline") or "",
            ad_url=hit["webpage_url"],
            apply_url=apply,
            location=location,
            text=(hit.get("description") or {}).get("text") or "",
            posted=parse_date(hit.get("publication_date")),
            deadline=parse_date(hit.get("application_deadline")),
        ))
    return posts


def fetch(http) -> list[Posting]:
    seen: dict[str, Posting] = {}
    for region in REGIONS:
        for q in QUERIES:
            offset = 0
            while offset <= MAX_OFFSET:
                url = f"{API}?{urlencode({'q': q, 'region': region, 'limit': PAGE, 'offset': offset})}"
                payload = http.get_json(url)
                for p in parse(payload):
                    seen.setdefault(p.ad_url, p)
                offset += PAGE
                if offset >= payload.get("total", {}).get("value", 0):
                    break
    return list(seen.values())
