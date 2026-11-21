"""Deterministic selection of 5-10 illustrative synthetic patient journeys."""
from __future__ import annotations

from bedflow.contracts import PatientExample, PatientMilestone
from bedflow.sim.metrics import TARGET_WINDOW_MIN
from bedflow.sim.model import ModelRun, PatientRecord

MIN_EXAMPLES = 5
MAX_EXAMPLES = 10


def milestones(rec: PatientRecord) -> list[PatientMilestone]:
    steps = [
        (rec.arrival, "ED_ARRIVAL"),
        (rec.bay_enter, "ED_BAY_ENTER"),
        (rec.physician_start, "PHYSICIAN_START"),
        (rec.physician_end, "PHYSICIAN_END"),
    ]
    if rec.admit:
        steps += [
            (rec.indicated, "ADMISSION_INDICATED"),
            (rec.ward_admitted, "WARD_ADMITTED"),
            (rec.ward_discharged, "WARD_DISCHARGED"),
            (rec.bed_ready, "BED_READY"),
        ]
    else:
        steps.append((rec.ed_discharged, "ED_DISCHARGED"))
    return [PatientMilestone(minute=float(t), type=kind) for t, kind in steps if t is not None]


def to_example(rec: PatientRecord) -> PatientExample:
    wait = rec.admission_wait
    return PatientExample(
        patient_id=rec.patient_id,
        admission_wait_min=None if wait is None else float(wait),
        milestones=milestones(rec),
    )


def _pick_min(items, key):
    return min(items, key=lambda p: (key(p), p.patient_id), default=None)


def _pick_max(items, key):
    return min(items, key=lambda p: (-key(p), p.patient_id), default=None)


def select_patient_examples(run: ModelRun) -> list[PatientExample]:
    w0, w1 = run.window
    candidates = [p for p in run.patients if w0 <= p.arrival < w1]
    admitted = [p for p in candidates if p.admission_wait is not None]
    discharged = [p for p in candidates if p.ed_discharged is not None]
    failures = [
        p for p in candidates
        if p.indicated is not None
        and (p.admission_wait is None or p.admission_wait > TARGET_WINDOW_MIN)
    ]
    full_ward_stay = [p for p in admitted if p.bed_ready is not None]
    by_wait = sorted(admitted, key=lambda p: (p.admission_wait, p.patient_id))

    picks = [
        _pick_min(admitted, lambda p: p.admission_wait),  # fastest admission
        by_wait[len(by_wait) // 2] if by_wait else None,  # median admission
        _pick_max(admitted, lambda p: p.admission_wait),  # longest admitted boarder
        failures[0] if failures else None,  # missed the 12h target
        _pick_min(discharged, lambda p: p.ed_discharged - p.arrival),  # quick ED discharge
        _pick_max(discharged, lambda p: p.bay_enter - p.arrival),  # longest wait for a bay
        full_ward_stay[0] if full_ward_stay else None,  # complete ward stay incl. turnover
    ]

    chosen: dict[int, PatientRecord] = {}
    for p in picks:
        if p is not None and p.patient_id not in chosen:
            chosen[p.patient_id] = p
    for pool in (candidates, run.patients):
        for p in pool:
            if len(chosen) >= MIN_EXAMPLES:
                break
            chosen.setdefault(p.patient_id, p)

    ordered = sorted(chosen.values(), key=lambda p: p.patient_id)[:MAX_EXAMPLES]
    return [to_example(p) for p in ordered]
