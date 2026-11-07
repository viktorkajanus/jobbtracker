from __future__ import annotations

from .classify import (
    GRADUATE,
    INTERNSHIP,
    JUNIOR_AMBIGUOUS,
    JUNIOR_EXPLICIT,
    SENIOR,
    THESIS,
    is_off_target,
)


def title_is_candidate(title: str) -> bool:
    """Cheap check on the title alone, used before fetching full descriptions."""
    t = title.lower()
    if SENIOR.search(t) or is_off_target(t):
        return False
    return any(p.search(t) for p in (THESIS, INTERNSHIP, GRADUATE, JUNIOR_EXPLICIT, JUNIOR_AMBIGUOUS))
