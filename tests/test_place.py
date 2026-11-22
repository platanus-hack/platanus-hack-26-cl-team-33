import numpy as np
import pytest
from fastapi.testclient import TestClient

from dcsim import catalog as C
from dcsim import server
from dcsim.model import FRAME_T, ST_OPER, Run, population_view
from dcsim.params import base_values
from dcsim.place import RADIUS_KM, build_probes, households_within, normalize, simulate, site_info
from dcsim.policy import STATUS_QUO

LAMPA = (-33.33, -70.77)  # Valle Grande, junto a los DC de Lampa
PUDAHUEL_W = (-33.44, -70.80)  # periferia poniente, sin casas a menos de 500 m


def _user(site, **kw):
    s = site_info(*site)
    return {"it_mw": 30, "cooling": "aire", "announce": C.ym("2027-01"),
            "commune": s["commune"], "near_homes": s["near_homes"], **kw}


def test_probes_are_passive():
    """Los hogares de muestra pesan cero: sin data center del usuario nada cambia."""
    view = population_view(LAMPA, build_probes(*LAMPA))
    a = Run(STATUS_QUO, seed=5).run().rec
    b = Run(STATUS_QUO, seed=5, pop=view).run().rec
    for k in ("it_chile", "litigations", "c_conflict", "p_status", "waitlist_mw"):
        assert np.allclose(a[k], b[k]), k


def test_user_dc_keeps_everyone_elses_random_numbers():
    view = population_view(PUDAHUEL_W)
    base = Run(STATUS_QUO, seed=2)
    withdc = Run(STATUS_QUO, seed=2, pop=view, user_dc=_user(PUDAHUEL_W))
    nb = base.N
    assert withdc.N == nb + 1 and withdc.user_i == nb
    for k in ("z", "u", "u_month", "gumbel", "lfmax"):
        assert np.array_equal(getattr(base, k), getattr(withdc, k)[:nb]), k


def test_history_before_announcement_is_untouched():
    view = population_view(PUDAHUEL_W)
    a = Run(STATUS_QUO, seed=4, pop=view).run().rec
    b = Run(STATUS_QUO, seed=4, pop=view, user_dc=_user(PUDAHUEL_W)).run().rec
    upto = C.YEARS.index(2026) + 1
    for k in ("it_chile", "litigations", "c_conflict"):
        assert np.allclose(a[k][..., :upto], b[k][..., :upto]), k


def test_air_cooled_dc_with_grid_priority_operates():
    view = population_view(PUDAHUEL_W)
    r = Run(STATUS_QUO, seed=0, params=base_values(), pop=view,
            user_dc=_user(PUDAHUEL_W, grid_priority=True)).run()
    assert r.status[r.user_i] == ST_OPER
    assert len(r.frames["status"]) == len(FRAME_T)
    assert r.frames["wls"][-1] < 1  # por aire casi no usa agua


def test_site_info():
    s = site_info(*LAMPA)
    assert s["ok"] and s["commune_id"] == "lampa" and s["aquifer"]
    h = [s["households"][str(r)] for r in (0.3, 0.5, 1.0, 3.0)]
    assert h == sorted(h) and h[-1] > 1000
    assert not site_info(-34.5, -71.5)["ok"]  # lejos de las comunas modeladas


def test_probe_weights_add_up_to_households_nearby():
    p = build_probes(*LAMPA)
    assert np.isclose(p["w"].sum(), households_within(*LAMPA, RADIUS_KM))
    assert (p["dist"] <= RADIUS_KM + 1e-9).all()


def test_evaporative_dc_next_to_homes_mobilizes_neighbours():
    r = simulate({"lat": LAMPA[0], "lon": LAMPA[1], "it_mw": 100, "cooling": "evaporativo"},
                 n=8, workers=1)
    assert r["mob_with"]["p50"][-1] > r["mob_without"]["p50"][-1]
    assert r["facts"]["p_sued"] > 0.3
    assert len(r["frames"]) == len(r["status_prob"]) == len(r["p_mob_with"])


def test_normalize_rejects_bad_input():
    with pytest.raises(ValueError):
        normalize({"lat": -33.4, "lon": -70.7, "it_mw": 5000})
    with pytest.raises(ValueError):
        normalize({"lat": 40.0, "lon": -3.7})


def test_place_api(monkeypatch):
    monkeypatch.setattr(server, "N_PLACE", 4)
    with TestClient(server.app) as client:
        site = client.get("/api/place/site", params={"lat": LAMPA[0], "lon": LAMPA[1]}).json()
        assert site["ok"]
        res = client.post("/api/place", json={"lat": PUDAHUEL_W[0], "lon": PUDAHUEL_W[1],
                                              "it_mw": 30, "cooling": "aire"}).json()
        assert res["n"] == 4 and res["site"]["commune_id"] == "pudahuel"
        bad = client.post("/api/place", json={"lat": -34.5, "lon": -71.5})
        assert bad.status_code == 400
