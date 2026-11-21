"""TEMPORARY fixture-only API for H1–H8 integration.

DO NOT deploy this as real analysis. C replaces its behavior with real engine
calls by H12. All responses disclose fixture mode through an HTTP header.

Run from a repo where `fixtures/` exists at root:
  uvicorn bedflow.api.mock_api:app --reload --app-dir backend
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from bedflow.contracts import (
    CompareRequest,
    CompareResponse,
    SimulateRequest,
    SimulationResult,
)

app = FastAPI(title="BedFlow Chile API — MOCK FIXTURES ONLY", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
FIXTURES = next(
    (parent / "fixtures" for parent in Path(__file__).resolve().parents
     if (parent / "fixtures" / "simulate_response.json").exists()),
    Path.cwd() / "fixtures",
)


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@app.post("/api/v1/simulate", response_model=SimulationResult)
def simulate_mock(request: SimulateRequest, response: Response) -> SimulationResult:
    response.headers["X-BedFlow-Mode"] = "mock-fixture-not-real"
    # Intentionally not dependent on inputs: this is a UI contract stub only.
    # The UI MUST show mock mode. Replace endpoint logic with the real engine.
    item = SimulationResult.model_validate(fixture("simulate_response.json"))
    return item.model_copy(update={"scenario_id": request.scenario_id, "seed": request.seed})


@app.post("/api/v1/compare", response_model=CompareResponse)
def compare_mock(request: CompareRequest, response: Response) -> CompareResponse:
    response.headers["X-BedFlow-Mode"] = "mock-fixture-not-real"
    return CompareResponse.model_validate(fixture("compare_response.json"))


@app.get("/health")
def health():
    return {"ok": True, "mode": "mock-fixture-not-real"}
