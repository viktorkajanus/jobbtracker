"""Fetch every source, classify, and write data/jobs.json for the website."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from .http import Http
from .models import Company
from .pipeline import build_job, dedupe, merge_with_previous
from .sources import ADAPTERS, jobtech

ROOT = Path(__file__).resolve().parent.parent
WORKERS = 8


def load_companies(paths: list[Path]) -> list[Company]:
    companies = []
    for path in paths:
        for entry in tomllib.loads(Path(path).read_text())["company"]:
            companies.append(Company(**entry))
    return companies


def fetch_company(company: Company, http):
    return ADAPTERS[company.ats](company, http)


def run(companies_paths, out_path: Path, today: date, fetch_company=fetch_company,
        fetch_jobtech=jobtech.fetch, http=None) -> dict:
    companies = load_companies(companies_paths)
    postings, status, failed = [], [], set()

    def fetch_one(company):
        try:
            return company, fetch_company(company, http), None
        except Exception as e:  # one broken feed must not stop the run
            return company, [], f"{type(e).__name__}: {e}"

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(fetch_one, [c for c in companies if c.ats in ADAPTERS]))

    for company, found, error in results:
        if error:
            failed.add(company.name)
            status.append({"name": company.name, "ok": False, "count": 0, "error": error})
            continue
        for p in found:
            p.segment = company.segment
        postings += found
        status.append({"name": company.name, "ok": True, "count": len(found), "error": None})

    try:
        found = fetch_jobtech(http)
        postings += found
        status.append({"name": "JobTech", "ok": True, "count": len(found), "error": None})
    except Exception as e:
        failed.add("JobTech")
        status.append({"name": "JobTech", "ok": False, "count": 0, "error": f"{type(e).__name__}: {e}"})

    jobs = dedupe([j for p in postings if (j := build_job(p, today))])
    previous = json.loads(out_path.read_text()).get("jobs", []) if out_path.exists() else []
    jobs = merge_with_previous(jobs, previous, failed, today)
    jobs.sort(key=lambda j: (j["deadline"] or "9999", j["company"]))

    data = {
        "generated": today.isoformat(),
        "jobs": jobs,
        "sources": status,
        "manual": [{"name": c.name, "segment": c.segment, "careers_url": c.careers_url}
                   for c in companies if c.ats not in ADAPTERS],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companies", nargs="*", type=Path, default=sorted((ROOT / "companies").glob("*.toml")))
    parser.add_argument("--out", type=Path, default=ROOT / "site" / "data" / "jobs.json")
    args = parser.parse_args(argv)

    data = run(args.companies, args.out, date.today(), http=Http())
    types = Counter(j["type"] for j in data["jobs"])
    broken = [s for s in data["sources"] if not s["ok"]]
    print(f"{len(data['jobs'])} jobs: " + ", ".join(f"{k} {v}" for k, v in types.most_common()))
    for s in broken:
        print(f"  FAILED {s['name']}: {s['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
