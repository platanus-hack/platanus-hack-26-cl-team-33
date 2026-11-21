"""La página muestra el análisis de sensibilidad: /api/sensitivity y el resumen en /api/story.

Rápido: lee cache/sensitivity.json y los escenarios ya guardados en cache/, no simula.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from dcsim import server

ROOT = Path(__file__).resolve().parent.parent
SENS = json.loads((ROOT / "cache" / "sensitivity.json").read_text())


def test_sensitivity_endpoint_returns_the_cached_analysis():
    client = TestClient(server.app)  # sin "with": no hace falta precalentar los escenarios
    assert client.get("/api/sensitivity").json() == SENS


def test_story_summarises_each_finding_from_the_analysis():
    """Cada hallazgo trae en cuántas variantes se mantiene y, en las que no, qué supuesto se
    movió y a qué valor: la misma cuenta que cache/sensitivity.json, hecha aparte aquí."""
    summary = TestClient(server.app).get("/api/story").json()["sensitivity"]
    factors = {f["key"]: f for f in SENS["factors"]}
    assert list(summary) == [f["id"] for f in SENS["findings"]]
    for f in SENS["findings"]:
        s = summary[f["id"]]
        assert (s["holds"], s["total"], s["joint_holds"]) == (
            f["holds"], f["total"], f["joint"]["holds"]), f["id"]
        expected = [(r["key"], end, factors[r["key"]][end]) for r in f["oat"]
                    for end in ("low", "high") if not r[f"holds_{end}"]]
        assert [(x["key"], x["end"], x["value"]) for x in s["fails"]] == expected, f["id"]
        assert len(s["fails"]) == s["total"] - s["holds"], f["id"]
        for x in s["fails"]:
            fac = factors[x["key"]]
            assert (x["label"], x["base"], x["unit"]) == (fac["label"], fac["base"], fac["unit"])


def test_summary_without_joint_draw_or_analysis():
    """Sin sorteo conjunto no se afirma que falle; sin análisis, no hay nada que mostrar."""
    one = {"factors": [{"key": "a", "label": "Supuesto A", "base": 1.0, "low": 0.5, "high": 2.0,
                        "unit": "—"}],
           "findings": [{"id": "x", "holds": 1, "total": 2,
                         "joint": {"value": None, "holds": False, "n": 0},
                         "oat": [{"key": "a", "low": 0.1, "high": 0.9, "holds_low": True,
                                  "holds_high": False}]}]}
    assert server.sensitivity_summary(one) == {"x": {
        "holds": 1, "total": 2, "joint_holds": None,
        "fails": [{"key": "a", "label": "Supuesto A", "end": "high", "value": 2.0, "base": 1.0,
                   "unit": "—"}]}}
    assert server.sensitivity_summary({}) == {}


def test_missing_analysis_file_gives_an_empty_answer(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "SENSITIVITY_JSON", tmp_path / "no-existe.json")
    monkeypatch.setattr(server, "_memo", {})  # memo aparte: no deja el {} para otros tests
    assert TestClient(server.app).get("/api/sensitivity").json() == {}
