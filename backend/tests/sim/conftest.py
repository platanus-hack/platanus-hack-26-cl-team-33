import pytest

from bedflow.contracts import SimulationConfig
from sim_helpers import make_config


@pytest.fixture
def base_config() -> SimulationConfig:
    return make_config()
