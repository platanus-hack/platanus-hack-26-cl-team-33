"""El modelo debe reproducir los datos observados 2012–2026 (criterio de término)."""

from dcsim.validation import run_validation


def test_hindcast_reproduces_observed_data():
    out = run_validation(n=200)
    failed = [f"{c['label']}: real={c['observed']} modelo={c['sim']}" for c in out["checks"]
              if not c["pass"]]
    assert not failed, "\n".join(failed)


def test_validation_labels_calibration_honestly():
    out = run_validation(n=200)
    kinds = {c["kind"] for c in out["checks"]}
    assert kinds == {"validación", "calibración"}
    assert sum(c["kind"] == "validación" for c in out["checks"]) >= 6
