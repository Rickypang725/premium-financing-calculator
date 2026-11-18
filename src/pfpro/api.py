"""REST API layer over the pfpro engine (M1).

Thin wrapper: all calculation lives in engine.py (ADR-1). This module
only validates input (Pydantic → 422 on violation), calls the engine,
and serialises results with the compliance disclaimer attached.
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field, model_validator

from .engine import ProjectionParams, Row, StressMatrix, project, stress_matrix

DISCLAIMER = (
    "Illustrative figures. Returns exclude bank fees and retained-asset "
    "opportunity costs. FX rates are assumptions. Past fulfilment ratios "
    "are not indicative of future performance. Final loan terms subject "
    "to bank confirmation."
)

app = FastAPI(title="Premium Financing Calculator", version="0.1.0")


# ------------------------------------------------------------------- models

class RateBracket(BaseModel):
    end_year: int = Field(ge=0)          # 0 = open segment
    rate: float = Field(ge=0)


class BenefitEntry(BaseModel):
    year: int = Field(ge=1)
    guaranteed: float = Field(ge=0)
    reversionary: float = Field(ge=0)
    special: float = Field(ge=0)


class ProjectionRequest(BaseModel):
    total_premium: float = Field(gt=0)
    discount_percent: float = Field(ge=0, le=100)
    surrender0_percent: float = Field(ge=0, le=100)
    ltv_percent: float = Field(gt=0, le=100)
    bank_fx: float = Field(gt=0)
    fwd_fx: float = Field(gt=0)
    rate_brackets: list[RateBracket] = Field(min_length=1)
    achievement_percent: float = Field(ge=0, le=100)
    benefit_table: list[BenefitEntry] = Field(min_length=1)


class StressRequest(ProjectionRequest):
    rates: list[float] = Field(min_length=1)
    ratios: list[float] = Field(min_length=1)
    stress_year: int = Field(ge=1)

    @model_validator(mode="after")
    def stress_year_in_table(self):
        if self.stress_year not in {e.year for e in self.benefit_table}:
            raise ValueError("stress_year must exist in benefit_table")
        return self


# --------------------------------------------------------------- serialisers

def _row_dict(r: Row) -> dict:
    return {"year": r.year, "interest": r.interest, "surrender": r.surrender,
            "gross": r.gross, "net": r.net, "irr": r.irr,
            "cashflows": r.cashflows}


def _matrix_dict(m: StressMatrix) -> dict:
    return {"rate_columns": m.rate_columns, "achievement_rows": m.achievement_rows,
            "rows": [[{"rate": c.rate, "achievement": c.achievement, "irr": c.irr}
                      for c in row] for row in m.rows]}


def _to_params(req: ProjectionRequest) -> ProjectionParams:
    return ProjectionParams(
        total_premium=req.total_premium,
        discount_percent=req.discount_percent,
        surrender0_percent=req.surrender0_percent,
        ltv_percent=req.ltv_percent,
        bank_fx=req.bank_fx,
        fwd_fx=req.fwd_fx,
        rate_brackets=[b.model_dump() for b in req.rate_brackets],
        achievement_percent=req.achievement_percent,
    )


def _table(req: ProjectionRequest) -> list[dict]:
    return [e.model_dump() for e in req.benefit_table]


# ------------------------------------------------------------------ endpoints

@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/projection")
def projection(req: ProjectionRequest) -> dict:
    rows = project(_to_params(req), _table(req))
    return {"disclaimer": DISCLAIMER, "projection": [_row_dict(r) for r in rows]}


@app.post("/stress")
def stress(req: StressRequest) -> dict:
    m = stress_matrix(_to_params(req), _table(req),
                      req.rates, req.ratios, req.stress_year)
    return {"disclaimer": DISCLAIMER, "matrix": _matrix_dict(m)}
