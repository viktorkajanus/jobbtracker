# Jobbtracker

Internships, graduate programmes, theses and junior roles for industrial engineering and
management students, in Stockholm, Gothenburg and selected cities abroad (London, Frankfurt,
Amsterdam, Zurich, Oslo, Copenhagen, Helsinki).

Every night a GitHub Action fetches ads from:

- **Arbetsförmedlingen JobTech API**, which covers almost all Swedish job ads
- **Company career sites** listed in `companies/*.toml` (Greenhouse, Lever, Workday,
  Teamtailor, SmartRecruiters, Workable, Ashby)

Each ad is classified with keyword rules (`jobbtracker/classify.py`) into type, area, period
and deadline. The results are written to `site/data/jobs.json`, and the static page in `site/`
is published with GitHub Pages.

LinkedIn and Indeed are deliberately not scraped: they have no public API and forbid scraping.

## Run locally

```sh
python3 -m pytest -q            # tests
python3 -m jobbtracker.run      # fetch everything into site/data/jobs.json
python3 -m http.server -d site  # open http://localhost:8000
```

## Adding a company

Add an entry to a file in `companies/`:

```toml
[[company]]
name = "Example Partners"
segment = "M&A"              # IB, PE, M&A, Consulting, Audit, Bank, Industry, Tech
cities = ["Stockholm"]
careers_url = "https://example.com/careers"
ats = "teamtailor"           # or greenhouse, lever, workday, smartrecruiters, workable, ashby, unsupported
feed = "https://example.teamtailor.com/jobs.rss"
notes = ""
```

Companies with `ats = "unsupported"` are listed on the page under "Companies not tracked
automatically".

## Status marks

Interested / Applied / Hidden marks are stored in your browser (localStorage) only. Each mark
keeps a snapshot of the job and a status history, ready for a future application-pipeline view.

## Adding jobs from LinkedIn

LinkedIn and Indeed are never scraped. Instead:

1. Search on LinkedIn Jobs in Safari and scroll so the ads you want are loaded.
2. Cmd+S, Format **Webbarkiv**, save into `inbox/` (not committed).
3. Run `python3 -m jobbtracker.inbox`, or ask Claude Code to "process the inbox".

New ads are added to `manual/jobs.json` with direct links, duplicates of jobs already in the
table are skipped, and imported jobs expire at their deadline or after 45 days.
