import numpy as np

from dcsim import catalog as C
from dcsim.model import ST_OPER, ST_WAIT, Run
from dcsim.params import base_values
from dcsim.policy import SCENARIOS, STATUS_QUO

HIST_END = C.YEARS.index(2026)


def test_same_seed_same_result():
    a = Run(STATUS_QUO, seed=7).run().rec
    b = Run(STATUS_QUO, seed=7).run().rec
    for k in ("it_chile", "water_ls_rm", "c_conflict", "p_status"):
        assert np.array_equal(a[k], b[k])


def test_history_is_identical_across_policies():
    """Números aleatorios comunes: la historia no depende de la política futura."""
    base = Run(STATUS_QUO, seed=3).run().rec
    for sid, s in SCENARIOS.items():
        if s["policy"].demand != "base":
            continue
        r = Run(s["policy"], seed=3).run().rec
        for k in ("it_chile", "waitlist_mw", "litigations", "google_water_ml"):
            assert np.allclose(base[k][:HIST_END], r[k][:HIST_END]), (sid, k)


def test_anchored_mode_matches_documented_2026_status():
    r = Run(STATUS_QUO, seed=0, params=base_values()).run().rec
    st = r["p_status"][:, C.YEARS.index(2026)]
    for i, p in enumerate(C.PROJECTS):
        if p.real_status == "operando":
            assert st[i] == ST_OPER, p.id
        if p.real_status == "lista_espera":
            assert st[i] == ST_WAIT, p.id


def test_google_quilicura_water_physics():
    """30 MW medios × 1,74 L/kWh ≈ 458 ML al año (≈ 14,5 L/s)."""
    r = Run(STATUS_QUO, seed=0, params=base_values()).run().rec
    ml = r["google_water_ml"][C.YEARS.index(2024)]
    assert 400 < ml < 520
