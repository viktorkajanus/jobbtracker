from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Company:
    name: str
    segment: str
    cities: list[str]
    careers_url: str
    ats: str
    feed: str = ""
    notes: str = ""


@dataclass
class Posting:
    """A raw job ad as delivered by a source, before classification."""

    source: str
    company: str
    title: str
    ad_url: str
    apply_url: str
    location: str
    text: str = ""
    posted: date | None = None
    deadline: date | None = None
    segment: str | None = None
    tags: list[str] = field(default_factory=list)
