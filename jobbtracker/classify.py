"""Rule-based classification of job postings.

Everything here is a pure function of the posting text so it is easy to test and
easy to replace with an AI classifier later.
"""

from __future__ import annotations

import re
from datetime import date

# --- Type -------------------------------------------------------------------

SENIOR = re.compile(
    r"\b(senior|sr\.?|manager|director|head of|lead|principal|partner|"
    r"vice president|vp|chef|experienced|expert|specialist)\b"
)
THESIS = re.compile(r"\b(thesis|examensarbete\w*|exjobb\w*|master'?s project)\b")
INTERNSHIP = re.compile(
    r"\b(intern|interns|internship\w*|summer (analyst|associate|programme|program|job)|"
    r"sommar\w*|praktik\w*|off[- ]cycle|placement|working student|werkstudent)\b"
)
GRADUATE = re.compile(
    r"\b(graduate (programme|program|intake|scheme)|graduate\b|trainee\w*|traineeprogram\w*)"
)
JUNIOR_EXPLICIT = re.compile(r"\b(junior\w*|entry[- ]level|nyexaminerad\w*)\b")
JUNIOR_AMBIGUOUS = re.compile(
    r"\b(analyst|associate|consultant|konsult|auditor|revisorsassistent|"
    r"revisor|controller|ekonom|advisor|investment professional)\b"
)
GRADUATE_SIGNAL = re.compile(
    r"(recent(ly)? graduat\w*|new(ly)? graduat\w*|nyexaminerad\w*|nyutexaminerad\w*|"
    r"entry[- ]level|no prior experience|\b0\s*[-–]\s*[12]\s*(years?|år))"
)
EXPERIENCE = re.compile(
    r"(?:(\d+)\s*[-–]\s*)?(\d+)\s*\+?\s*(?:years?|års?)\b(?:\s+of)?"
    r"(?:\s+(?:relevant|professional|work|previous))?\s+(?:experience|erfarenhet)"
)


def _min_years_required(text: str) -> int | None:
    years = []
    for low, high in EXPERIENCE.findall(text):
        years.append(int(low) if low else int(high))
    return min(years) if years else None


def classify_type(title: str, text: str) -> str | None:
    """Return Internship, Graduate, Thesis, Junior, or None for non-student roles."""
    t = title.lower()
    body = text.lower()
    # Programme words win over seniority words ("Graduate Program - Exploration Manager").
    if THESIS.search(t):
        return "Thesis"
    if INTERNSHIP.search(t):
        return "Internship"
    if GRADUATE.search(t):
        return "Graduate"
    if SENIOR.search(t):
        return None
    required = _min_years_required(body)
    if required is not None and required >= 3:
        return None
    if JUNIOR_EXPLICIT.search(t):
        return "Junior"
    if JUNIOR_AMBIGUOUS.search(t) and GRADUATE_SIGNAL.search(body):
        return "Junior"
    return None


# --- Area -------------------------------------------------------------------

AREAS: list[tuple[str, re.Pattern]] = [
    ("IB", re.compile(r"investment bank\w*|\bibd\b|capital markets|\becm\b|\bdcm\b|leveraged finance|"
                     r"sales,?\s*(and|&)?\s*trading")),
    ("M&A", re.compile(r"\bm&a\b|merger|acquisition|corporate finance|transaction|deal advisory|valuation")),
    ("PE", re.compile(r"private equity|buy-?out|venture capital")),
    ("Consulting", re.compile(r"consult\w*|konsult\w*")),
    ("Audit", re.compile(r"audit\w*|revision|revisor\w*|assurance")),
    ("Supply chain", re.compile(r"supply chain|procurement|purchas\w*|\bbuyer|inköp\w*|upphandl\w*|logisti\w*|sourcing")),
    ("Strategy", re.compile(r"strateg\w*|business dev\w*|affärsutveckl\w*|verksamhetsutveckl\w*|corporate development|transformation")),
    ("Analytics", re.compile(r"analytics|data analy\w*|business intelligence|\bbi\b|business analyst")),
    ("Finance", re.compile(r"financ\w*|finans\w*|controller|treasury|\bekonom\w*|accounting|redovisning")),
]

