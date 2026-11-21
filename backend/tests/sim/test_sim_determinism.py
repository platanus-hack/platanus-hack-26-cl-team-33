"""Same (config, seed) -> identical JSON; seeds are independent."""
from bedflow.contracts import SimulationResult
from bedflow.sim import simulate


def test_same_seed_same_json(base_config):
    assert simulate(base_config, 7).model_dump_json() == simulate(base_config, 7).model_dump_json()


def test_different_seed_differs(base_config):
    assert simulate(base_config, 7).model_dump_json() != simulate(base_config, 8).model_dump_json()


def test_json_round_trip(base_config):
    result = simulate(base_config, 11)
    assert SimulationResult.model_validate_json(result.model_dump_json()) == result
