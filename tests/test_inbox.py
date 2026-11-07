from datetime import date
from pathlib import Path

from jobbtracker.inbox import parse_linkedin, parse_relative_date

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 7)


def test_parse_linkedin_search_results():
    jobs = parse_linkedin((FIXTURES / "linkedin_search.html").read_text(), TODAY)
    assert [j["company"] for j in jobs] == ["Nordea", "BlackRock", "Volvo Group"]
    nordea, blackrock, volvo = jobs
    assert nordea["title"] == "Quantitative Risk Analyst, Credit Portfolio Oversight"
    assert nordea["location"] == "Stockholm (Hybrid)"
    assert nordea["url"] == "https://www.linkedin.com/jobs/view/4484927618/"
    assert nordea["source"] == "linkedin"
    assert nordea["posted"] == "2026-10-31"
    assert blackrock["title"] == "Graduate Analyst"
    assert blackrock["location"] == "Stockholms kommun (På plats)"
    assert blackrock["posted"] is None
    assert volvo["title"] == "Volvo Group Graduate Program 2027 - Technology Exploration Manager"
    assert volvo["posted"] == "2026-10-24"


def test_parse_relative_date():
    assert parse_relative_date("Lade upp för 3 dagar sedan", TODAY) == date(2026, 11, 4)
    assert parse_relative_date("för 2 månader sedan", TODAY) == date(2026, 9, 7)
    assert parse_relative_date("för 5 timmar sedan", TODAY) == TODAY
    assert parse_relative_date("Posted 1 week ago", TODAY) == date(2026, 10, 31)
    assert parse_relative_date("3 days ago", TODAY) == date(2026, 11, 4)
    assert parse_relative_date("Marknadsfört", TODAY) is None