# Technical roles: excluded unless the title also names a business area
# ("Supply Chain Developer", "Business Developer").
SOFT_OFF_TARGET = re.compile(
    r"software|developer|utvecklare|\bengineer\b|devops|frontend|backend|full[- ]?stack|"
    r"\bit[- ]|machine learning|\bengineering\b"
)
# Roles that stay excluded whatever else the title says.
HARD_OFF_TARGET = re.compile(
    r"nurse|sjuksköt|lager|warehouse|driver|chaufför|säljare|telemarket|kundtjänst|customer service|"
    r"receptionist|architect\w*|arkitekt\w*|hvac|acoustic\w*|akustik\w*|structural|konstruktion\w*|"
    r"geotechn\w*|electrical|mechanical|\bhr\b|human resources|employer brand\w*|marketing|"
    r"communicat\w*|kommunikat\w*|\bevents?\b|\bnetwork\b|cyber|designer|"
    r"talent acquisition|talent brand|recruit(er|ment|ing)?\b|dinner|\bclub\b|tekniker|"
    r"\bsales\b(?!,?\s*(and|&)?\s*trading)"
)

SEGMENT_AREAS = {"IB": "IB", "PE": "PE", "M&A": "M&A", "Consulting": "Consulting", "Audit": "Audit"}


def _areas_in(s: str) -> list[str]:
    return [name for name, pattern in AREAS if pattern.search(s)]


def is_off_target(title: str) -> bool:
    """Technical or unrelated roles, unless the title also names a business area."""
    t = title.lower()
    if HARD_OFF_TARGET.search(t):
        return True
    return bool(SOFT_OFF_TARGET.search(t)) and not _areas_in(t)


def classify_areas(title: str, text: str, segment: str | None = None, use_text: bool = False) -> list[str]:
    """Areas inferred from the title, then optionally the ad text, then the company's segment."""
    t = title.lower()
    if is_off_target(t):
        return []
    areas = _areas_in(t)
    if not areas and use_text:
        areas = _areas_in(text.lower())
    if not areas and segment in SEGMENT_AREAS:
        areas = [SEGMENT_AREAS[segment]]
    return areas


# --- City -------------------------------------------------------------------

CITY_ALIASES = {
    "Stockholm": ["stockholm", "solna", "sundbyberg", "kista", "nacka", "lidingö", "danderyd",
                  "bromma", "sollentuna", "södertälje", "huddinge", "täby"],
    "Gothenburg": ["göteborg", "goteborg", "gothenburg", "mölndal", "molndal", "torslanda",
                   "lindholmen", "hisings", "partille", "kungälv", "lerum", "härryda", "ale kommun",
                   "öckerö", "kungsbacka", "landvetter"],
    "London": ["london"],
    "Frankfurt": ["frankfurt"],
    "Amsterdam": ["amsterdam"],
    "Zurich": ["zürich", "zurich", "zuerich"],
    "Oslo": ["oslo"],
    "Copenhagen": ["copenhagen", "københavn", "kobenhavn", "köpenhamn"],
    "Helsinki": ["helsinki", "helsingfors"],
}

CITIES = list(CITY_ALIASES)
ABROAD = [c for c in CITIES if c not in ("Stockholm", "Gothenburg")]


def normalize_city(raw: str) -> str | None:
    s = raw.lower()
    for city, aliases in CITY_ALIASES.items():
        if any(a in s for a in aliases):
            return city
    return None


def normalize_cities(raw: str) -> list[str]:
    s = raw.lower()
    return [city for city, aliases in CITY_ALIASES.items() if any(a in s for a in aliases)]


# --- Dates ------------------------------------------------------------------

MONTHS = {
    1: ["january", "januari", "jan"],
    2: ["february", "februari", "feb"],
    3: ["march", "mars", "mar"],
    4: ["april", "apr"],
    5: ["may", "maj"],
    6: ["june", "juni", "jun"],
    7: ["july", "juli", "jul"],
    8: ["august", "augusti", "aug"],
    9: ["september", "sept", "sep"],
    10: ["october", "oktober", "oct", "okt"],
    11: ["november", "nov"],
    12: ["december", "dec"],
}
MONTH_ABBR = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_RE = "(" + "|".join(sorted({n for names in MONTHS.values() for n in names}, key=len, reverse=True)) + r")\.?"


def _month_num(name: str) -> int:
    name = name.lower().rstrip(".")
    for num, names in MONTHS.items():
        if name in names:
            return num
    raise ValueError(name)


