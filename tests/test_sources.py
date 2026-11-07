import json
from datetime import date
from pathlib import Path

from jobbtracker.models import Company
from jobbtracker.sources import (
    ashby,
    greenhouse,
    jobtech,
    lever,
    smartrecruiters,
    teamtailor,
    workable,
    workday,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def company(**kw):
    defaults = dict(name="Acme", segment="Consulting", cities=["Stockholm"], careers_url="",
                    ats="greenhouse", feed="")
    return Company(**{**defaults, **kw})


class FakeHttp:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get_json(self, url):
        self.calls.append(("GET", url, None))
        return self.responses[url]

    def post_json(self, url, body):
        self.calls.append(("POST", url, body))
        return self.responses[(url, body.get("searchText"))]

    def get_text(self, url):
        self.calls.append(("GET", url, None))
        return self.responses[url]


def test_jobtech_parse():
    posts = jobtech.parse(load("jobtech.json"))
    first, second = posts
    assert first.company == "Scania CV AB"
    assert first.title == "Examensarbete inom inköp och supply chain"
    assert first.ad_url == "https://arbetsformedlingen.se/platsbanken/annonser/31633599"
    assert first.apply_url == "https://scania.com/apply/123"
    assert first.location == "Södertälje, Stockholms län"
    assert first.deadline == date(2026, 11, 19)
    assert first.posted == date(2026, 10, 22)
    assert first.source == "jobtech"
    assert "våren 2027" in first.text
    # No external apply link: applying happens via Platsbanken itself.
    assert second.apply_url == second.ad_url
    assert second.deadline is None


def test_jobtech_stockholm_county_fallback():
    # Municipalities not in our alias list still count as Stockholm via the county.
    assert "Stockholms län" in jobtech.parse(load("jobtech.json"))[0].location


def test_greenhouse_parse():
    [p] = greenhouse.parse(load("greenhouse.json"), "Example Bank")
    assert p.company == "Example Bank"
    assert p.title == "Summer Analyst 2027 - Investment Banking"
    assert p.ad_url == p.apply_url == "https://boards.greenhouse.io/examplebank/jobs/7001"
    assert "London" in p.location
    assert p.posted == date(2026, 10, 1)
    assert p.text == "Join our IBD team. Application deadline: 2026-12-01"


def test_lever_parse():
    [p] = lever.parse(load("lever.json"), "Acme")
    assert p.ad_url == "https://jobs.lever.co/acme/abc-1"
    assert p.apply_url == "https://jobs.lever.co/acme/abc-1/apply"
    assert "Stockholm" in p.location and "Gothenburg" in p.location
    assert "September 2027" in p.text and "15 December 2026" in p.text
    assert p.posted is not None


def test_teamtailor_parse():
    [p] = teamtailor.parse((FIXTURES / "teamtailor.rss").read_text(), "Fortos")
    assert p.title == "Associate Consultant"
    assert p.ad_url == "https://career.fortos.se/jobs/123-associate-consultant"
    assert "Stockholm" in p.location
    assert p.text == "Vi söker dig som är nyexaminerad civilingenjör."
    assert p.posted == date(2026, 11, 3)


def test_workday_public_base():
    feed = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/External/jobs"
    assert workday.public_base(feed) == "https://acme.wd3.myworkdayjobs.com/External"


def test_workday_fetch_searches_terms_and_loads_details_for_candidates():
    feed = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/External/jobs"
    detail_url = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/External/job/Gothenburg/Master-Thesis---Logistics_R123"
    empty = {"total": 0, "jobPostings": []}
    responses = {(feed, term): empty for term in workday.SEARCH_TERMS}
    responses[(feed, "thesis")] = load("workday_list.json")
    responses[(feed, "logistics")] = load("workday_list.json")  # duplicate hit across terms
    responses[detail_url] = load("workday_detail.json")
    http = FakeHttp(responses)

    [p] = workday.fetch(company(ats="workday", feed=feed), http)

    assert p.title == "Master Thesis - Logistics"
    assert p.ad_url == "https://acme.wd3.myworkdayjobs.com/External/job/Gothenburg/Master-Thesis---Logistics_R123"
    assert p.apply_url == p.ad_url + "/apply"
    assert "Gothenburg" in p.location and "Stockholm" in p.location
    assert p.text == "The thesis runs during spring 2027."
    assert p.posted == date(2026, 11, 4)
    assert sum(1 for c in http.calls if c[1] == detail_url) == 1


def test_smartrecruiters_parse():
    [p] = smartrecruiters.parse(load("smartrecruiters.json"), "Acme", "Acme")
    assert p.title == "Summer Internship Procurement"
    assert p.ad_url == "https://jobs.smartrecruiters.com/Acme/744000"
    assert p.location == "Stockholm, Sweden"
    assert p.posted == date(2026, 10, 20)


def test_workable_parse():
    [p] = workable.parse(load("workable.json"), "Acme")
    assert p.apply_url == "https://apply.workable.com/j/AB12/apply"
    assert p.location == "Oslo, Norway"
    assert p.text == "Entry level role."


def test_ashby_parse():
    [p] = ashby.parse(load("ashby.json"), "Acme")
    assert "Copenhagen" in p.location and "Helsinki" in p.location
    assert p.apply_url == "https://jobs.ashbyhq.com/acme/1/application"
    assert p.posted == date(2026, 10, 28)


def test_workday_location_prefilter():
    assert workday.location_may_match("Stockholm")
    assert workday.location_may_match("3 Locations")
    assert workday.location_may_match("")
    assert not workday.location_may_match("New York, NY")
    assert not workday.location_may_match("Bengaluru")


def test_recruitee_parse():
    from jobbtracker.sources import recruitee
    [p] = recruitee.parse(load("recruitee.json"), "IK Partners")
    assert p.ad_url == "https://ikpartners.recruitee.com/o/off-cycle-analyst-intern-amsterdam"
    assert p.apply_url.endswith("/c/new")
    assert "Amsterdam" in p.location and "Stockholm" in p.location
    assert p.posted == date(2026, 9, 28)
    assert "private equity" in p.text and "January 2027" in p.text


def test_workday_skips_listings_without_path():
    feed = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/External/jobs"
    empty = {"total": 0, "jobPostings": []}
    responses = {(feed, term): empty for term in workday.SEARCH_TERMS}
    responses[(feed, "intern")] = {"total": 1, "jobPostings": [{"title": "Summer Intern"}]}
    assert workday.fetch(company(ats="workday", feed=feed), FakeHttp(responses)) == []
