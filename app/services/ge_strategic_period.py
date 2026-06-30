"""Strategic period helpers (M29 · §3.3.6)."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from fastapi import HTTPException

LIFECYCLE_ACTIVE = "active"
LIFECYCLE_PENDING = "pending_assessment"
LIFECYCLE_MET = "met"
LIFECYCLE_PARTIAL = "partial_met"
LIFECYCLE_NOT_MET = "not_met"
LIFECYCLE_ARCHIVED = "archived"

TERMINAL_LIFECYCLES = frozenset(
    {LIFECYCLE_MET, LIFECYCLE_PARTIAL, LIFECYCLE_NOT_MET, LIFECYCLE_ARCHIVED}
)
LOCKED_LIFECYCLES = frozenset({LIFECYCLE_PENDING, *TERMINAL_LIFECYCLES})


def today() -> date:
    return date.today()


def year_bounds(year: int) -> tuple[str, str]:
    return f"{year}-01-01", f"{year}-12-31"


def current_year_bounds() -> tuple[str, str]:
    y = today().year
    return year_bounds(y)


def quarter_bounds_for(d: date) -> tuple[str, str]:
    q = (d.month - 1) // 3
    start_month = q * 3 + 1
    end_month = start_month + 2
    last_day = monthrange(d.year, end_month)[1]
    return (
        f"{d.year}-{start_month:02d}-01",
        f"{d.year}-{end_month:02d}-{last_day:02d}",
    )


def default_sub_period() -> tuple[str, str, str]:
    start, end = quarter_bounds_for(today())
    return "quarter", start, end


def parse_ymd(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def planning_year_from_start(period_start: str | None) -> int | None:
    if not period_start:
        return None
    return parse_ymd(period_start).year


def is_month_boundary(start: str, end: str) -> bool:
    s, e = parse_ymd(start), parse_ymd(end)
    if s.day != 1:
        return False
    last = monthrange(e.year, e.month)[1]
    return e.day == last and s.year == e.year and s.month == e.month


def is_quarter_boundary(start: str, end: str) -> bool:
    s, e = parse_ymd(start), parse_ymd(end)
    if s.day != 1 or (s.month - 1) % 3 != 0:
        return False
    end_month = s.month + 2
    last = monthrange(e.year, end_month)[1]
    return e.year == s.year and e.month == end_month and e.day == last


def is_year_boundary(start: str, end: str) -> bool:
    y = parse_ymd(start).year
    return start == f"{y}-01-01" and end == f"{y}-12-31"


def validate_sub_objective_period(granularity: str, start: str, end: str) -> None:
    if granularity not in ("month", "quarter", "year"):
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})
    if granularity == "month" and not is_month_boundary(start, end):
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})
    if granularity == "quarter" and not is_quarter_boundary(start, end):
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})
    if granularity == "year" and not is_year_boundary(start, end):
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})


def validate_sub_program_period(granularity: str, start: str, end: str) -> None:
    if granularity not in ("month", "quarter"):
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})
    if granularity == "month" and not is_month_boundary(start, end):
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})
    if granularity == "quarter" and not is_quarter_boundary(start, end):
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})


def validate_company_period(granularity: str, start: str, end: str) -> None:
    if granularity != "year":
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})
    if not is_year_boundary(start, end):
        raise HTTPException(status_code=400, detail={"detail": "period_granularity_invalid"})


def period_within_bounds(child_start: str, child_end: str, parent_start: str, parent_end: str) -> bool:
    cs, ce = parse_ymd(child_start), parse_ymd(child_end)
    ps, pe = parse_ymd(parent_start), parse_ymd(parent_end)
    return ps <= cs and ce <= pe


def company_ancestor_bounds(db, objective) -> tuple[str, str] | None:
    from app.models.ge import GeObjective

    current = objective
    while current is not None:
        if current.level == "company" and current.period_start and current.period_end:
            return current.period_start, current.period_end
        if current.parent_id is None:
            break
        current = db.get(GeObjective, current.parent_id)
    return None