YEAR = r"(20\d\d)"
RANGE = re.compile(rf"\b{MONTH_RE}\s*(?:to|till|until|through|[-–])\s*{MONTH_RE}\s*,?\s*{YEAR}")
START = re.compile(
    rf"\b(?:start\w*|begin\w*|commenc\w*|börjar|kick[- ]?off)\s+(?:in|i|on|den|from|during)?\s*"
    rf"(?:\d{{1,2}}(?:st|nd|rd|th)?\s+)?{MONTH_RE}\s*,?\s*{YEAR}"
)
QUARTER = re.compile(rf"\bq([1-4])\s*{YEAR}")
SEASONS = [
    ("Summer", re.compile(r"\b(summer|sommar\w*)\b")),
    ("Spring", re.compile(r"\b(spring|vår\w*|vt\s?\d{2,4})\b")),
    ("Autumn", re.compile(r"\b(autumn|fall|höst\w*|ht\s?\d{2,4})\b")),
]


def _season_year(season_re: re.Pattern, s: str) -> int | None:
    near = re.search(rf"(?:{season_re.pattern})\s*(?:of\s*)?{YEAR}|{YEAR}\s*(?:{season_re.pattern})", s)
    if near:
        return int(next(g for g in near.groups() if g and g.isdigit() and len(g) == 4))
    return None


def extract_period(title: str, text: str, today: date) -> str | None:
    """A short human label for when the role takes place, or None if unknown."""
    t, body = title.lower(), text.lower()
    both = f"{t}\n{body}"

    if m := RANGE.search(both):
        a, b, year = _month_num(m.group(1)), _month_num(m.group(2)), m.group(3)
        return f"{MONTH_ABBR[a]}–{MONTH_ABBR[b]} {year}"
    if m := START.search(both):
        return f"Start {MONTH_ABBR[_month_num(m.group(1))]} {m.group(2)}"

    if m := QUARTER.search(both):
        return f"Q{m.group(1)} {m.group(2)}"
    if m := re.search(rf"\b{MONTH_RE}\s*{YEAR}", t):
        return f"Start {MONTH_ABBR[_month_num(m.group(1))]} {m.group(2)}"

    title_year = re.search(YEAR, t)
    for label, season_re in SEASONS:
        source = t if season_re.search(t) else body if season_re.search(body) else None
        if source is None:
            continue
        year = _season_year(season_re, source) or (int(title_year.group(1)) if title_year else None)
        if year is None:
            if label == "Summer":
                year = today.year if today.month <= 6 else today.year + 1
            else:
                continue
        return f"{label} {year}"

    if title_year:
        return title_year.group(1)
    return None


DEADLINE_KEYWORD = re.compile(
    r"(deadline|apply by|apply before|apply no later than|last day (?:to|of) appl\w*|"
    r"closing date|applications? close\w*|sista ansökningsdag\w*|ansök senast|senast den|senast)"
)
ISO_DATE = re.compile(r"\b(20\d\d)-(\d{2})-(\d{2})\b")
DAY_MONTH = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{MONTH_RE}(?:\s*,?\s*{YEAR})?")
MONTH_DAY = re.compile(rf"\b{MONTH_RE}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,?\s*{YEAR})?")


def _parse_date(s: str, today: date) -> date | None:
    candidates = []
    if m := ISO_DATE.search(s):
        candidates.append((m.start(), (int(m.group(1)), int(m.group(2)), int(m.group(3))), True))
    if m := DAY_MONTH.search(s):
        y = m.group(3)
        candidates.append((m.start(), (int(y) if y else None, _month_num(m.group(2)), int(m.group(1))), bool(y)))
    if m := MONTH_DAY.search(s):
        y = m.group(3)
        candidates.append((m.start(), (int(y) if y else None, _month_num(m.group(1)), int(m.group(2))), bool(y)))
    if not candidates:
        return None
    _, (year, month, day), has_year = min(candidates)
    try:
        d = date(year or today.year, month, day)
    except ValueError:
        return None
    if not has_year and d < today:
        d = d.replace(year=d.year + 1)
    return d


def extract_deadline(text: str, today: date) -> date | None:
    s = text.lower()
    for m in DEADLINE_KEYWORD.finditer(s):
        window = s[m.end(): m.end() + 60]
        if d := _parse_date(window, today):
            return d
    return None
