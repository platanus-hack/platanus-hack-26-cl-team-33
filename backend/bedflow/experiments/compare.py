"""Paired multi-seed scenario comparison (Person C).

For each (scenario, seed) the engine's ``simulate(config, seed)`` is called once.
Per-seed metrics are aggregated into ``MetricStats`` using an *approximate* 95%
confidence interval: mean +/- 1.96 * s / sqrt(n), with s the sample standard
deviation (ddof=1). The interval is a normal approximation; it is only
indicative for small n (use n >= 5).

Null handling: a seed whose metric is ``None`` (no eligible admissions) is
dropped for that metric. Paired deltas use only seeds where both the baseline
and the variant are non-null. With a single valid seed the interval collapses
to the mean; with zero valid seeds an ``ExperimentError`` is raised.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence

from pydantic import ValidationError

from bedflow.contracts import (
    CompareResponse,
    CompareScenarioResult,
    CompareSummary,
    MetricStats,
    ScenarioVariant,
    SimulationConfig,
    SimulationResult,
)

SimulateFn = Callable[[SimulationConfig, int], SimulationResult]

# Flat config fields a scenario is allowed to override.
ALLOWED_OVERRIDES = frozenset({"physicians", "bed_turnover_min", "ward_beds"})
Z95 = 1.96


class ExperimentError(ValueError):
    """Invalid experiment definition or unusable results (maps to HTTP 422)."""


def apply_overrides(
    config: SimulationConfig, overrides: Mapping[str, int | float]
) -> SimulationConfig:
    """Return a new validated config with whitelisted flat overrides applied."""
    unknown = set(overrides) - ALLOWED_OVERRIDES
    if unknown:
        raise ExperimentError(f"overrides not allowed: {sorted(unknown)}")
    for key, value in overrides.items():
        if isinstance(value, bool) or not math.isfinite(value):
            raise ExperimentError(f"override {key} must be a finite number")
    try:
        return SimulationConfig.model_validate({**config.model_dump(), **overrides})
    except ValidationError as exc:
        raise ExperimentError(f"invalid configuration after overrides: {exc}") from exc


def _stats(values: Sequence[float], name: str) -> MetricStats:
    if not values:
        raise ExperimentError(f"no valid seeds to compute {name}")
    if not all(math.isfinite(v) for v in values):
        raise ExperimentError(f"non-finite value in {name}")
    n = len(values)
    mean = math.fsum(values) / n
    if n < 2:
        return MetricStats(mean=mean, ci95_low=mean, ci95_high=mean)
    sd = math.sqrt(math.fsum((v - mean) ** 2 for v in values) / (n - 1))
    half = Z95 * sd / math.sqrt(n)
    return MetricStats(mean=mean, ci95_low=mean - half, ci95_high=mean + half)


def _default_simulate() -> SimulateFn:
    try:
        from bedflow.sim.engine import simulate
    except ImportError as exc:  # engine (Person A) not available yet
        raise ExperimentError("simulation engine is not available") from exc
    return simulate


def compare(
    base_config: SimulationConfig,
    scenarios: Sequence[ScenarioVariant],
    seeds: Sequence[int],
    simulate_fn: SimulateFn | None = None,
) -> CompareResponse:
    """Run every scenario on the same seeds and aggregate the 3 contract metrics."""
    if not seeds:
        raise ExperimentError("at least one seed is required")
    if len(set(seeds)) != len(seeds) or any(s < 0 for s in seeds):
        raise ExperimentError("seeds must be unique nonnegative integers")
    ids = [s.scenario_id for s in scenarios]
    if len(set(ids)) != len(ids):
        raise ExperimentError("duplicate scenario ids")
    if "baseline" not in ids:
        raise ExperimentError("baseline scenario is required")

    run = simulate_fn or _default_simulate()
    configs = {s.scenario_id: apply_overrides(base_config, s.overrides) for s in scenarios}

    # per scenario -> per seed -> metrics
    metrics: dict[str, list] = {
        sid: [run(cfg, seed).metrics for seed in seeds] for sid, cfg in configs.items()
    }
    baseline = metrics["baseline"]

    results = []
    for scenario in scenarios:
        ms = metrics[scenario.scenario_id]
        pct = [m.admitted_within_12h_pct for m in ms if m.admitted_within_12h_pct is not None]
        wait = [
            m.mean_wait_to_bed_capped_12h_min
            for m in ms
            if m.mean_wait_to_bed_capped_12h_min is not None
        ]
        util = [m.avg_ed_bay_utilization_pct for m in ms]
        summary = CompareSummary(
            admitted_within_12h_pct=_stats(pct, "admitted_within_12h_pct"),
            mean_wait_to_bed_capped_12h_min=_stats(wait, "mean_wait_to_bed_capped_12h_min"),
            avg_ed_bay_utilization_pct=_stats(util, "avg_ed_bay_utilization_pct"),
        )
        delta = None
        if scenario.scenario_id != "baseline":
            diffs = [
                v.admitted_within_12h_pct - b.admitted_within_12h_pct
                for v, b in zip(ms, baseline, strict=True)
                if v.admitted_within_12h_pct is not None
                and b.admitted_within_12h_pct is not None
            ]
            delta = _stats(diffs, "paired_delta_12h_pp")
        results.append(
            CompareScenarioResult(
                scenario_id=scenario.scenario_id,
                label=scenario.label,
                summary=summary,
                paired_delta_12h_pp=delta,
            )
        )
    return CompareResponse(seeds=list(seeds), results=results)
