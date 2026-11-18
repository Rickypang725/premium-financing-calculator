"""API-layer tests (M1). Engine-layer correctness is covered by test_engine.py;
here we verify the HTTP boundary: endpoint behaviour, validation → 422,
and the compliance disclaimer contract."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pfpro.api import app

VECTORS = json.loads((Path(__file__).parent / "vectors.json").read_text())
BASE = VECTORS["base_params"]
EXP = VECTORS["expected"]

client = TestClient(app)


def _payload(**overrides) -> dict:
    payload = {**BASE, "benefit_table": VECTORS["benefit_table"]}
    payload.update(overrides)
    return payload


# ------------------------------------------------------------------ endpoints

def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_projection_matches_golden_kpis():
    r = client.post("/projection", json=_payload())
    assert r.status_code == 200
    body = r.json()
    rows = {row["year"]: row for row in body["projection"]}
    assert len(body["projection"]) == len(VECTORS["benefit_table"])
    # KPIs derived from the projection rows (contract: API cannot change answers)
    y7 = rows[7]
    assert y7["surrender"] == pytest.approx(EXP["year7"]["surrender"], abs=1e-6)
    assert y7["net"] == pytest.approx(EXP["year7"]["net"], abs=1e-6)
    assert y7["irr"] == pytest.approx(EXP["year7"]["irr"], abs=1e-6)


def test_every_response_carries_disclaimer():
    for endpoint in ["/projection"]:
        r = client.post(endpoint, json=_payload())
        assert r.status_code == 200
        assert "not indicative of future performance" in r.json()["disclaimer"]
    r = client.post("/stress", json=_payload(rates=[2.0, 4.11], ratios=[100],
                                             stress_year=20))
    assert r.status_code == 200
    assert "not indicative of future performance" in r.json()["disclaimer"]


def test_stress_endpoint_shape_and_golden_cell():
    r = client.post("/stress", json=_payload(rates=[2.0, 4.11], ratios=[100, 60],
                                             stress_year=20))
    assert r.status_code == 200
    m = r.json()["matrix"]
    assert m["rate_columns"] == sorted({2.0, 4.11})
    assert m["achievement_rows"] == [100, 60]
    assert len(m["rows"]) == 2 and all(len(row) == 2 for row in m["rows"])
    i = m["achievement_rows"].index(60)
    j = m["rate_columns"].index(4.11)
    assert m["rows"][i][j]["irr"] * 100 == pytest.approx(1.35, abs=0.005)


def test_openapi_docs_available():
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    assert "/projection" in spec["paths"] and "/stress" in spec["paths"]


# ------------------------------------------------------------------ 422 guard

@pytest.mark.parametrize("override", [
    {"total_premium": -1},                 # negative premium
    {"ltv_percent": 105},                  # LTV out of range — business rule
    {"bank_fx": 0},                        # zero FX rate
    {"benefit_table": []},                 # empty table
    {"rate_brackets": []},                 # no rate brackets
])
def test_invalid_input_returns_422(override):
    r = client.post("/projection", json=_payload(**override))
    assert r.status_code == 422


def test_stress_year_outside_table_returns_422():
    r = client.post("/stress", json=_payload(rates=[4.11], ratios=[100],
                                             stress_year=13))  # 13 not in table
    assert r.status_code == 422
