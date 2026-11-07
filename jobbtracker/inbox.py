"""Import jobs from LinkedIn/Indeed search pages saved into inbox/.

In Safari: Cmd+S, Format "Webbarkiv" (.webarchive). That saves the page as shown,
including every job card currently loaded in the list.

    python3 -m jobbtracker.inbox
"""

from __future__ import annotations

import html as htmllib
import plistlib
import re
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

from . import manual

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
TABLE = ROOT / "site" / "data" / "jobs.json"
MANUAL = ROOT / "manual" / "jobs.json"

LINKEDIN_CARD = re.compile(r'componentkey="job-card-component-ref-(\d+)"')
LINKEDIN_END = re.compile(r"Är dessa resultat användbara|Are these results helpful")
VERIFIED = re.compile(r"\((verifierat jobb|verified job)\)$")

UNITS = {
    "timme": "hours", "timmar": "hours", "hour": "hours", "hours": "hours", "minut": "hours", "minuter": "hours",
    "minute": "hours", "minutes": "hours",
    "dag": "days", "dagar": "days", "day": "days", "days": "days",
    "vecka": "weeks", "veckor": "weeks", "week": "weeks", "weeks": "weeks",
    "månad": "months", "månader": "months", "month": "months", "months": "months",
}
RELATIVE = re.compile(r"(\d+)\s+(" + "|".join(sorted(UNITS, key=len, reverse=True)) + r")\b\s*(sedan|ago)")


def parse_relative_date(text: str, today: date) -> date | None:
    m = RELATIVE.search(text.lower())
    if not m:
        return None
    n, unit = int(m.group(1)), UNITS[m.group(2)]
    if unit == "hours":
        return today
    if unit == "months":
        month = today.month - n
        year = today.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        return today.replace(year=year, month=month, day=min(today.day, 28))
    return today - timedelta(**{unit: n})


def _text_lines(fragment: str) -> list[str]:
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", fragment, flags=re.S)
    t = htmllib.unescape(re.sub(r"<[^>]+>", "\n", t))
    return [line.strip() for line in t.split("\n") if line.strip()]


def parse_linkedin(page: str, today: date) -> list[dict]:
    first: dict[str, int] = {}
    for m in LINKEDIN_CARD.finditer(page):
        first.setdefault(m.group(1), m.start())
    cards = sorted(first.items(), key=lambda kv: kv[1])
    end_match = LINKEDIN_END.search(page)
    page_end = end_match.start() if end_match else len(page)

    jobs = []
    for i, (job_id, pos) in enumerate(cards):
        start = page.rfind("<", 0, pos)
        end = page.rfind("<", 0, cards[i + 1][1]) if i + 1 < len(cards) else page_end
        lines = [l for l in _text_lines(page[start:end]) if not VERIFIED.search(l)]
        if len(lines) < 3:
            continue
        posted = next((d for l in lines[3:] if (d := parse_relative_date(l, today))), None)
        jobs.append({
            "source": "linkedin",
            "company": lines[1],
            "title": lines[0],
            "location": lines[2],
            "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
            "posted": posted.isoformat() if posted else None,
        })
    return jobs


def read_page(path: Path) -> str:
    if path.suffix == ".webarchive":
        archive = plistlib.loads(path.read_bytes())
        return archive["WebMainResource"]["WebResourceData"].decode("utf-8", errors="replace")
    return path.read_text(errors="replace")


def parse_file(path: Path, today: date) -> list[dict]:
    page = read_page(path)
    if LINKEDIN_CARD.search(page):
        return parse_linkedin(page, today)
    raise ValueError("no job list found (in Safari, save with Format: Webbarkiv)")


def main() -> None:
    import json

    today = date.today()
    files = sorted(p for p in INBOX.iterdir() if p.suffix in (".webarchive", ".html", ".mhtml")) if INBOX.exists() else []
    if not files:
        print("Inbox is empty.")
        return
    table = json.loads(TABLE.read_text()).get("jobs", []) if TABLE.exists() else []
    saved = manual.active_manual_jobs(manual.load(MANUAL), today)
    done = INBOX / "processed"
    done.mkdir(exist_ok=True)

    total_added = []
    for path in files:
        try:
            raws = parse_file(path, today)
        except ValueError as e:
            print(f"{path.name}: {e}", file=sys.stderr)
            continue
        added, skipped = manual.add_manual_jobs(raws, saved, table, today)
        saved += added
        total_added += added
        print(f"{path.name}: {len(raws)} ads, {len(added)} added")
        for j in added:
            print(f"  + {j['company']} | {j['title']} | {', '.join(j['cities'])}")
        for r, reason in skipped:
            print(f"  - {r['company']} | {r['title']} ({reason})")
        shutil.move(str(path), done / path.name)

    manual.save(MANUAL, saved)
    print(f"{len(total_added)} new jobs saved to {MANUAL.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
