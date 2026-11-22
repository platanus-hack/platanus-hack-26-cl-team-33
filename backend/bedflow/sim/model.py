"""SimPy patient-flow model: ED bays -> physician -> disposition -> ward bed.

Internal module. ``run_model`` returns raw per-patient records, per-bed stays,
sampled snapshots and exact window integrals; ``engine.simulate`` turns them
into the shared ``SimulationResult``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import simpy

from bedflow.contracts import SimulationConfig
from bedflow.sim.cohort import Cohort, horizon_min, measurement_window

COUNTERS = (
    "ed_waiting",
    "ed_treatment",
    "ed_boarding",
    "ward_occupied",
    "ward_turnover",
    "ward_ready",
    "physicians_busy",
)


class InvariantViolation(RuntimeError):
    """Resource conservation broke. Fail loudly instead of returning bad numbers."""


@dataclass(slots=True)
class PatientRecord:
    patient_id: int
    arrival: float
    admit: bool
    bay_enter: float | None = None
    physician_start: float | None = None
    physician_end: float | None = None
    indicated: float | None = None
    ed_discharged: float | None = None
    ward_admitted: float | None = None
    ward_discharged: float | None = None
    bed_ready: float | None = None
    bed_id: int | None = None

    @property
    def bay_exit(self) -> float | None:
        return self.ed_discharged if self.ed_discharged is not None else self.ward_admitted

    @property
    def admission_wait(self) -> float | None:
        if self.indicated is None or self.ward_admitted is None:
            return None
        return self.ward_admitted - self.indicated


@dataclass(slots=True)
class BedStay:
    """One occupancy of a ward bed: occupied -> turnover -> ready."""

    bed_id: int
    patient_id: int | None  # None = synthetic initial occupant
    start: float
    discharged: float | None = None
    ready: float | None = None


@dataclass
class ModelRun:
    config: SimulationConfig
    horizon: float
    window: tuple[float, float]
    patients: list[PatientRecord]
    bed_stays: list[BedStay]
    snapshots: list[tuple[float, dict[str, int]]]
    bay_area: float  # integral of (ed_treatment + ed_boarding) dt over the window
    ward_area: float  # integral of ward_occupied dt over the window
    max_boarding: int  # max ed_boarding held for a positive time inside the window
    trace: list[tuple[float, dict[str, int]]] | None = field(default=None)


class StateTracker:
    """Single place where counts change; checks invariants and integrates exactly."""

    def __init__(self, env: simpy.Environment, config: SimulationConfig,
                 window: tuple[float, float], trace: bool) -> None:
        self.env = env
        self.ed_spaces = config.ed_spaces
        self.physicians = config.physicians
        self.ward_beds = config.ward_beds
        self.w0, self.w1 = window
        self.counts = dict.fromkeys(COUNTERS, 0)
        self.counts["ward_occupied"] = config.initial_ward_occupied
        self.counts["ward_ready"] = config.ward_beds - config.initial_ward_occupied
        self._last = 0.0
        self.bay_area = 0.0
        self.ward_area = 0.0
        self.max_boarding = 0
        self.trace: list[tuple[float, dict[str, int]]] | None = [] if trace else None
        self._check()
        if self.trace is not None:
            self.trace.append((0.0, dict(self.counts)))

    def _accumulate(self, now: float) -> None:
        lo, hi = max(self._last, self.w0), min(now, self.w1)
        if hi > lo:
            c = self.counts
            dt = hi - lo
            self.bay_area += (c["ed_treatment"] + c["ed_boarding"]) * dt
            self.ward_area += c["ward_occupied"] * dt
            if c["ed_boarding"] > self.max_boarding:
                self.max_boarding = c["ed_boarding"]
        self._last = now

    def change(self, **deltas: int) -> None:
        now = self.env.now
        self._accumulate(now)
        for name, delta in deltas.items():
            self.counts[name] += delta
        self._check()
        if self.trace is not None:
            self.trace.append((now, dict(self.counts)))

    def finish(self, end: float) -> None:
        self._accumulate(end)

    def _check(self) -> None:
        c = self.counts
        if any(v < 0 for v in c.values()):
            raise InvariantViolation(f"negative count at t={self.env.now}: {c}")
        if c["ed_treatment"] + c["ed_boarding"] > self.ed_spaces:
            raise InvariantViolation(f"ED bays over capacity at t={self.env.now}: {c}")
        if c["physicians_busy"] > self.physicians:
            raise InvariantViolation(f"physicians over capacity at t={self.env.now}: {c}")
        if c["ward_occupied"] + c["ward_turnover"] + c["ward_ready"] != self.ward_beds:
            raise InvariantViolation(f"ward beds not conserved at t={self.env.now}: {c}")


class HospitalModel:
    def __init__(self, config: SimulationConfig, cohort: Cohort, trace: bool = False) -> None:
        self.config = config
        self.cohort = cohort
        self.env = simpy.Environment()
        self.window = measurement_window(config)
        self.horizon = horizon_min(config)
        self.tracker = StateTracker(self.env, config, self.window, trace)

        self.bays = simpy.Resource(self.env, capacity=config.ed_spaces)
        self.docs = simpy.Resource(self.env, capacity=config.physicians)
        # Store holds only READY beds; getters are served FIFO.
        self.ready_beds = simpy.Store(self.env, capacity=config.ward_beds)
        self.ready_beds.items.extend(range(config.initial_ward_occupied, config.ward_beds))

        self.patients: list[PatientRecord] = []
        self.bed_stays: list[BedStay] = []
        self.snapshots: list[tuple[float, dict[str, int]]] = []

    def run(self) -> ModelRun:
        env = self.env
        env.process(self._snapshot_process())
        for bed_id, residual in enumerate(self.cohort.initial_residual_min):
            stay = BedStay(bed_id=bed_id, patient_id=None, start=0.0)
            self.bed_stays.append(stay)
            env.process(self._bed_cycle(stay, float(residual), None))
        c = self.cohort
        for i in range(c.n_patients):
            rec = PatientRecord(
                patient_id=i, arrival=float(c.arrival_min[i]), admit=bool(c.admit[i])
            )
            self.patients.append(rec)
            env.process(self._patient(rec, float(c.service_min[i]), float(c.los_min[i])))

        env.run(until=self.horizon)
        self.tracker.finish(self.horizon)
        return ModelRun(
            config=self.config,
            horizon=self.horizon,
            window=self.window,
            patients=self.patients,
            bed_stays=self.bed_stays,
            snapshots=self.snapshots,
            bay_area=self.tracker.bay_area,
            ward_area=self.tracker.ward_area,
            max_boarding=self.tracker.max_boarding,
            trace=self.tracker.trace,
        )

    def _patient(self, rec: PatientRecord, service_min: float, los_min: float):
        env, track = self.env, self.tracker.change
        yield env.timeout(rec.arrival)  # scheduled from t=0 so env.now == arrival exactly
        track(ed_waiting=+1)

        bay = self.bays.request()
        yield bay
        rec.bay_enter = env.now
        track(ed_waiting=-1, ed_treatment=+1)

        doc = self.docs.request()
        yield doc
        rec.physician_start = env.now
        track(physicians_busy=+1)
        yield env.timeout(service_min)
        self.docs.release(doc)
        rec.physician_end = env.now

        if not rec.admit:
            self.bays.release(bay)
            rec.ed_discharged = env.now
            track(physicians_busy=-1, ed_treatment=-1)
            return

        # Boarding: physician is free, ED bay stays held until a ward bed is ready.
        rec.indicated = env.now
        track(physicians_busy=-1, ed_treatment=-1, ed_boarding=+1)
        bed_id = yield self.ready_beds.get()
        self.bays.release(bay)
        rec.ward_admitted = env.now
        rec.bed_id = bed_id
        track(ed_boarding=-1, ward_ready=-1, ward_occupied=+1)
        stay = BedStay(bed_id=bed_id, patient_id=rec.patient_id, start=env.now)
        self.bed_stays.append(stay)
        env.process(self._bed_cycle(stay, los_min, rec))

    def _bed_cycle(self, stay: BedStay, stay_min: float, rec: PatientRecord | None):
        env, track = self.env, self.tracker.change
        yield env.timeout(stay_min)
        stay.discharged = env.now
        if rec is not None:
            rec.ward_discharged = env.now
        track(ward_occupied=-1, ward_turnover=+1)

        yield env.timeout(self.config.bed_turnover_min)
        stay.ready = env.now
        if rec is not None:
            rec.bed_ready = env.now
        track(ward_turnover=-1, ward_ready=+1)
        yield self.ready_beds.put(stay.bed_id)

    def _snapshot_process(self):
        env = self.env
        w0, w1 = self.window
        step = float(self.config.snapshot_every_min)
        k = 0
        while (minute := w0 + k * step) < w1:
            if minute > env.now:
                yield env.timeout(minute - env.now)
            self.snapshots.append((minute, dict(self.tracker.counts)))
            k += 1


def run_model(config: SimulationConfig, cohort: Cohort, trace: bool = False) -> ModelRun:
    return HospitalModel(config, cohort, trace=trace).run()
