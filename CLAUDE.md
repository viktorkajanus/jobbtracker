# Jobbtracker

Job tracker for industrial engineering (I-ek) students. Python 3.11+, stdlib only, pytest for tests.
Work test-first: add a failing test (often a regression from real data), then fix.

## "Process the inbox"

The user saves LinkedIn job-search pages from Safari (Cmd+S, Format "Webbarkiv") into `inbox/`.

1. `git pull --rebase` (the nightly bot commits `site/data/jobs.json`).
2. `python3 -m jobbtracker.inbox` parses every file, skips duplicates of jobs already in the
   table, appends new ones to `manual/jobs.json` and moves files to `inbox/processed/`.
3. Show the user what was added and skipped. If an ad that looks relevant was skipped as
   "not a student role", that is a classifier bug: add a regression test and fix `classify.py`.
4. `python3 -m jobbtracker.run --no-fetch`, run tests, commit `manual/jobs.json` (never
   `inbox/`, it contains the user's LinkedIn session page) and push. The page updates in ~1 min.

If a file has no job cards, it was probably saved as "Sidkälla"/HTML, which saves the feed instead.

## Layout

- `jobbtracker/classify.py` rules for type, area, city, period, deadline
- `jobbtracker/sources/` one adapter per job system; `companies/*.toml` which company uses which
- `jobbtracker/run.py` nightly fetch -> `site/data/jobs.json`; `site/` static page (GitHub Pages)
- `jobbtracker/manual.py`, `jobbtracker/inbox.py` LinkedIn/Indeed imports

No emojis anywhere (code, UI, commit messages).
