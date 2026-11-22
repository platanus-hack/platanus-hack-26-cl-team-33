import pytest

from dcsim.montecarlo import run_ensemble
from dcsim.policy import SCENARIOS


@pytest.fixture(scope="session")
def ensembles():
    """Ensembles anclados de todos los escenarios (cacheados en disco)."""
    return {sid: run_ensemble(s["policy"], n=200) for sid, s in SCENARIOS.items()}
