from __future__ import annotations

import xml.etree.ElementTree as ET

from ..models import Posting
from ..text import parse_date, strip_html

TT = "{https://teamtailor.com/locations}"


def parse(xml: str, company: str) -> list[Posting]:
    root = ET.fromstring(xml)
    posts = []
    for item in root.iter("item"):
        locations = []
        for loc in item.iter(f"{TT}location"):
            parts = [loc.findtext(f"{TT}{k}") for k in ("city", "name", "country")]
            locations.append(", ".join(p for p in parts if p))
        link = item.findtext("link", "")
        posts.append(Posting(
            source="teamtailor",
            company=company,
            title=item.findtext("title", ""),
            ad_url=link,
            apply_url=link,
            location="; ".join(locations),
            text=strip_html(item.findtext("description")),
            posted=parse_date(item.findtext("pubDate")),
        ))
    return posts


def fetch(company, http) -> list[Posting]:
    return parse(http.get_text(company.feed), company.name)
