from datetime import date

from jobbtracker.manual import add_manual_jobs, active_manual_jobs, search_url

TODAY = date(2026, 11, 7)


def raw(**kw):
    defaults = dict(source="linkedin", company="Lazard", title="Summer Analyst 2027 - M&A", location="Stockholm, Sweden")
    return {**defaults, **kw}


def test_search_url_linkedin():
    url = search_url("linkedin", "Summer Analyst", "Lazard", "Stockholm")
    assert url == "https://www.linkedin.com/jobs/search/?keywords=Summer+Analyst+Lazard&location=Stockholm"


def test_search_url_indeed():
    url = search_url("indeed", "Trainee", "Volvo", "Gothenburg")
    assert url == "https://se.indeed.com/jobs?q=Trainee+Volvo&l=Gothenburg"


def test_add_classifies_and_builds_links():
    added, skipped = add_manual_jobs([raw()], manual=[], existing=[], today=TODAY)
    [job] = added
    assert skipped == []
    assert job["type"] == "Internship"
    assert job["areas"] == ["M&A"]
    assert job["cities"] == ["Stockholm"]
    assert job["period"] == "Summer 2027"
    assert job["source"] == "linkedin"
    assert job["first_seen"] == "2026-11-07"
    assert job["ad_url"] == job["apply_url"]
    assert job["ad_url"].startswith("https://www.linkedin.com/jobs/search/")


def test_explicit_url_and_deadline_are_kept():
    [job], _ = add_manual_jobs([raw(url="https://www.linkedin.com/jobs/view/123", deadline="2026-12-01")],
                               manual=[], existing=[], today=TODAY)
    assert job["ad_url"] == "https://www.linkedin.com/jobs/view/123"
    assert job["deadline"] == "2026-12-01"


def test_skips_duplicates_of_existing_jobs():
    existing = [{"company": "Lazard Frères", "title": "Summer Analyst 2027 – M&A", "cities": ["Stockholm"]}]
    added, skipped = add_manual_jobs([raw(company="Lazard Freres")], manual=[], existing=existing, today=TODAY)
    # Company spelling differs too much here, so this is NOT treated as a duplicate.
    assert len(added) == 1
    added, skipped = add_manual_jobs([raw(company="Lazard Frères")], manual=[], existing=existing, today=TODAY)
    assert added == [] and skipped[0][1] == "already in table"


def test_skips_duplicates_within_manual_list():
    first, _ = add_manual_jobs([raw()], manual=[], existing=[], today=TODAY)
    added, skipped = add_manual_jobs([raw()], manual=first, existing=[], today=TODAY)
    assert added == [] and skipped[0][1] == "already in table"


def test_skips_untracked_city():
    added, skipped = add_manual_jobs([raw(location="New York")], manual=[], existing=[], today=TODAY)
    assert added == [] and skipped[0][1] == "location not tracked"


def test_skips_senior():
    added, skipped = add_manual_jobs([raw(title="Vice President, M&A")], manual=[], existing=[], today=TODAY)
    assert added == [] and skipped[0][1] == "not a student role"


def test_plain_title_without_signal_counts_as_junior():
    # Search results show no description, so trust that the user picked a relevant ad.
    [job], _ = add_manual_jobs([raw(title="Analyst, Corporate Finance")], manual=[], existing=[], today=TODAY)
    assert job["type"] == "Junior"


def test_active_manual_jobs_expire():
    jobs = [
        {"id": "a", "deadline": "2026-11-01", "first_seen": "2026-11-01"},
        {"id": "b", "deadline": None, "first_seen": "2026-09-01"},
        {"id": "c", "deadline": None, "first_seen": "2026-10-15"},
        {"id": "d", "deadline": "2026-12-01", "first_seen": "2026-08-01"},
    ]
    assert [j["id"] for j in active_manual_jobs(jobs, TODAY)] == ["c", "d"]


def test_graduate_programme_with_manager_in_title():
    title = "Volvo Group Graduate Program 2027 - Technology Exploration Manager"
    [job], _ = add_manual_jobs([raw(company="Volvo Group", title=title, location="Göteborg")],
                               manual=[], existing=[], today=TODAY)
    assert job["type"] == "Graduate"
