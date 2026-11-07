from datetime import date

from jobbtracker.models import Posting
from jobbtracker.pipeline import build_job, dedupe, merge_with_previous

TODAY = date(2026, 11, 7)


def posting(**kw):
    defaults = dict(source="greenhouse", company="Acme", title="Summer Analyst 2027 - M&A",
                    ad_url="https://x/1", apply_url="https://x/1/apply", location="Stockholm",
                    text="", segment="IB")
    return Posting(**{**defaults, **kw})


class TestBuildJob:
    def test_full_record(self):
        job = build_job(posting(text="Application deadline: 2026-12-01", posted=date(2026, 10, 1)), TODAY)
        assert job == {
            "id": job["id"],
            "company": "Acme",
            "title": "Summer Analyst 2027 - M&A",
            "type": "Internship",
            "areas": ["M&A"],
            "cities": ["Stockholm"],
            "period": "Summer 2027",
            "deadline": "2026-12-01",
            "posted": "2026-10-01",
            "first_seen": "2026-11-07",
            "apply_url": "https://x/1/apply",
            "ad_url": "https://x/1",
            "source": "greenhouse",
        }
        assert len(job["id"]) == 12

    def test_source_deadline_wins_over_text(self):
        job = build_job(posting(deadline=date(2026, 11, 20), text="Deadline 2026-12-01"), TODAY)
        assert job["deadline"] == "2026-11-20"

    def test_drops_senior(self):
        assert build_job(posting(title="Vice President, M&A"), TODAY) is None

    def test_drops_off_target(self):
        assert build_job(posting(title="Software Engineer Intern"), TODAY) is None

    def test_drops_untracked_city(self):
        assert build_job(posting(location="New York, NY"), TODAY) is None

    def test_drops_expired(self):
        assert build_job(posting(deadline=date(2026, 11, 1)), TODAY) is None

    def test_multiple_cities(self):
        job = build_job(posting(location="London; Stockholm; New York"), TODAY)
        assert job["cities"] == ["Stockholm", "London"]

    def test_jobtech_stockholm_county_counts_as_stockholm(self):
        job = build_job(posting(source="jobtech", segment=None, location="Upplands Väsby, Stockholms län",
                                title="Trainee inom inköp"), TODAY)
        assert job["cities"] == ["Stockholm"]

    def test_jobtech_requires_an_area(self):
        p = posting(source="jobtech", segment=None, title="Trainee butik")
        assert build_job(p, TODAY) is None

    def test_company_source_allows_general_area(self):
        job = build_job(posting(segment="Industry", title="Global Graduate Programme 2027"), TODAY)
        assert job["areas"] == []


def job(**kw):
    defaults = dict(id="a", company="Scania", title="Examensarbete inköp", type="Thesis", areas=["Supply chain"],
                    cities=["Stockholm"], period=None, deadline=None, posted=None, first_seen="2026-11-07",
                    apply_url="u", ad_url="u", source="workday")
    return {**defaults, **kw}


class TestDedupe:
    def test_prefers_company_source_over_jobtech(self):
        a = job(id="a", source="jobtech", company="Scania CV AB", deadline="2026-12-01")
        b = job(id="b", source="workday", company="Scania")
        [kept] = dedupe([a, b])
        assert kept["id"] == "b"
        # Fills gaps from the duplicate it replaced.
        assert kept["deadline"] == "2026-12-01"

    def test_keeps_different_titles(self):
        assert len(dedupe([job(id="a"), job(id="b", title="Graduate Programme")])) == 2

    def test_keeps_same_title_in_different_cities(self):
        assert len(dedupe([job(id="a"), job(id="b", cities=["London"])])) == 2

    def test_title_match_ignores_case_and_punctuation(self):
        assert len(dedupe([job(id="a", title="Summer Analyst - IBD"), job(id="b", title="summer analyst, ibd")])) == 1


class TestMerge:
    def test_keeps_first_seen_from_previous_run(self):
        prev = [job(id="a", first_seen="2026-10-01")]
        [merged] = merge_with_previous([job(id="a", first_seen="2026-11-07")], prev, failed_sources=set(), today=TODAY)
        assert merged["first_seen"] == "2026-10-01"

    def test_vanished_job_is_dropped(self):
        prev = [job(id="old")]
        assert merge_with_previous([], prev, failed_sources=set(), today=TODAY) == []

    def test_jobs_from_failed_source_are_kept(self):
        prev = [job(id="old", company="Acme", source="greenhouse")]
        merged = merge_with_previous([], prev, failed_sources={"Acme"}, today=TODAY)
        assert [j["id"] for j in merged] == ["old"]

    def test_kept_job_still_expires(self):
        prev = [job(id="old", company="Acme", deadline="2026-11-01")]
        assert merge_with_previous([], prev, failed_sources={"Acme"}, today=TODAY) == []


def test_jobtech_technical_thesis_not_rescued_by_ad_text():
    p = posting(source="jobtech", segment=None, title="Master thesis - Structural Analysis",
                text="You will work with our consultants on transaction data.")
    assert build_job(p, TODAY) is None


def test_jobtech_graduate_programme_area_from_text():
    p = posting(source="jobtech", segment=None, title="F15 Graduate Programme 2027",
                text="Rotations within procurement and logistics.")
    assert build_job(p, TODAY)["areas"] == ["Supply chain"]


def test_industry_thesis_without_business_area_is_dropped():
    p = posting(segment="Industry", title="Master Thesis – R&D Nonwoven Linting Analysis")
    assert build_job(p, TODAY) is None


def test_industry_graduate_programme_without_area_is_kept():
    p = posting(segment="Industry", title="Global Graduate Programme 2027")
    assert build_job(p, TODAY) is not None
