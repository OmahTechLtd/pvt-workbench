"""Oil viscosity correlations and the calculation behind the viscosity page.
Source for the equations: Ahmed, Reservoir Engineering Handbook, 5th ed., pp. 104-109.
Temperatures are in degF (converted to degR inside where the source uses T in degR). Viscosity in cp."""
import math
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel



def mu_dead_beal(api, t_f):
    """Beal (1946), as curve-fit by Standing. Eq. printed in Example 2-36, p. 108."""
    t_r = t_f + 460
    a = 10 ** (0.43 + 8.33 / api)
    return (0.32 + 1.8e7 / api ** 4.53) * (360 / (t_r - 260)) ** a


def mu_dead_beggs_robinson(api, t_f):
    """Beggs and Robinson (1975). x = Y T^-1.163 with T in degF; the source prints (T - 460) with T in degR."""
    z = 3.0324 - 0.02023 * api
    y = 10 ** z
    x = y * t_f ** -1.163
    return 10 ** x - 1


def mu_dead_glaso(api, t_f):
    """Glaso (1980). Temperature in degF; the source prints (T - 460) with T in degR."""
    a = 10.313 * math.log10(t_f) - 36.447
    return 3.141e10 * t_f ** -3.444 * math.log10(api) ** a


def mu_sat_chew_connally(mu_od, rs):
    """Chew and Connally (1959), Eq. 2-109 with the Standing curve fit."""
    a = rs * (2.2e-7 * rs - 7.4e-4)
    c = 8.62e-5 * rs
    d = 1.1e-3 * rs
    e = 3.74e-3 * rs
    b = 0.68 / 10 ** c + 0.25 / 10 ** d + 0.062 / 10 ** e
    return 10 ** a * mu_od ** b


def mu_sat_beggs_robinson(mu_od, rs):
    """Beggs and Robinson (1975), Eq. 2-120."""
    a = 10.715 * (rs + 100) ** -0.515
    b = 5.44 * (rs + 150) ** -0.338
    return a * mu_od ** b


def mu_under_beal(mu_ob, p, pb):
    """Beal (1946) curve-fit by Standing (1981), p. 107."""
    return mu_ob + 0.001 * (p - pb) * (0.024 * mu_ob ** 1.6 + 0.038 * mu_ob ** 0.56)


def mu_under_vasquez_beggs(mu_ob, p, pb, m_coeff=2.6):
    """Vasquez and Beggs (1980), Eq. 2-121. The coefficient is 2.6 on p. 107 and 26 in Example 2-36 on p. 109."""
    a = -3.9e-5 * p - 5
    m = m_coeff * p ** 1.187 * 10 ** a
    return mu_ob * (p / pb) ** m


DEAD = [("beal", "Beal (1946)", mu_dead_beal), ("beggs_robinson", "Beggs-Robinson (1975)", mu_dead_beggs_robinson),
        ("glaso", "Glaso (1980)", mu_dead_glaso)]
SAT = [("chew_connally", "Chew-Connally (1959)", mu_sat_chew_connally),
       ("beggs_robinson", "Beggs-Robinson (1975)", mu_sat_beggs_robinson)]
UNDER = [("beal", "Beal (1946), Standing fit", mu_under_beal), ("vasquez_beggs", "Vasquez-Beggs (1980)", mu_under_vasquez_beggs)]

# Example 2-36, p. 108. Oil 2 uses 1.286 cp for the dead-oil viscosity, as the data table prints and as the
# book's AAE figures need. Oil 4 is run at 5,000 psi because the published undersaturated results need it.
EX236 = [
    dict(oil=1, api=47.1, t_f=250, rs=751, pb=2377, p=5000, mu_od=0.765, mu_ob=0.224, mu_o=0.281),
    dict(oil=2, api=40.7, t_f=220, rs=768, pb=2620, p=5000, mu_od=1.286, mu_ob=0.373, mu_o=0.450),
    dict(oil=3, api=48.6, t_f=260, rs=693, pb=2051, p=5000, mu_od=0.686, mu_ob=0.221, mu_o=0.292),
    dict(oil=4, api=40.5, t_f=237, rs=968, pb=2884, p=5000, mu_od=1.014, mu_ob=0.377, mu_o=0.414),
    dict(oil=5, api=44.2, t_f=218, rs=943, pb=3045, p=6000, mu_od=1.009, mu_ob=0.305, mu_o=0.394),
    dict(oil=6, api=27.3, t_f=180, rs=807, pb=4239, p=5000, mu_od=4.166, mu_ob=0.950, mu_o=1.008),
]
BOOK = {
    "dead": {"beal": [0.322, 0.638, 0.275, 0.545, 0.512, 4.425], "beggs_robinson": [0.568, 1.020, 0.493, 0.917, 0.829, 4.246],
             "glaso": [0.417, 0.775, 0.363, 0.714, 0.598, 4.536]},
    "dead_aae": {"beal": 44.9, "beggs_robinson": 17.32, "glaso": 35.26},
    "sat": {"chew_connally": [0.313, 0.426, 0.308, 0.311, 0.316, 0.842], "beggs_robinson": [0.287, 0.377, 0.279, 0.297, 0.300, 0.689]},
    "sat_aae": {"chew_connally": 21.0, "beggs_robinson": 17.0},
    "under": {"beal": [0.273, 0.437, 0.275, 0.434, 0.373, 0.945], "vasquez_beggs": [0.303, 0.485, 0.318, 0.472, 0.417, 1.016]},
    "under_aae": {"beal": 3.8, "vasquez_beggs": 7.5},
}


