"""Per-run metrics exactly as defined in spec/CONTRACTS.md.

Occupancy, bay utilization and max boarding are exact event-time integrals over
the measurement window ``[warmup_end, measurement_end)``, not 15-minute samples.
"""
from __future__ import annotations

import numpy as np

from bedflow.contracts import SimulationMetrics
from bedflow.sim.model import ModelRun

TARGET_WINDOW_MIN = 720.0


def _pct(value: float) -> float:
    return float(min(100.0, max(0.0, value)))


def compute_metrics(run: ModelRun) -> SimulationMetrics:
    cfg = run.config
    w0, w1 = run.window
    duration = w1 - w0

    eligible = [p for p in run.patients if p.indicated is not None and w0 <= p.indicated < w1]
    capped: list[float] = []
    success = 0
    for p in eligible:
        wait = p.admission_wait
        if wait is None:
            # Unresolved at the horizon. Follow-up >= 12h guarantees a full window.
            if run.horizon - p.indicated < TARGET_WINDOW_MIN:
                raise RuntimeError("eligible indication without a full 720-minute window")
            capped.append(TARGET_WINDOW_MIN)
            continue
        if wait <= TARGET_WINDOW_MIN:
            success += 1
        capped.append(min(wait, TARGET_WINDOW_MIN))

    n = len(eligible)
    if n:
        pct = _pct(100.0 * success / n)
        mean_wait = float(min(TARGET_WINDOW_MIN, np.mean(capped)))
        p90_wait = float(min(TARGET_WINDOW_MIN, np.percentile(capped, 90)))
    else:
        pct = mean_wait = p90_wait = None

    return SimulationMetrics(
        eligible_admissions=n,
        admitted_within_12h_count=success,
        admitted_within_12h_pct=pct,
        mean_wait_to_bed_capped_12h_min=mean_wait,
        p90_wait_to_bed_capped_12h_min=p90_wait,
        avg_ed_bay_utilization_pct=_pct(100.0 * run.bay_area / (cfg.ed_spaces * duration)),
        avg_ward_occupancy_pct=_pct(100.0 * run.ward_area / (cfg.ward_beds * duration)),
        max_ed_boarding=int(run.max_boarding),
        ed_arrivals_measured=sum(1 for p in run.patients if w0 <= p.arrival < w1),
    )
