from datetime import date
from pathlib import Path

from jobbtracker.inbox import parse_indeed, parse_linkedin, parse_relative_date

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


def test_card_with_repeated_title():
    page = ('<div componentkey="job-card-component-ref-4477291471"><p>Graduate &amp; Junior Consulting Professionals</p>'
            '<p>Graduate &amp; Junior Consulting Professionals</p><p>Accenture Nordics</p><p>Stockholm</p>'
            '<p>Lade upp för 3 veckor sedan</p></div>')
    [job] = parse_linkedin(page, TODAY)
    assert (job["title"], job["company"], job["location"]) == (
        "Graduate & Junior Consulting Professionals", "Accenture Nordics", "Stockholm")


def test_parse_indeed_search_results():
    from jobbtracker.inbox import parse_indeed
    jobs = parse_indeed((FIXTURES / "indeed_search.html").read_text())
    assert [j["company"] for j in jobs] == ["Knowit Sweden", "CAG Clara Financial Consulting", "Ericsson"]
    knowit = jobs[0]
    assert knowit["title"] == "Mentorship Program – Knowit Management Consulting 2027"
    assert knowit["location"] == "111 57 Stockholm"
    assert knowit["url"] == "https://se.indeed.com/viewjob?jk=715d72b3d605d359"
    assert knowit["source"] == "indeed"
    assert jobs[2]["title"] == "Real Estate Portfolio Project Manager | Early Career Program"


def test_parse_file_detects_indeed(tmp_path):
    from jobbtracker.inbox import parse_file
    path = tmp_path / "indeed.html"
    path.write_text((FIXTURES / "indeed_search.html").read_text())
    assert {j["source"] for j in parse_file(path, TODAY)} == {"indeed"}


def test_linkedin_open_ad_text_is_attached_to_its_card():
    page = ('<div componentkey="job-card-component-ref-111"><p>Graduate Analyst</p><p>BlackRock</p><p>Stockholm</p></div>'
            '<div componentkey="job-card-component-ref-222"><p>Business Analyst</p><p>Volvo</p><p>Göteborg</p></div>'
            '<a href="https://www.linkedin.com/jobs/search-results/?currentJobId=222&amp;start=25">Se alla</a>'
            '<h2>Om jobbet</h2><p>Start in August 2027.</p><p>Sista ansökningsdag: 30 november 2026</p>'
            '<h2>Om företaget</h2><p>Volvo builds trucks. Deadline 1 January 2030</p>')
    graduate, analyst = parse_linkedin(page, TODAY)
    assert "text" not in graduate
    assert "Sista ansökningsdag: 30 november 2026" in analyst["text"]
    assert "trucks" not in analyst["text"]


def test_indeed_open_ad_text_is_attached_to_its_card():
    page = ('<div class="job_seen_beacon"><a data-jk="aaaa000000000001"><span title="Analyst" id="jobTitle-1"></span></a>'
            '<span data-testid="company-name">Knowit</span><div data-testid="text-location">Stockholm</div></div>'
            '<div class="job_seen_beacon"><a data-jk="aaaa000000000002"><span title="Mentorship Program" id="jobTitle-2"></span></a>'
            '<span data-testid="company-name">Knowit</span><div data-testid="text-location">Stockholm</div></div>'
            '<div class="jobsearch-RightPane"><a href="/viewjob?jk=aaaa000000000002">Apply</a>'
            '<div class="react-native-html-content simple-job-description-html"><style>p{margin:0}</style>'
            '<p>Application deadline: 23:59 (CET) 22nd of November 2026</p></div>'
            '<div id="vj-rcv-flag-sentinel-jobDescriptionSeen"></div></div>')
    first, second = parse_indeed(page)
    assert "text" not in first
    assert second["text"] == "Application deadline: 23:59 (CET) 22nd of November 2026"
