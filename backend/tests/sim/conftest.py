import pytest
from sim_helpers import make_config

from bedflow.contracts import SimulationConfig


@pytest.fixture
def base_config() -> SimulationConfig:
    return make_config()
