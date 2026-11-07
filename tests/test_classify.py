from datetime import date

import pytest

from jobbtracker.classify import (
    classify_areas,
    classify_type,
    extract_deadline,
    extract_period,
    normalize_city,
)

TODAY = date(2026, 11, 7)


class TestClassifyType:
    @pytest.mark.parametrize(
        "title",
        [
            "Summer Analyst 2027 - Investment Banking",
            "Summer Internship - Strategy Consulting",
            "Sommarpraktik inom revision",
            "Intern, Supply Chain",
            "Off-cycle Internship M&A",
            "Praktikant Corporate Finance",
        ],
    )
    def test_internship(self, title):
        assert classify_type(title, "") == "Internship"

    @pytest.mark.parametrize(
        "title",
        [
            "Graduate Programme 2027",
            "Management Trainee",
            "Traineeprogram inom inköp",
            "Global Graduate Program - Finance",
            "Associate Consultant - Graduate Intake 2027",
        ],
    )
    def test_graduate(self, title):
        assert classify_type(title, "") == "Graduate"

    @pytest.mark.parametrize(
        "title",
        [
            "Examensarbete: Optimering av lagerflöden",
            "Master Thesis - Pricing Strategy",
            "Exjobb inom supply chain",
            "Thesis worker, procurement analytics",
        ],
    )
    def test_thesis(self, title):
        assert classify_type(title, "") == "Thesis"

    @pytest.mark.parametrize(
        "title,text",
        [
            ("Analyst, M&A", "We are looking for a recent graduate to join our team."),
            ("Junior Consultant", ""),
            ("Associate Auditor", "Nyexaminerad civilingenjör eller civilekonom."),
            ("Business Analyst", "0-2 years of experience."),
            ("Entry Level Financial Analyst", ""),
        ],
    )
    def test_junior(self, title, text):
        assert classify_type(title, text) == "Junior"

    @pytest.mark.parametrize(
        "title,text",
        [
            ("Senior Manager, Transaction Services", ""),
            ("Head of Procurement", ""),
            ("Analyst, M&A", "You have 5+ years of experience in investment banking."),
            ("Lagerarbetare", ""),
            ("Director, Private Equity", ""),
        ],
    )
    def test_not_student_role(self, title, text):
        assert classify_type(title, text) is None

    def test_senior_overrides_intern_keyword_in_text(self):
        assert classify_type("Senior Associate", "Supervise our interns.") is None

    def test_thesis_beats_internship(self):
        assert classify_type("Thesis internship - Logistics", "") == "Thesis"


class TestClassifyAreas:
    def test_investment_banking(self):
        assert "IB" in classify_areas("Summer Analyst - Investment Banking Division", "")

    def test_ma_from_title(self):
        assert "M&A" in classify_areas("Analyst, Mergers & Acquisitions", "")

    def test_corporate_finance_is_ma(self):
        assert "M&A" in classify_areas("Corporate Finance Intern", "")

    def test_private_equity(self):
        assert "PE" in classify_areas("Private Equity Summer Intern", "")

    def test_audit_swedish(self):
        assert "Audit" in classify_areas("Revisorsassistent", "")

    def test_supply_chain(self):
        areas = classify_areas("Graduate Programme - Procurement & Logistics", "")
        assert "Supply chain" in areas

    def test_consulting(self):
        assert "Consulting" in classify_areas("Management Consultant Intern", "")

    def test_strategy(self):
        assert "Strategy" in classify_areas("Business Development & Strategy Trainee", "")

    def test_analytics(self):
        assert "Analytics" in classify_areas("Data Analyst Intern", "")

    def test_segment_default_when_nothing_matches(self):
        assert classify_areas("Summer Internship 2027", "", segment="PE") == ["PE"]

    def test_unrelated_role_has_no_area(self):
        assert classify_areas("Software Engineer Intern", "") == []

    def test_unrelated_role_ignores_bank_segment(self):
        assert classify_areas("Software Engineer Intern", "", segment="Bank") == []


class TestNormalizeCity:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Stockholm, Sweden", "Stockholm"),
            ("Solna", "Stockholm"),
            ("Göteborg", "Gothenburg"),
            ("Gothenburg, Västra Götaland", "Gothenburg"),
            ("Mölndal", "Gothenburg"),
            ("Partille, Västra Götalands län", "Gothenburg"),
            ("Kungälv", "Gothenburg"),
            ("London, United Kingdom", "London"),
            ("Frankfurt am Main", "Frankfurt"),
            ("Amsterdam, NL", "Amsterdam"),
            ("Zürich", "Zurich"),
            ("Oslo", "Oslo"),
            ("København", "Copenhagen"),
            ("Helsinki, Finland", "Helsinki"),
        ],
    )
    def test_known(self, raw, expected):
        assert normalize_city(raw) == expected

    @pytest.mark.parametrize("raw", ["New York", "Malmö", "", "Remote"])
    def test_unknown(self, raw):
        assert normalize_city(raw) is None


class TestExtractPeriod:
    def test_summer_from_title(self):
        assert extract_period("Summer Analyst 2027", "", TODAY) == "Summer 2027"

    def test_swedish_summer(self):
        assert extract_period("Sommarjobb 2027", "", TODAY) == "Summer 2027"

    def test_summer_without_year_uses_next_summer(self):
        assert extract_period("Summer Internship", "", TODAY) == "Summer 2027"

    def test_month_range(self):
        text = "The internship runs from June to August 2027."
        assert extract_period("Intern", text, TODAY) == "Jun–Aug 2027"

    def test_start_month(self):
        text = "The programme starts in September 2027."
        assert extract_period("Graduate Programme", text, TODAY) == "Start Sep 2027"

    def test_swedish_start(self):
        text = "Programmet startar i augusti 2027."
        assert extract_period("Traineeprogram", text, TODAY) == "Start Aug 2027"

    def test_spring_thesis(self):
        text = "Examensarbetet utförs under våren 2027."
        assert extract_period("Examensarbete", text, TODAY) == "Spring 2027"

    def test_graduate_intake_year(self):
        assert extract_period("Graduate Programme 2027", "", TODAY) == "2027"

    def test_unknown(self):
        assert extract_period("Junior Analyst", "Join our team.", TODAY) is None


