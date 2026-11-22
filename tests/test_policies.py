"""Las palancas mueven los resultados en la dirección que exige su mecanismo."""

Y35 = 1  # índice de 2035 en los valores pareados


def med(res, key, idx=Y35):
    vals = sorted(v[idx] for v in res["paired"][key])
    return vals[len(vals) // 2]


def test_air_cooling_cuts_water(ensembles):
    assert med(ensembles["aire"], "water_ls_rm") < 0.7 * med(ensembles["status_quo"], "water_ls_rm")


def test_threshold_80_routes_projects_to_seia(ensembles):
    sq = ensembles["status_quo"]["extra"]["routes"]
    u80 = ensembles["umbral_80"]["extra"]["routes"]
    share = lambda r: r.get("SEIA", 0) / sum(r.values())  # noqa: E731
    assert share(sq) < 0.15
    assert share(u80) > 0.6


def test_cumulative_evaluation_reduces_litigation(ensembles):
    cum, sq = ensembles["acumulativa"], ensembles["status_quo"]
    assert med(cum, "litigations") < med(sq, "litigations")


def test_faster_permits_barely_add_capacity_when_grid_is_full(ensembles):
    base = med(ensembles["status_quo"], "it_rm", 0)
    fast = med(ensembles["mesa"], "it_rm", 0)
    assert abs(fast - base) / base < 0.05


def test_north_incentive_moves_capacity_to_antofagasta(ensembles):
    assert med(ensembles["norte"], "mw_antofagasta", 0) > med(ensembles["status_quo"],
                                                             "mw_antofagasta", 0) + 50