def _aae(calc, meas):
    return 100 * sum(abs(c - m) / m for c, m in zip(calc, meas)) / len(meas)


class ViscosityIn(BaseModel):
    api: Optional[float] = None
    t_f: Optional[float] = None
    rs: Optional[float] = None
    p: Optional[float] = None
    pb: Optional[float] = None
    mu_od_measured: Optional[float] = None
    mu_ob_measured: Optional[float] = None
    mu_o_measured: Optional[float] = None


def _safe(f, *a):
    try:
        v = f(*a)
        return v if isinstance(v, float) and math.isfinite(v) and v > 0 else None
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def _rows(items, measured):
    out = []
    for r in items:
        if r["value"] is not None and measured:
            r["error_pct"] = 100 * (r["value"] - measured) / measured
        out.append(r)
    return out


def compute_viscosity(i: ViscosityIn):
    res = {"dead": [], "saturated": [], "undersaturated": [], "notes": []}
    if i.api is not None and i.t_f is not None:
        if i.api <= 0 or i.t_f <= 0:
            raise HTTPException(422, "API gravity and temperature must be above zero.")
        res["dead"] = _rows([{"key": k, "name": n, "value": _safe(f, i.api, i.t_f)} for k, n, f in DEAD], i.mu_od_measured)
    dead_sources = []
    if i.mu_od_measured:
        dead_sources.append(("measured dead-oil viscosity", i.mu_od_measured))
    dead_sources += [(f"{n} dead-oil viscosity", r["value"]) for (k, n, f), r in zip(DEAD, res["dead"]) if r["value"]]
    if i.rs is not None and i.rs >= 0:
        for src, mud in dead_sources:
            for k, n, f in SAT:
                v = _safe(f, mud, i.rs)
                res["saturated"].append({"key": k, "name": n, "from": src, "value": v})
        res["saturated"] = _rows(res["saturated"], i.mu_ob_measured)
    if i.p is not None and i.pb is not None:
        if i.p < i.pb:
            raise HTTPException(422, "The undersaturated equations apply at or above the bubble point. Pressure is below pb.")
        sources = []
        if i.mu_ob_measured:
            sources.append(("measured bubble-point viscosity", i.mu_ob_measured))
        sources += [(f"{r['name']} with {r['from']}", r["value"]) for r in res["saturated"] if r["value"]]
        for src, mob in sources:
            for k, n, f in UNDER:
                res["undersaturated"].append({"key": k, "name": n, "from": src, "value": _safe(f, mob, i.p, i.pb)})
        res["undersaturated"] = _rows(res["undersaturated"], i.mu_o_measured)
    return res


def viscosity_checks():
    rows = EX236
    out = {"dead": [], "saturated": [], "undersaturated": []}
    meas_dead = [r["mu_od"] for r in rows]
    for k, n, f in DEAD:
        calc = [f(r["api"], r["t_f"]) for r in rows]
        out["dead"].append({"name": n, "calc": calc, "book": BOOK["dead"][k], "aae": _aae(calc, meas_dead), "book_aae": BOOK["dead_aae"][k]})
    meas_ob = [r["mu_ob"] for r in rows]
    for k, n, f in SAT:
        calc = [f(r["mu_od"], r["rs"]) for r in rows]
        out["saturated"].append({"name": n, "calc": calc, "book": BOOK["sat"][k], "aae": _aae(calc, meas_ob), "book_aae": BOOK["sat_aae"][k]})
    meas_o = [r["mu_o"] for r in rows]
    for k, n, f in UNDER:
        calc = [f(r["mu_ob"], r["p"], r["pb"]) for r in rows]
        out["undersaturated"].append({"name": n, "calc": calc, "book": BOOK["under"][k], "aae": _aae(calc, meas_o), "book_aae": BOOK["under_aae"][k]})
    out["measured"] = {"dead": meas_dead, "saturated": meas_ob, "undersaturated": meas_o}
    out["notes"] = [
        "Oil 2 dead-oil viscosity is 1.286 cp in the data table and 0.286 cp in the results table. The published average errors for all three dead-oil methods and its saturated results for oil 2 reproduce only with 1.286, so that value is used.",
        "Oil 4 is run at 5,000 psi. The data table lists 6,000 psi, but the published undersaturated results for oil 4 reproduce only at 5,000 psi.",
        "Oil 4 uses 237 degF here, as the viscosity table prints, and the dead-oil results reproduce with it. The gas-oil ratio and bubble-point checks reproduce with 214 degF for this oil.",
        "The published Beal result for oil 6 is 0.945 cp, which is below the bubble-point viscosity of 0.950 cp. The equation cannot give that, so this one value is not reproduced (it returns 0.995 cp).",
        "Beal's average error is 3.8% and Vasquez-Beggs 7.5% in the source. They reproduce when the measured viscosity for oil 5 is taken as 0.394 cp, as the data table prints (the results table prints 0.396).",
        "Vasquez-Beggs uses a coefficient of 2.6 in m = 2.6 p^1.187 10^a on p. 107. Example 2-36 prints 26 on p. 109. Only 2.6 gives the published answers.",
        "The source prints the Beggs-Robinson saturated average error as 17%. The six values match to three decimals and average 17.6% here, so the difference looks like rounding in the source.",
        "Temperatures are in degF. The published formulas print (T - 460) with T in degR for Beggs-Robinson and Glaso, which is the same thing.",
    ]
    return out
