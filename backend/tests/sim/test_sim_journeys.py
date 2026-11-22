"""Per-patient milestone ordering and the selected example journeys."""
import pytest

from bedflow.sim import simulate
from bedflow.sim.journeys import milestones
from sim_helpers import SCENARIOS, make_config, traced_run

DISCHARGED = ["ED_ARRIVAL", "ED_BAY_ENTER", "PHYSICIAN_START", "PHYSICIAN_END", "ED_DISCHARGED"]
ADMITTED = ["ED_ARRIVAL", "ED_BAY_ENTER", "PHYSICIAN_START", "PHYSICIAN_END",
            "ADMISSION_INDICATED", "WARD_ADMITTED", "WARD_DISCHARGED", "BED_READY"]


def _valid_sequence(types: list[str]) -> bool:
    return types == DISCHARGED[: len(types)] or types == ADMITTED[: len(types)]


@pytest.mark.parametrize("seed", [41, 42])
def test_all_patient_milestones_monotone_and_ordered(seed):
    run = traced_run(make_config(), seed)
    for p in run.patients:
        ms = milestones(p)
        types = [m.type for m in ms]
        assert _valid_sequence(types), (p.patient_id, types)
        times = [m.minute for m in ms]
        assert times == sorted(times), p.patient_id
        if p.admit and p.physician_end is not None:
            assert p.indicated == p.physician_end
        if p.admission_wait is not None:
            assert p.admission_wait >= 0


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_patient_examples(scenario):
    config = make_config(**SCENARIOS[scenario])
    result = simulate(config, 42)
    examples = result.patient_examples
    assert 5 <= len(examples) <= 10
    ids = [e.patient_id for e in examples]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    kinds = set()
    for e in examples:
        types = [m.type for m in e.milestones]
        assert _valid_sequence(types)
        by_type = {m.type: m.minute for m in e.milestones}
        if "WARD_ADMITTED" in by_type:
            assert e.admission_wait_min == pytest.approx(
                by_type["WARD_ADMITTED"] - by_type["ADMISSION_INDICATED"])
            kinds.add("admitted")
        else:
            assert e.admission_wait_min is None
        if "ED_DISCHARGED" in by_type:
            kinds.add("discharged")
    assert kinds == {"admitted", "discharged"}


def test_examples_fill_up_when_few_outcomes():
    result = simulate(make_config(admission_probability=0.0, measurement_h=24), 5)
    assert 5 <= len(result.patient_examples) <= 10
    assert all(e.admission_wait_min is None for e in result.patient_examples)
