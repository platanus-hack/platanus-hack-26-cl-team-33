"""Análisis de sensibilidad: forma del resultado y cómo se arman los parámetros de cada futuro.

No corre el análisis (son 76.500 simulaciones): revisa cache/sensitivity.json y las piezas
que garantizan que cada extremo se compara con la corrida normal en las mismas semillas.
"""

import json
import re
from dataclasses import replace
from pathlib import Path

import numpy as np

from dcsim import sensitivity as S
from dcsim.model import Run
from dcsim.montecarlo import _code_hash
from dcsim.params import PARAMS, P, sample_values
from dcsim.policy import STATUS_QUO

ROOT = Path(__file__).resolve().parent.parent
FIXED = [p.key for p in PARAMS if not p.sample]


def _sens() -> dict:
    return json.loads((ROOT / "cache" / "sensitivity.json").read_text())


def test_sensitivity_was_built_with_this_code():
    assert _sens()["model"] == _code_hash(), (
        "cache/sensitivity.json está desactualizado: corre python -m dcsim.sensitivity")


def test_sensitivity_covers_every_fixed_assumption_and_finding():
    out = _sens()
    assert [f["key"] for f in out["factors"]] == FIXED
    assert [f["id"] for f in out["findings"]] == [
        "paquete", "permisos", "boom", "cerrillos", "lampa", "transparencia"]
    for f in out["findings"]:
        assert f["total"] == 2 * len(FIXED), f["id"]
        assert 0 <= f["holds"] <= f["total"], f["id"]
        assert 0 <= f["holds_consistent"] <= f["total_consistent"] <= f["total"], f["id"]
        assert [r["key"] for r in f["oat"]] == FIXED, f["id"]
        assert len(f["top"]) == 3 and f["range"][0] <= f["range"][1], f["id"]
        assert f["joint"]["n"] == out["n_joint"] > 0, f["id"]


def test_kickers_match_the_published_findings():
    pub = {f["id"]: f for f in json.loads((ROOT / "cache" / "findings.json").read_text())}
    for f in _sens()["findings"]:
        assert f["kicker"] == pub[f["id"]]["kicker"], f["id"]


def test_base_setting_is_a_normal_run():
    """Sin ajuste, los parámetros y la corrida son los de siempre (números aleatorios comunes)."""
    for seed in range(5):
        assert S.params_for(seed, ("base",)) == sample_values(np.random.default_rng([seed, 1]))
    a = Run(STATUS_QUO, seed=3).run().rec
    b = Run(STATUS_QUO, seed=3, params=S.params_for(3, ("base",))).run().rec
    for k in a:
        assert np.array_equal(a[k], b[k]), k


def test_one_at_a_time_changes_only_that_assumption():
    v0 = S.params_for(2, ("base",))
    v = S.params_for(2, ("oat", "op_w_water", P["op_w_water"].low))
    assert {k for k in v if v[k] != v0[k]} == {"op_w_water"}


def test_joint_setting_keeps_the_usual_draws():
    for seed in range(5):
        v0, v = S.params_for(seed, ("base",)), S.params_for(seed, ("joint",))
        for p in PARAMS:
            if p.sample:
                assert v[p.key] == v0[p.key], p.key
            else:
                assert p.low <= v[p.key] <= p.high, p.key
    assert S.params_for(0, ("joint",))["op_w_water"] != S.params_for(1, ("joint",))["op_w_water"]


def test_demand_of_5_per_year_is_the_status_quo():
    """El análisis reutiliza "Como hoy" como la demanda de 5 proyectos al año del boom."""
    a = Run(STATUS_QUO, seed=1).run().rec
    b = Run(replace(STATUS_QUO, demand_rate=5.0), seed=1).run().rec
    for k in a:
        assert np.array_equal(a[k], b[k]), k


def test_model_reads_only_declared_params():
    """Cada v["..."] del modelo es un parámetro con rango, y cada parámetro se usa."""
    src = (ROOT / "dcsim" / "model.py").read_text()
    used = set(re.findall(r"""\bv\[["'](\w+)["']\]""", src))
    assert used <= set(P), sorted(used - set(P))
    assert set(P) <= used, sorted(set(P) - used)
