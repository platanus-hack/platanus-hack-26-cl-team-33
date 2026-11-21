"""BedFlow Chile v1.0 frozen cross-team schemas.

Owner: Person C. All edits require three-person agreement and fixture/TS updates.
Python 3.12 / Pydantic v2.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SimulationConfig(StrictModel):
    arrival_rate_per_hour: float = Field(gt=0)
    physicians: int = Field(ge=1)
    ed_spaces: int = Field(ge=1)
    ward_beds: int = Field(ge=1)
    initial_ward_occupied: int = Field(ge=0)
    admission_probability: float = Field(ge=0, le=1)
    mean_physician_service_min: float = Field(gt=0)
    mean_inpatient_los_h: float = Field(gt=0)
    bed_turnover_min: float = Field(ge=0)
    warmup_h: int = Field(ge=0)
    measurement_h: int = Field(ge=1)
    followup_h: int = Field(ge=12)
    snapshot_every_min: int = Field(ge=1)

    @model_validator(mode="after")
    def check_initial_occupancy(self):
        if self.initial_ward_occupied > self.ward_beds:
            raise ValueError("initial_ward_occupied must not exceed ward_beds")
        return self


class SimulateRequest(StrictModel):
    scenario_id: str = Field(min_length=1)
    seed: int = Field(ge=0)
    config: SimulationConfig


class SimulationMetrics(StrictModel):
    eligible_admissions: int = Field(ge=0)
    admitted_within_12h_count: int = Field(ge=0)
    admitted_within_12h_pct: float | None = Field(default=None, ge=0, le=100)
    mean_wait_to_bed_capped_12h_min: float | None = Field(default=None, ge=0, le=720)
    p90_wait_to_bed_capped_12h_min: float | None = Field(default=None, ge=0, le=720)
    avg_ed_bay_utilization_pct: float = Field(ge=0, le=100)
    avg_ward_occupancy_pct: float = Field(ge=0, le=100)
    max_ed_boarding: int = Field(ge=0)
    ed_arrivals_measured: int = Field(ge=0)

    @model_validator(mode="after")
    def check_denominator(self):
        if self.admitted_within_12h_count > self.eligible_admissions:
            raise ValueError("success count cannot exceed eligible indications")
        if self.eligible_admissions == 0 and self.admitted_within_12h_pct is not None:
            raise ValueError("admission percentage must be null when denominator is zero")
        if self.eligible_admissions > 0 and self.admitted_within_12h_pct is None:
            raise ValueError("admission percentage required when denominator is positive")
        return self


class TimelineSnapshot(StrictModel):
    minute: float = Field(ge=0)
    ed_waiting: int = Field(ge=0)
    ed_treatment: int = Field(ge=0)
    ed_boarding: int = Field(ge=0)
    ward_occupied: int = Field(ge=0)
    ward_turnover: int = Field(ge=0)
    ward_ready: int = Field(ge=0)


MilestoneType = Literal[
    "ED_ARRIVAL", "ED_BAY_ENTER", "PHYSICIAN_START", "PHYSICIAN_END",
    "ADMISSION_INDICATED", "WARD_ADMITTED", "ED_DISCHARGED",
    "WARD_DISCHARGED", "BED_READY",
]


class PatientMilestone(StrictModel):
    minute: float = Field(ge=0)
    type: MilestoneType


class PatientExample(StrictModel):
    patient_id: int = Field(ge=0)
    admission_wait_min: float | None = Field(default=None, ge=0)
    milestones: list[PatientMilestone]


class SimulationResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    scenario_id: str
    seed: int = Field(ge=0)
    metrics: SimulationMetrics
    timeline: list[TimelineSnapshot]
    patient_examples: list[PatientExample]


class ScenarioVariant(StrictModel):
    scenario_id: Literal["baseline", "more_physicians", "faster_turnover", "more_ward_beds"]
    label: str = Field(min_length=1)
    overrides: dict[str, int | float]

    @model_validator(mode="after")
    def valid_overrides(self):
        expected = {
            "baseline": {},
            "more_physicians": {"physicians": 6},
            "faster_turnover": {"bed_turnover_min": 30.0},
            "more_ward_beds": {"ward_beds": 28},
        }
        if self.overrides != expected[self.scenario_id]:
            raise ValueError(f"{self.scenario_id} must use overrides {expected[self.scenario_id]}")
        return self


class CompareRequest(StrictModel):
    base_config: SimulationConfig
    seeds: list[int] = Field(min_length=2, max_length=40)
    scenarios: list[ScenarioVariant] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def check_comparison(self):
        if len(set(self.seeds)) != len(self.seeds) or any(s < 0 for s in self.seeds):
            raise ValueError("seeds must be unique nonnegative integers")
        if set(s.scenario_id for s in self.scenarios) != {
            "baseline", "more_physicians", "faster_turnover", "more_ward_beds"
        }:
            raise ValueError("all four canonical scenarios are required")
        return self


class MetricStats(StrictModel):
    mean: float
    ci95_low: float
    ci95_high: float


class CompareSummary(StrictModel):
    admitted_within_12h_pct: MetricStats
    mean_wait_to_bed_capped_12h_min: MetricStats
    avg_ed_bay_utilization_pct: MetricStats


class CompareScenarioResult(StrictModel):
    scenario_id: str
    label: str
    summary: CompareSummary
    paired_delta_12h_pp: MetricStats | None


class CompareResponse(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    seeds: list[int]
    results: list[CompareScenarioResult]
