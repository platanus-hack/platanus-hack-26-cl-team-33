"""Fail when frontend/src/types/api.ts drifts from the Pydantic contract."""
import re
from pathlib import Path

import pytest

from bedflow import contracts

TS = Path(__file__).resolve().parents[3] / "frontend" / "src" / "types" / "api.ts"

MODELS = [
    "SimulationConfig", "SimulateRequest", "SimulationMetrics", "TimelineSnapshot",
    "PatientMilestone", "PatientExample", "SimulationResult", "ScenarioVariant",
    "CompareRequest", "MetricStats", "CompareSummary", "CompareScenarioResult",
    "CompareResponse",
]


def _ts_fields(source: str, name: str) -> set[str]:
    # interfaces in api.ts contain no nested braces
    match = re.search(rf"export interface {name} \{{([^}}]*)\}}", source)
    assert match, f"interface {name} missing in api.ts"
    return set(re.findall(r"(\w+)\??\s*:", match.group(1)))


@pytest.mark.parametrize("name", MODELS)
def test_ts_interface_matches_pydantic_fields(name):
    fields = set(getattr(contracts, name).model_fields)
    assert _ts_fields(TS.read_text(encoding="utf-8"), name) == fields


def test_milestone_types_match():
    from typing import get_args
    source = TS.read_text(encoding="utf-8")
    block = re.search(r"export type MilestoneType =(.*?);", source, re.S).group(1)
    assert set(re.findall(r"'(\w+)'", block)) == set(get_args(contracts.MilestoneType))
