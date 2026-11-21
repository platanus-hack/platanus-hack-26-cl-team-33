"""Precalcula todo lo que la portada necesita y deja en cache/ solo esos archivos.

    uv run python -m dcsim.precompute

Correrlo después de cambiar el modelo y antes de desplegar: el servidor parte leyendo estos
resultados en vez de simular ~2.000 futuros en una CPU chica. Los archivos se versionan en git.
"""

from __future__ import annotations

import time

from .montecarlo import CACHE_DIR, _cache_key, run_ensemble
from .policy import HYPOTHESIS_SCENARIOS, SCENARIOS, STATUS_QUO
from .server import N_PRESET
from .validation import run_validation


def main() -> None:
    t0 = time.time()
    keep = set()
    policies = [s["policy"] for s in SCENARIOS.values()] + list(HYPOTHESIS_SCENARIOS.values())
    for pol in policies:
        run_ensemble(pol, n=N_PRESET)
        keep.add(f"{_cache_key(pol, N_PRESET, 'anchored')}.json")
    run_validation(n=N_PRESET)
    keep.add(f"{_cache_key(STATUS_QUO, N_PRESET, 'free')}.json")
    removed = 0
    for f in CACHE_DIR.glob(f"*_{N_PRESET}_*.json"):
        if f.name not in keep:
            f.unlink()
            removed += 1
    print(f"{len(keep)} archivos listos, {removed} obsoletos borrados, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
