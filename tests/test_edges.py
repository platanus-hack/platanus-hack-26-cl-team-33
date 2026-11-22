"""Entradas raras de la API y de la sensibilidad: 4xx claro, nunca 500 ni archivos a medias."""

import pytest
from fastapi.testclient import TestClient

from dcsim import sensitivity
from dcsim.server import app

JSON = {"content-type": "application/json"}


def test_non_finite_numbers_are_rejected_not_crashed():
    with TestClient(app) as client:
        for raw in ('{"policy": {"permit_speed": NaN}}', '{"policy": {"permit_speed": 1e309}}'):
            assert client.post("/api/run", content=raw, headers=JSON).status_code == 422, raw


def test_unknown_fields_are_rejected():
    with TestClient(app) as client:
        assert client.post("/api/run", json={"policy": {}, "extra": 1}).status_code == 422
        assert client.post("/api/calc", json={"cooling": {}, "extra": 1}).status_code == 422


def test_front_page_proof_shows_only_validation_checks():
    """«Probado con lo que ya pasó» no muestra datos que se usaron para ajustar el modelo."""
    with TestClient(app) as client:
        story = client.get("/api/story").json()
    assert story["checks"]
    assert all(c["kind"] == "validación" for c in story["checks"])
    assert story["n_validation"] + story["n_calibration"] == story["total"]


def test_sensitivity_cli_refuses_partial_runs_over_the_committed_file():
    with pytest.raises(SystemExit):
        sensitivity.main(["--factors", "no_existe"])
    with pytest.raises(SystemExit):
        sensitivity.main(["--factors", "op_w_water"])  # parcial y sin --out
