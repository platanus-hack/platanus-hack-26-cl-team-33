"""BedFlow Chile HTTP API (Person C).

Run: uvicorn bedflow.api.app:app --app-dir backend --reload
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bedflow.api.engine_adapter import Engine, load_engine, stub_compare
from bedflow.contracts import (
    CompareRequest,
    CompareResponse,
    SimulateRequest,
    SimulationResult,
)
from bedflow.experiments.compare import ExperimentError, compare

log = logging.getLogger("bedflow.api")

MODE_HEADER = "X-BedFlow-Mode"


def create_app(engine: Engine | None = None) -> FastAPI:
    engine = engine or load_engine()
    app = FastAPI(title="BedFlow Chile API", version="1.0")

    origins = os.getenv("BEDFLOW_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins.split(",") if o.strip()],
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
        expose_headers=[MODE_HEADER],
    )

    @app.exception_handler(ExperimentError)
    async def experiment_error(_: Request, exc: ExperimentError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
            headers={MODE_HEADER: engine.mode},
        )

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Simulation failed. See server logs."},
            headers={MODE_HEADER: engine.mode},
        )

    @app.post("/api/v1/simulate", response_model=SimulationResult)
    def simulate_endpoint(request: SimulateRequest, response: Response) -> SimulationResult:
        response.headers[MODE_HEADER] = engine.mode
        result = engine.simulate(request.config, request.seed)
        return result.model_copy(update={"scenario_id": request.scenario_id})

    @app.post("/api/v1/compare", response_model=CompareResponse)
    def compare_endpoint(request: CompareRequest, response: Response) -> CompareResponse:
        response.headers[MODE_HEADER] = engine.mode
        if not engine.is_real:
            return stub_compare()  # fixture only; header discloses stub mode
        return compare(request.base_config, request.scenarios, request.seeds, engine.simulate)

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "mode": engine.mode}

    return app


app = create_app()
