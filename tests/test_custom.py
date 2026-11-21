"""«Tu regla» se compara con seguir como hoy en los mismos futuros (mismas semillas)."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from dcsim import catalog as C
from dcsim import server
from dcsim.insights import METRICS
from dcsim.montecarlo import CACHE_DIR, _cache_key
from dcsim.policy import STATUS_QUO

N = 8  # pocos futuros: cada regla corre en medio segundo
Y35 = 1  # columna de 2035 en los valores pareados


@pytest.fixture
def client(monkeypatch):
    """Cliente con N futuros por regla propia; borra el «como hoy» chico que deja en cache/."""
    monkeypatch.setattr(server, "N_CUSTOM", N)
    path = CACHE_DIR / f"{_cache_key(STATUS_QUO, N, 'anchored')}.json"
    existed = path.exists()
    yield TestClient(server.app)  # sin «with»: no precalienta los ensambles de la portada
    if not existed:
        path.unlink(missing_ok=True)


def test_custom_rule_is_compared_on_the_same_futures(client, ensembles):
    sq = {k: np.array(v) for k, v in ensembles["status_quo"]["paired"].items()}  # 200 futuros
    res = client.post("/api/run", json={"policy": {"air_cooling_rm": True}}).json()
    assert res["meta"]["n"] == res["baseline"]["n"] == N

    # «como hoy» son los primeros N de los 200 futuros de la portada: las mismas semillas
    base = client.get("/api/baseline").json()
    assert base["meta"]["n"] == N
    for k, v in base["paired"].items():
        assert np.array_equal(v, sq[k][:N]), k
    for k in server.STORY_KEYS:
        assert res["baseline"]["values"][k] == base["series"][k]["p50"][C.YEARS.index(2035)], k
        if k in sq:
            first = np.median(sq[k][:N, Y35])
            assert res["baseline"]["values"][k] == pytest.approx(first, abs=2e-3), k

    # los conteos salen de comparar futuro a futuro y suman N
    assert set(res["compare"]) == set(server.COMPARE_KEYS)
    assert set(server.COMPARE_KEYS) <= set(res["paired"])  # cada cifra tiene valores por futuro
    for k, c in res["compare"].items():
        a, b = np.array(res["paired"][k])[:, Y35], sq[k][:N, Y35]
        up, down = int((a > b).sum()), int((a < b).sum())
        good_up = METRICS[k][2]
        if good_up is None:
            assert (c["more"], c["less"]) == (up, down), k
        else:
            assert (c["better"], c["worse"]) == ((up, down) if good_up else (down, up)), k
        assert c["same"] == N - up - down and c["n"] == N, k
    assert res["compare"]["water_ls_rm"]["better"] == N  # sin agua para enfriar, en todos


def test_status_quo_as_custom_rule_changes_nothing(client):
    res = client.post("/api/run", json={"policy": {}}).json()
    for k, c in res["compare"].items():
        assert c["same"] == c["n"] == N, k  # ni mejor ni peor, ni más ni menos
    assert res["paired"] == client.get("/api/baseline").json()["paired"]  # los mismos futuros
