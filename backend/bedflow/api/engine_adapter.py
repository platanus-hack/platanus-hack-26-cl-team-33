"""Selects between the real SimPy engine and the explicitly-marked fixture stub.

BEDFLOW_MODE:
  auto (default) - real engine if ``bedflow.sim.engine`` imports, else stub
  real           - real engine, fail at startup if unavailable
  stub           - fixture responses only (UI integration; NOT real analysis)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from bedflow.contracts import CompareResponse, SimulationConfig, SimulationResult
from bedflow.experiments.compare import SimulateFn

MODE_REAL = "real-engine"
MODE_STUB = "stub-fixture-not-real"

FIXTURES = next(
    (p / "fixtures" for p in Path(__file__).resolve().parents
     if (p / "fixtures" / "simulate_response.json").exists()),
    Path.cwd() / "fixtures",
)


@dataclass(frozen=True)
class Engine:
    mode: str
    simulate: SimulateFn

    @property
    def is_real(self) -> bool:
        return self.mode == MODE_REAL


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def stub_simulate(config: SimulationConfig, seed: int) -> SimulationResult:
    """Fixture payload ignoring inputs; only for UI contract integration."""
    return SimulationResult.model_validate(_fixture("simulate_response.json")).model_copy(
        update={"seed": seed}
    )


def stub_compare() -> CompareResponse:
    return CompareResponse.model_validate(_fixture("compare_response.json"))


def load_engine(mode: str | None = None) -> Engine:
    mode = (mode or os.getenv("BEDFLOW_MODE", "auto")).lower()
    if mode not in {"auto", "real", "stub"}:
        raise ValueError(f"BEDFLOW_MODE must be auto|real|stub, got {mode!r}")
    if mode != "stub":
        try:
            from bedflow.sim.engine import simulate
        except ImportError:
            if mode == "real":
                raise
        else:
            return Engine(MODE_REAL, simulate)
    return Engine(MODE_STUB, stub_simulate)
