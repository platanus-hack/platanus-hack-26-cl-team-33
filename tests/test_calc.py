"""Calculadora de evaluación conjunta: cambiar el enfriamiento desde 2027 sin tocar la historia."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from dcsim import catalog as C
from dcsim import server
from dcsim.model import AIR, EVAP, ST_PERMIT, Run
from dcsim.montecarlo import CACHE_DIR, _cache_key
from dcsim.policy import STATUS_QUO

Y26 = C.YEARS.index(2026)
Y35 = C.YEARS.index(2035)


def test_cooling_from_2027_keeps_the_history_and_moves_water_and_power():
    q = C.COMMUNE_IDX["quilicura"]
    ov = {"microsoft_scl03": {"cooling_2027": "evaporativo"},
          "ascenty_3": {"cooling_2027": "evaporativo"}}
    wa, wb = [], []
    for seed in range(6):
        a = Run(STATUS_QUO, seed=seed).run().rec
        b = Run(STATUS_QUO, seed=seed, overrides=ov).run().rec
        for k in ("c_water_ls", "c_demand", "p_status", "litigations"):
            assert np.array_equal(a[k][..., :Y26 + 1], b[k][..., :Y26 + 1]), k
        wa.append(a["c_water_ls"][q, Y35])
        wb.append(b["c_water_ls"][q, Y35])
    # con agua, más agua en la mediana (en un futuro dado pueden no alcanzar a operar: juicios)
    assert np.median(wb) > np.median(wa)


def test_air_costs_electricity_for_the_same_project():
    i = C.PROJECT_IDX["campo_lampa"]
    water, power = [], []
    for seed in range(4):
        a = Run(STATUS_QUO, seed=seed).run()  # declarado: aire
        ov = {"campo_lampa": {"cooling_2027": "evaporativo"}}
        b = Run(STATUS_QUO, seed=seed, overrides=ov).run()
        if a.rec["p_mw"][i, Y35] > 0 and b.rec["p_mw"][i, Y35] > 0:
            water.append(b.rec["p_water_ls"][i, Y35] - a.rec["p_water_ls"][i, Y35])
            power.append(a.rec["p_mw"][i, Y35] - b.rec["p_mw"][i, Y35])
    assert water and min(water) > 0 and min(power) > 0  # agua: más litros; aire: más MW
    assert a.cool[i] == AIR and b.cool[i] in (EVAP, AIR)


def test_scripted_project_is_not_stuck_after_its_script_ends():
    """Antes, una anulación después del guion dejaba a Cerrillos «en tramitación» para siempre."""
    i = C.PROJECT_IDX["google_cerrillos"]
    ov = {"google_cerrillos": {"cooling_2027": "evaporativo"}}
    for seed in range(8):
        st = Run(STATUS_QUO, seed=seed, overrides=ov).run().rec["p_status"][i]
        stuck = all(st[y] == ST_PERMIT for y in range(C.YEARS.index(2028), Y35 + 1))
        assert not stuck, seed


@pytest.fixture()
def small_n(monkeypatch):
    """Pocos futuros para que el test sea rápido; borra el «como hoy» de 6 futuros que crea."""
    n = 6
    path = CACHE_DIR / f"{_cache_key(STATUS_QUO, n, 'anchored')}.json"
    existed = path.exists()
    monkeypatch.setattr(server, "N_CUSTOM", n)
    server._calc.clear()
    yield n
    server._calc.clear()
    if not existed:
        path.unlink(missing_ok=True)


def test_calc_endpoint(small_n):
    with TestClient(server.app) as client:
        base = client.post("/api/calc", json={"cooling": {}}).json()
        assert base["compare"] is None and base["meta"]["n"] == small_n
        # pedir el enfriamiento que ya tiene no es un cambio
        same = client.post("/api/calc", json={"cooling": {"google_cerrillos": "aire"}}).json()
        assert same["compare"] is None
        res = client.post("/api/calc", json={"cooling": {"campo_lampa": "evaporativo"}}).json()
        assert res["changes"] == {"campo_lampa": "evaporativo"}
        li = C.COMMUNE_IDX["lampa"]
        c = res["compare"]["c_water_ls"][li]
        assert c["better"] + c["worse"] + c["same"] == small_n
        def status(cooling):
            return client.post("/api/calc", json={"cooling": cooling}).status_code
        assert status({"google_quilicura_1": "aire"}) == 400  # ya opera: no se cambia
        assert status({"campo_lampa": "hielo"}) == 422


def test_front_page_question_is_precomputed():
    """Quilicura con agua responde al instante en el sitio (60 futuros) y en local (100)."""
    ov = server.calc_demo_overrides()
    assert sorted(ov) == ["ascenty_3", "ascenty_data_hall", "cirion_quilicura_2", "microsoft_scl03"]
    for n in (60, 100):
        assert (CACHE_DIR / f"{_cache_key(STATUS_QUO, n, 'anchored', ov)}.json").exists(), n
