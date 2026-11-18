"""Premium-financing calculation engine.

Pure functions only: standard library, no I/O, no environment access.
Contract: tests/test_engine.py + tests/vectors.json (golden vectors
reverse-verified against the reference tool's live UI, 2026-11-09).

Formulas: docs/02-functional-spec.md §2–§4.
"""

from dataclasses import dataclass, replace
from typing import Optional



# --------------------------------------------------------------------- IRR

def _npv(cashflows: list[float], r: float) -> float:
    base = 1.0 + r
    return sum(cf / base ** t for t, cf in enumerate(cashflows))


def solve_irr(cashflows: list[float]) -> Optional[float]:
    """Annualised IRR of a yearly cashflow series.

    Robust bracketed bisection over (-1, +10]: scan the domain for an NPV
    sign change, then bisect to machine precision. Any correct solver is
    acceptable per docs/02-functional-spec.md §2 — Newton-Raphson was tried
    first but diverges on front-loaded-loss profiles (e.g. the year-5
    golden case jumps to r=2.8 on the first iteration), so this rebuild
    trades solver elegance for guaranteed convergence.

    cashflows[0] is t=0, cashflows[t] is year t. Returns None when the
    series has no sign change (IRR undefined — the reference tool shows "—")
    or no root exists in (-1, +10].
    """
    if not (any(cf > 0 for cf in cashflows) and any(cf < 0 for cf in cashflows)):
        return None

    lo, hi = -0.999999, 10.0
    grid = 10_000
    prev_r, prev_f = lo, _npv(cashflows, lo)
    if prev_f == 0.0:
        return lo
    for i in range(1, grid + 1):
        r = lo + (hi - lo) * i / grid
        f = _npv(cashflows, r)
        if f == 0.0:
            return r
        if prev_f * f < 0:            # sign change → bisect
            a, b = prev_r, r
            for _ in range(200):
                m = (a + b) / 2
                fm = _npv(cashflows, m)
                if abs(fm) < 1e-12:
                    return m
                if prev_f * fm < 0:
                    b = m
                else:
                    a, prev_f = m, fm
            return (a + b) / 2
        prev_r, prev_f = r, f
    return None


# ------------------------------------------------------------- H/P pricing

def effective_rate(hibor_1m: float, h_spread: float,
                   prime_rate: float, p_spread: float) -> float:
    """Adopted loan rate = min(HIBOR(1M) + h_spread, prime - p_spread)."""
    return min(hibor_1m + h_spread, prime_rate - p_spread)


# ------------------------------------------------------------------ params

@dataclass
class ProjectionParams:
    total_premium: float
    discount_percent: float
    surrender0_percent: float
    ltv_percent: float
    bank_fx: float
    fwd_fx: float
    rate_brackets: list          # [{end_year, rate}] — see bracket_rate()
    achievement_percent: float


@dataclass
class Row:
    year: int
    interest: float              # that year's interest (single, not capitalised)
    surrender: float             # total surrender value incl. achievement scaling
    gross: float                 # surrender - loan principal
    net: float                   # gross + outlay - cumulative interest
    irr: Optional[float]
    cashflows: list[float]       # [outlay, -interest x (year-1), gross - interest]


def loan_usd(p: ProjectionParams) -> float:
    """Loan = premium x first-day surrender% x LTV% (surrender-based, not premium-based)."""
    return p.total_premium * p.surrender0_percent / 100 * p.ltv_percent / 100


def outlay_usd(p: ProjectionParams) -> float:
    """Upfront cash outlay in USD (negative = cash outflow)."""
    loan = loan_usd(p)
    return -((p.total_premium * (1 - p.discount_percent / 100)) * p.fwd_fx
             - loan * p.bank_fx) / p.fwd_fx


def bracket_rate(brackets: list, year: int) -> float:
    """First bracket with end_year >= year, or the open segment (end_year = 0)."""
    for b in brackets:
        if b["end_year"] == 0 or b["end_year"] >= year:
            return b["rate"]
    return brackets[-1]["rate"]


# ---------------------------------------------------------------- projection

def project(params, table: list[dict]) -> list[Row]:
    """Year-by-year projection over the benefit table.

    table: [{year, guaranteed, reversionary, special}]. One Row per entry.
    """
    loan = loan_usd(params)
    outlay = outlay_usd(params)
    rows: list[Row] = []

    for entry in table:
        year = entry["year"]
        k = bracket_rate(params.rate_brackets, year)
        z = loan * k / 100.0                                   # 當年利息
        # Cumulative interest over CALENDAR years 1..year-1 — the benefit
        # table may skip years (e.g. 11-14), but interest accrues every year.
        cumulative = sum(loan * bracket_rate(params.rate_brackets, y) / 100.0
                         for y in range(1, year))
        surrender = (entry["guaranteed"]
                     + (entry["reversionary"] + entry["special"])
                     * params.achievement_percent / 100.0)
        gross = surrender - loan
        net = gross + outlay - cumulative - z
        yearly = [loan * bracket_rate(params.rate_brackets, y) / 100.0
                  for y in range(1, year + 1)]
        cashflows = [outlay] + [-v for v in yearly[:-1]] + [gross - yearly[-1]]
        rows.append(Row(year=year, interest=z, surrender=surrender,
                          gross=gross, net=net, irr=solve_irr(cashflows),
                          cashflows=cashflows))
    return rows


# -------------------------------------------------------------- stress matrix

@dataclass
class StressCell:
    rate: float
    achievement: float
    irr: Optional[float]


@dataclass
class StressMatrix:
    rate_columns: list[float]        # sorted; current rate inserted if absent
    achievement_rows: list[float]    # as passed (caller sorts)
    rows: list[list[StressCell]]     # rows[i][j] = achievement i, rate j


def stress_matrix(params, table: list[dict], rates: list[float],
                  ratios: list[float], stress_year: int) -> StressMatrix:
    """Rate x achievement matrix of IRRs at the stress year.

    Each cell shifts the WHOLE bracket table by (cell rate - current rate)
    ("same magnitude for the whole term") and scales non-guaranteed bonuses
    by the achievement ratio, then reruns the engine.
    """
    current = bracket_rate(params.rate_brackets, stress_year)

    cols = sorted(set(rates) | {current})

    rows: list[list[StressCell]] = []
    for ratio in ratios:
        row: list[StressCell] = []
        for rate in cols:
            shifted = [{"end_year": b["end_year"], "rate": b["rate"] + (rate - current)}
                       for b in params.rate_brackets]
            p = replace(params, rate_brackets=shifted, achievement_percent=ratio)
            year_row = next((r for r in project(p, table) if r.year == stress_year), None)
            row.append(StressCell(rate=rate, achievement=ratio,
                                  irr=year_row.irr if year_row else None))
        rows.append(row)

    return StressMatrix(rate_columns=cols, achievement_rows=list(ratios), rows=rows)