class TestExtractDeadline:
    def test_iso(self):
        assert extract_deadline("Application deadline: 2026-11-30", TODAY) == date(2026, 11, 30)

    def test_english_long(self):
        assert extract_deadline("Apply by 15 December 2026.", TODAY) == date(2026, 12, 15)

    def test_swedish(self):
        text = "Sista ansökningsdag är den 1 december."
        assert extract_deadline(text, TODAY) == date(2026, 12, 1)

    def test_month_first(self):
        assert extract_deadline("Deadline: January 10, 2027", TODAY) == date(2027, 1, 10)

    def test_yearless_date_in_past_rolls_forward(self):
        assert extract_deadline("Deadline 15 January", TODAY) == date(2027, 1, 15)

    def test_rolling(self):
        assert extract_deadline("We review applications on a rolling basis.", TODAY) is None

    def test_none(self):
        assert extract_deadline("Welcome to apply!", TODAY) is None


class TestRealWorldMisses:
    """Regressions found when running against live JobTech data."""

    @pytest.mark.parametrize(
        "title,area",
        [
            ("Junior Business Developer", "Strategy"),
            ("Volvo Group Graduate Program 2027 - Supply Chain Developer", "Supply chain"),
            ("Volvo Group Graduate Program - Business Dev. & Digitalization Engineer", "Strategy"),
            ("Junior verksamhetsutvecklare till område AI och Data", "Strategy"),
            ("Praktikplats vid Riksgälden – avdelningen Finansiell stabilitet", "Finance"),
            ("Praktikant Upphandling/anbud", "Supply chain"),
        ],
    )
    def test_business_area_beats_off_target(self, title, area):
        assert area in classify_areas(title, "")

    def test_plain_developer_still_off_target(self):
        assert classify_areas("Junior Java-utvecklare", "") == []

    def test_area_from_text_for_programmes(self):
        text = "Som trainee roterar du mellan inköp, logistik och supply chain."
        assert classify_areas("F15 Graduate Programme 2027", text, use_text=True) == ["Supply chain"]

    def test_text_not_used_by_default(self):
        text = "Som trainee roterar du mellan inköp, logistik och supply chain."
        assert classify_areas("F15 Graduate Programme 2027", text) == []


class TestConsultingFeedMisses:
    """Regressions from the live consulting/audit feeds."""

    @pytest.mark.parametrize(
        "title",
        [
            "Architecture Intern",
            "Summer Intern HVAC",
            "Graduate Acoustics Consultant 2027",
            "Drømmer du om at arbejde med events? Bliv Employer Branding-praktikant",
            "Praktikant – få bred erfaring med HR, læring og udvikling",
            "Junior Network Consultant",
            "Marketing Intern",
            "Structural Engineer Graduate",
        ],
    )
    def test_off_target_even_at_consulting_firm(self, title):
        assert classify_areas(title, "", segment="Consulting") == []

    def test_month_year_in_title_is_start(self):
        title = "Junior Consultant till Monitor Deloitte (Stockholm) - Aug 2027"
        assert extract_period(title, "", TODAY) == "Start Aug 2027"

    def test_quarter(self):
        assert extract_period("Intern - Q3 2027 (start date July, August or September)", "", TODAY) == "Q3 2027"


class TestFullRunMisses:
    """Regressions from the first full run across all company feeds."""

    @pytest.mark.parametrize(
        "title",
        [
            "AI Engineering Internship",
            "Engineering (Manufacturing) Summer Internship 2027",
            "Junior Consultant Cyber Security (Dutch speaker)",
            "Junior Creative Designer",
            "Junior Fashion Designer - Women's Jersey",
            "Talent Acquisition Intern (Early Careers)",
            "Talent Brand & Acquisition Trainee",
            "Werkstudent Recruitment",
            "Deloitte SAP Graduate Dinner 2026",
            "Boost Your Consulting Skills: Graduate Consulting Club x Roland Berger",
            "Sales Summer Internship 2027",
            "Praktik/LIA – Underhållstekniker",
        ],
    )
    def test_excluded(self, title):
        assert classify_areas(title, "", segment="Consulting") == []

    def test_sales_and_trading_is_ib(self):
        areas = classify_areas("Sales, Trading and Structuring Off Cycle Internship Programme 2027", "", segment="Bank")
        assert areas == ["IB"]

    def test_buyer_is_supply_chain(self):
        assert classify_areas("Junior Buyer - Womenswear", "") == ["Supply chain"]


class TestLinkedInImportMisses:
    def test_programme_title_beats_senior_word(self):
        title = "Volvo Group Graduate Program 2027 - Technology Exploration Manager"
        assert classify_type(title, "") == "Graduate"

    def test_product_manager_intern(self):
        assert classify_type("Product Manager Intern", "") == "Internship"

    def test_swedish_plural_junior(self):
        assert classify_type("Juniora Analysts till Deloitte Digital (Stockholm) - Aug 2027", "") == "Junior"

    def test_transformation_role_with_engineering_word(self):
        title = "Juniora Analysts till Operations Transformation, Engineering, AI & Data (Stockholm) – Aug 2027"
        assert "Strategy" in classify_areas(title, "")

    def test_engineering_internship_still_excluded(self):
        assert classify_areas("Digital Engineering Internship", "", segment="Consulting") == []
