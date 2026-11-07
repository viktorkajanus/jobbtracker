import json
from datetime import date

from jobbtracker.models import Company, Posting
from jobbtracker.run import load_companies, run

TODAY = date(2026, 11, 7)

TOML = """
[[company]]
name = "Acme Bank"
segment = "IB"
cities = ["London"]
careers_url = "https://acme.example/careers"
ats = "greenhouse"
feed = "https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"

[[company]]
name = "Broken Co"
segment = "Consulting"
cities = ["Stockholm"]
careers_url = "https://broken.example"
ats = "lever"
feed = "https://api.lever.co/v0/postings/broken?mode=json"

[[company]]
name = "Manual Co"
segment = "PE"
cities = ["Stockholm"]
careers_url = "https://manual.example"
ats = "unsupported"
"""


def test_load_companies(tmp_path):
    path = tmp_path / "companies.toml"
    path.write_text(TOML)
    companies = load_companies([path])
    assert [c.name for c in companies] == ["Acme Bank", "Broken Co", "Manual Co"]
    assert companies[0].feed.startswith("https://boards-api")


def test_run_writes_jobs_and_source_status(tmp_path):
    (tmp_path / "companies.toml").write_text(TOML)
    out = tmp_path / "jobs.json"
    out.write_text(json.dumps({"jobs": [
        {"id": "kept1", "company": "Broken Co", "title": "Junior Consultant", "type": "Junior", "areas": ["Consulting"],
         "cities": ["Stockholm"], "period": None, "deadline": None, "posted": None, "first_seen": "2026-10-01",
         "apply_url": "u", "ad_url": "u", "source": "lever"},
    ]}))

    def fetch_company(company, http):
        if company.name == "Broken Co":
            raise TimeoutError("boom")
        return [Posting(source="greenhouse", company=company.name, title="Summer Analyst 2027 - IBD",
                        ad_url="https://acme/1", apply_url="https://acme/1", location="London")]

    def fetch_jobtech(http):
        return [Posting(source="jobtech", company="X AB", title="Trainee inom inköp",
                        ad_url="https://af/2", apply_url="https://af/2", location="Solna, Stockholms län")]

    run(companies_paths=[tmp_path / "companies.toml"], out_path=out, today=TODAY,
        fetch_company=fetch_company, fetch_jobtech=fetch_jobtech, http=None)

    data = json.loads(out.read_text())
    titles = sorted(j["title"] for j in data["jobs"])
    assert titles == ["Junior Consultant", "Summer Analyst 2027 - IBD", "Trainee inom inköp"]
    acme = next(j for j in data["jobs"] if j["company"] == "Acme Bank")
    assert acme["areas"] == ["IB"]
    assert data["generated"] == "2026-11-07"
    status = {s["name"]: s for s in data["sources"]}
    assert status["Acme Bank"]["ok"] and status["Acme Bank"]["count"] == 1
    assert not status["Broken Co"]["ok"] and "boom" in status["Broken Co"]["error"]
    assert status["JobTech"]["ok"]
    assert "Manual Co" not in status
    assert data["manual"] == [{"name": "Manual Co", "segment": "PE", "careers_url": "https://manual.example"}]
