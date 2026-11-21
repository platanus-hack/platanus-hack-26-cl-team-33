"""Precalcula todo lo que la portada necesita y deja en cache/ solo esos archivos.

    uv run python -m dcsim.precompute

Correrlo después de cambiar el modelo y antes de desplegar: el servidor parte leyendo estos
resultados en vez de simular ~2.000 futuros en una CPU chica. Los archivos se versionan en git.

También deja "Como hoy" con los tamaños que usa "Tu regla" (60 futuros en Render free, 100 en
standard): la regla del usuario se compara con "Como hoy" en las mismas semillas sin tener que
simularlo de nuevo al partir el servidor.
"""

from __future__ import annotations

import re
import time

from .montecarlo import CACHE_DIR, _cache_key, run_ensemble
from .policy import HYPOTHESIS_SCENARIOS, SCENARIOS, STATUS_QUO
from .server import N_CUSTOM, N_PRESET
from .validation import run_validation

N_BASELINE = sorted({60, 100, N_CUSTOM})  # futuros de "Tu regla" (DCSIM_N_CUSTOM)
ENSEMBLE = re.compile(r"(anchored|free)_(\d+)_[0-9a-f]{16}\.json")


def main() -> None:
    t0 = time.time()
    keep = set()
    policies = [s["policy"] for s in SCENARIOS.values()] + list(HYPOTHESIS_SCENARIOS.values())
    for pol in policies:
        run_ensemble(pol, n=N_PRESET)
        keep.add(f"{_cache_key(pol, N_PRESET, 'anchored')}.json")
    run_validation(n=N_PRESET)
    keep.add(f"{_cache_key(STATUS_QUO, N_PRESET, 'free')}.json")
    for n in N_BASELINE:
        run_ensemble(STATUS_QUO, n=n)
        keep.add(f"{_cache_key(STATUS_QUO, n, 'anchored')}.json")
    # Solo se borran ensambles de los tamaños de este script; findings.json, sensitivity.json y
    # explore_raw.json no calzan con el patrón.
    sizes = {N_PRESET, *N_BASELINE}
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        m = ENSEMBLE.fullmatch(f.name)
        if m and int(m.group(2)) in sizes and f.name not in keep:
            f.unlink()
            removed += 1
    print(f"{len(keep)} archivos listos, {removed} obsoletos borrados, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
