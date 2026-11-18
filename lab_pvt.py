"""Laboratory PVT analysis.

Constant composition expansion, differential liberation, separator tests, adjustment of
differential data to separator conditions, correction to a new bubble point, and the
gas condensate tests (gas plant products, z-factors, constant volume depletion).

Source for the equations and the worked examples: Ahmed, Reservoir Engineering Handbook,
5th ed., pp. 123-166. Pressures are gauge (psig) at the interface. Where an equation needs
absolute pressure the offset is a parameter, because the source mixes bases between examples
(14.7 psi for the oil examples, 15.025 psi for the gas condensate example).
"""
from typing import List, Optional

import numpy as np
from fastapi import HTTPException
from pydantic import BaseModel

PSC = 14.73          # psia, standard pressure used in Eq. 3-11
TSC = 520.0          # degR, standard temperature used in Eq. 3-11
BBL_FT3 = 5.615      # ft3 per bbl


# --------------------------------------------------------------------------------------
# Equations
# --------------------------------------------------------------------------------------

def relative_volume(v_total, v_sat):
    """Eq. 3-1."""
    return v_total / v_sat


def density_above_pb(rho_sat, vrel):
    """Eq. 3-2."""
    return rho_sat / vrel


def y_function(psat, p, vrel, p_offset=14.7):
    """Eq. 3-3. Defined below the saturation pressure. p and psat are psig, p_offset converts p in the denominator
    to psia. The printed table reproduces with 14.7."""
    return (psat - p) / ((p + p_offset) * (vrel - 1.0))


def vrel_from_y(psat, p, a, b, p_offset=0.0):
    """Eq. 3-5 (and 3-20 with the new saturation pressure). Reproduces the smoothed table with gauge pressure."""
    pp = p + p_offset
    return 1.0 + (psat - p) / (pp * (a + b * pp))


def vrel_above_new_pb(psat_new, p, slope):
    """Eq. 3-21. The slope of the relative volume line above the old saturation pressure is negative."""
    return 1.0 - slope * (psat_new - p)


def compressibility_slope(vrel, dv_dp):
    """Eq. 3-6."""
    return -dv_dp / vrel


def compressibility_interval(v1, v2, p1, p2):
    """Eq. 3-7. Subscript 1 is the higher pressure."""
    return -(1.0 / v2) * (v1 - v2) / (p1 - p2)


def bg_from_z(z, p_abs, t_r, psc=PSC, tsc=TSC):
    """Eq. 3-11. ft3/scf."""
    return (psc / tsc) * z * t_r / p_abs


def z_from_gas(p_abs, v_gas, n, t_r, r=10.73):
    """Eq. 3-27 and 3-29. p psia, volume ft3, n lb-mol, T degR."""
    return p_abs * v_gas / (n * r * t_r)


def moles_produced(v_gp_sc, psc=14.73, tsc=520.0, r=10.73):
    """Eq. 3-28."""
    return psc * v_gp_sc / (r * tsc)


def btd(bod, rsdb, rsd, bg_ft3_scf):
    """Eq. 3-9. Bg is converted from ft3/scf to bbl/scf."""
    return bod + (rsdb - rsd) * bg_ft3_scf / BBL_FT3


def shrinkage(bod, bodb):
    """Eq. 3-14."""
    return bod / bodb


def bo_below_pb(bofb, sod):
    """Eq. 3-15."""
    return bofb * sod


def bo_above_pb(bofb, vrel):
    """Eq. 3-16."""
    return bofb * vrel


def rs_adjusted(rsfb, rsdb, rsd, bofb, bodb):
    """Eq. 3-17."""
    return rsfb - (rsdb - rsd) * bofb / bodb


def bt_from_vrel(bofb, vrel):
    """Eq. 3-18."""
    return bofb * vrel


def bt_from_btd(btd_value, bofb, bodb):
    """Eq. 3-19."""
    return btd_value * bofb / bodb


def rsfb_new(rsfb_old, rsdb_new, rsdb_old):
    """Eq. 3-22."""
    return rsfb_old * rsdb_new / rsdb_old


def bofb_new(bofb_old, bodb_new, bodb_old):
    """Eq. 3-23."""
    return bofb_old * bodb_new / bodb_old


def gpm_factor(psc=15.025, tsc=520.0):
    """Constant in Eq. 3-24."""
    return 11.173 * psc / tsc


def gpm_component(y, m, gamma_oi, psc=15.025, tsc=520.0):
    """Eq. 3-24. gal per Mscf of gas processed."""
    return gpm_factor(psc, tsc) * y * m / gamma_oi


def z_from_cce(z1, p, p1, vrel, vrel1=1.0):
    """Eq. 3-25 and 3-26. Pressures psia."""
    return z1 * (p / p1) * (vrel / vrel1)


def z_two_phase(zd, pd, p, gp_fraction):
    """Eq. 3-31. Pressures psia, gp_fraction is Gp/GIIP as a fraction."""
    return (zd / pd) * p / (1.0 - gp_fraction)


def oil_saturation_from_ldo(ldo_pct, swi):
    """Eq. 3-33. LDO in percent of hydrocarbon pore space, swi as a fraction. Returns percent of pore volume."""
    return ldo_pct * (1.0 - swi)


def fit_line(x, y):
    """Least squares straight line y = a + b x. Returns (a, b)."""
    b, a = np.polyfit(np.asarray(x, float), np.asarray(y, float), 1)
    return float(a), float(b)


# --------------------------------------------------------------------------------------
# Handlers (request models and calculation functions used by the API)
# --------------------------------------------------------------------------------------

class PV(BaseModel):
    p: float
    vrel: float


class CCEIn(BaseModel):
    psat: float                         # psig
    rho_sat: Optional[float] = None     # gm/cc at the saturation pressure
    points: List[PV]
    p_offset: float = 14.7
    exclude_near_pct: float = 10.0      # leave out Y-function points this close to psat (percent of psat)
    a: Optional[float] = None           # supply to use a published fit instead of fitting the points
    b: Optional[float] = None


def compute_cce(i: CCEIn):
    pts = sorted(i.points, key=lambda r: -r.p)
    if len(pts) < 3:
        raise HTTPException(status_code=422, detail="Give at least three pressure and relative volume points.")
    rows = []
    for r in pts:
        row = {"p": r.p, "vrel": r.vrel}
        if i.rho_sat and r.p >= i.psat:
            row["density"] = density_above_pb(i.rho_sat, r.vrel)
        if r.p < i.psat and r.vrel > 1.0:
            row["y"] = y_function(i.psat, r.p, r.vrel, i.p_offset)
        rows.append(row)
    cut = i.psat * (1 - i.exclude_near_pct / 100.0)
    fit_pts = [(r["p"], r["y"]) for r in rows if "y" in r and r["p"] <= cut]
    a, b = i.a, i.b
    fit_note = "Coefficients supplied by the caller."
    if a is None or b is None:
        if len(fit_pts) < 2:
            raise HTTPException(status_code=422, detail="Not enough points below the saturation pressure to fit the Y-function.")
        a, b = fit_line([x for x, _ in fit_pts], [y for _, y in fit_pts])
        fit_note = f"Fitted to {len(fit_pts)} points at or below {cut:.0f} psig. Points nearer the saturation pressure are erratic and left out."
    for r in rows:
        if r["p"] < i.psat:
            r["vrel_smooth"] = vrel_from_y(i.psat, r["p"], a, b)
    # compressibility above the saturation pressure
    above = [r for r in rows if r["p"] >= i.psat]
    comp = []
    for hi, lo in zip(above[:-1], above[1:]):
        comp.append({"p_high": hi["p"], "p_low": lo["p"],
                     "co": compressibility_interval(hi["vrel"], lo["vrel"], hi["p"], lo["p"])})
    return {"rows": rows, "a": a, "b": b, "fit_note": fit_note, "compressibility": comp}


class DLRow(BaseModel):
    p: float            # psig
    rsd: float
    bod: float
    z: Optional[float] = None
    rho: Optional[float] = None


class DLIn(BaseModel):
    t_f: float
    rsdb: float
    bodb: float
    rows: List[DLRow]
    p_offset: float = 14.7


def compute_dl(i: DLIn):
    rows = []
    t_r = i.t_f + 460.0
    for r in sorted(i.rows, key=lambda r: -r.p):
        row = {"p": r.p, "rsd": r.rsd, "bod": r.bod, "sod": shrinkage(r.bod, i.bodb)}
        if r.z is not None and r.p > 0:
            bg = bg_from_z(r.z, r.p + i.p_offset, t_r)
            row["bg"] = bg
            row["btd"] = btd(r.bod, i.rsdb, r.rsd, bg)
        rows.append(row)
    return {"rows": rows, "bodb": i.bodb, "rsdb": i.rsdb}


class AdjustIn(BaseModel):
    pb: float                       # psig
    rsdb: float
    bodb: float
    rsfb: float
    bofb: float
    dl: List[DLRow]
    cce: List[PV] = []
    btd: List[PV] = []              # optional (p, Btd) pairs from the DL test, for Eq. 3-19


def compute_adjust(i: AdjustIn):
    out = []
    for r in sorted(i.dl, key=lambda r: -r.p):
        if r.p > i.pb:
            continue
        sod = shrinkage(r.bod, i.bodb)
        out.append({"p": r.p, "rs": rs_adjusted(i.rsfb, i.rsdb, r.rsd, i.bofb, i.bodb) if r.rsd > 0 else 0.0,
                    "bo": bo_below_pb(i.bofb, sod), "sod": sod})
    above = [{"p": r.p, "rs": i.rsfb, "bo": bo_above_pb(i.bofb, r.vrel)}
             for r in sorted(i.cce, key=lambda r: -r.p) if r.p > i.pb]
    # Bt from the CCE relative volume below the bubble point (Eq. 3-18)
    bt_cce = [{"p": r.p, "bt": bt_from_vrel(i.bofb, r.vrel)} for r in sorted(i.cce, key=lambda r: -r.p) if r.p < i.pb]
    bt_dl = [{"p": r.p, "bt": bt_from_btd(r.vrel, i.bofb, i.bodb)} for r in sorted(i.btd, key=lambda r: -r.p)]
    return {"below": out, "above": above, "bt_from_cce": bt_cce, "bt_from_dl": bt_dl}


class SepTest(BaseModel):
    pressure: float          # separator pressure, psig
    temperature: float
    gor_separator: float     # scf per bbl of stock tank oil
    gor_stock_tank: float
    api: Optional[float] = None
    bofb: Optional[float] = None


class SepIn(BaseModel):
    tests: List[SepTest]


def compute_separator(i: SepIn):
    rows = []
    for t in i.tests:
        rows.append({"pressure": t.pressure, "temperature": t.temperature, "api": t.api, "bofb": t.bofb,
                     "rsfb": t.gor_separator + t.gor_stock_tank})
    with_b = [r for r in rows if r["bofb"] is not None]
    best = min(with_b, key=lambda r: r["bofb"]) if with_b else None
    return {"rows": rows, "optimum": best}


class NewPbIn(BaseModel):
    psat_old: float
    psat_new: float
    a: float
    b: float
    slope: float                     # slope of Vrel versus p above the old saturation pressure (negative)
    pressures: List[float]
    rsfb_old: Optional[float] = None
    rsdb_old: Optional[float] = None
    rsdb_new: Optional[float] = None
    bofb_old: Optional[float] = None
    bodb_old: Optional[float] = None
    bodb_new: Optional[float] = None
    stock_tank_gor: float = 0.0


def compute_new_pb(i: NewPbIn):
    if i.slope >= 0:
        raise HTTPException(status_code=422, detail="The slope above the saturation pressure must be negative.")
    rows = []
    for p in sorted(i.pressures, reverse=True):
        if p >= i.psat_new:
            rows.append({"p": p, "vrel": vrel_above_new_pb(i.psat_new, p, i.slope), "eq": "3-21"})
        elif p > 0:
            rows.append({"p": p, "vrel": vrel_from_y(i.psat_new, p, i.a, i.b), "eq": "3-20"})
    res = {"rows": rows}
    if None not in (i.rsfb_old, i.rsdb_old, i.rsdb_new):
        r = rsfb_new(i.rsfb_old, i.rsdb_new, i.rsdb_old)
        res["rsfb_new"] = r
        res["separator_gor_new"] = r - i.stock_tank_gor
    if None not in (i.bofb_old, i.bodb_old, i.bodb_new):
        res["bofb_new"] = bofb_new(i.bofb_old, i.bodb_new, i.bodb_old)
    return res


class DLPoint(BaseModel):
    p: float
    value: float


class ExtrapolateIn(BaseModel):
    psat_old: float
    psat_new: float
    points: List[DLPoint]            # Bod or Rsd versus pressure below the old saturation pressure
    value_at_old: float              # Bodb or Rsdb
    low_pct: float = 30.0
    high_pct: float = 90.0


def estimate_new_pb_value(i: ExtrapolateIn):
    """Numerical version of the graphical procedure on p. 147: a straight line through the middle pressure range is
    extended to the new saturation pressure and the curvature at the old saturation pressure is carried over.
    This is an estimate. The published example does not reproduce for Bod."""
    lo, hi = i.psat_old * i.low_pct / 100.0, i.psat_old * i.high_pct / 100.0
    sel = [(r.p, r.value) for r in i.points if lo <= r.p <= hi]
    if len(sel) < 2:
        raise HTTPException(status_code=422, detail="Not enough points in the middle pressure range.")
    a, b = fit_line([x for x, _ in sel], [y for _, y in sel])
    curvature = i.value_at_old - (a + b * i.psat_old)
    return {"line_intercept": a, "line_slope": b, "curvature_at_old": curvature,
            "value_at_new": a + b * i.psat_new + curvature, "points_used": len(sel)}


class GPMComponent(BaseModel):
    name: str
    y: float
    m: float
    gamma_oi: Optional[float] = None


class GPMIn(BaseModel):
    components: List[GPMComponent]
    psc: float = 15.025
    tsc: float = 520.0


def compute_gpm(i: GPMIn):
    rows = []
    total = 0.0
    for c in i.components:
        g = gpm_component(c.y, c.m, c.gamma_oi, i.psc, i.tsc) if c.gamma_oi else None
        if g is not None:
            total += g
        rows.append({"name": c.name, "y": c.y, "gpm": g})
    return {"factor": gpm_factor(i.psc, i.tsc), "rows": rows, "total": total}


class GasCondIn(BaseModel):
    pd: float                        # dew-point pressure, psig
    zd: float
    p_offset: float = 15.025
    cce: List[PV] = []               # pressure (psig) and relative volume
    cvd: List[DLPoint] = []          # pressure (psig) and cumulative produced percent of initial gas in place
    ldo: List[DLPoint] = []          # pressure (psig) and liquid dropout, percent of hydrocarbon pore space
    swi: float = 0.0


def compute_gas_condensate(i: GasCondIn):
    pd_abs = i.pd + i.p_offset
    cce = [{"p": r.p, "vrel": r.vrel, "z": z_from_cce(i.zd, r.p + i.p_offset, pd_abs, r.vrel)}
           for r in sorted(i.cce, key=lambda r: -r.p)]
    cvd = [{"p": r.p, "gp_pct": r.value,
            "z_two_phase": z_two_phase(i.zd, pd_abs, r.p + i.p_offset, r.value / 100.0)}
           for r in sorted(i.cvd, key=lambda r: -r.p)]
    ldo = [{"p": r.p, "ldo": r.value, "so": oil_saturation_from_ldo(r.value, i.swi)}
           for r in sorted(i.ldo, key=lambda r: -r.p)]
    peak = max(ldo, key=lambda r: r["ldo"]) if ldo else None
    return {"cce": cce, "cvd": cvd, "ldo": ldo, "max_ldo": peak}


# --------------------------------------------------------------------------------------
# Published data used for the checks and as examples
# --------------------------------------------------------------------------------------

T32 = [  # psig, relative volume, density gm/cc (None where not printed), Y-function printed
    (6500, 0.9371, 0.6919, None), (6000, 0.9422, 0.6882, None), (5500, 0.9475, 0.6843, None),
    (5000, 0.9532, 0.6803, None), (4500, 0.9592, 0.6760, None), (4000, 0.9657, 0.6714, None),
    (3500, 0.9728, 0.6665, None), (3000, 0.9805, 0.6613, None), (2500, 0.9890, 0.6556, None),
    (2400, 0.9909, 0.6544, None), (2300, 0.9927, 0.6531, None), (2200, 0.9947, 0.6519, None),
    (2100, 0.9966, 0.6506, None), (2000, 0.9987, 0.6493, None), (1936, 1.0000, 0.6484, None),
    (1930, 1.0014, None, None), (1928, 1.0018, None, None), (1923, 1.0030, None, None),
    (1918, 1.0042, None, None), (1911, 1.0058, None, None), (1878, 1.0139, None, None),
    (1808, 1.0324, None, None), (1709, 1.0625, None, 2.108), (1600, 1.1018, None, 2.044),
    (1467, 1.1611, None, 1.965), (1313, 1.2504, None, 1.874), (1161, 1.3694, None, 1.784),
    (1035, 1.5020, None, 1.710), (782, 1.9283, None, 1.560), (600, 2.4960, None, 1.453),
    (437, 3.4464, None, 1.356),
]
SMOOTHED = {1930: 1.0014, 1928: 1.0018, 1923: 1.0030, 1918: 1.0042, 1911: 1.0058, 1878: 1.0139, 1808: 1.0324,
            1709: 1.0630, 1600: 1.1028, 1467: 1.1626, 1313: 1.2532, 1161: 1.3741, 1035: 1.5091,
            782: 1.9458, 600: 2.5328, 437: 3.5290}
T33 = [(6500, 6000, 10.73), (6000, 5500, 11.31), (5500, 5000, 11.96), (5000, 4500, 12.70), (4500, 4000, 13.57),
       (4000, 3500, 14.61), (3500, 3000, 15.86), (3000, 2500, 17.43), (2500, 2000, 19.47), (2000, 1936, 20.79)]
# psig, Rsd, Bod, Btd, density, z, Bg ft3/scf, incremental gas gravity
T34 = [
    (1700, 841, 1.679, 1.846, 0.6577, 0.864, 0.01009, 0.885), (1500, 766, 1.639, 1.982, 0.6650, 0.869, 0.01149, 0.894),
    (1300, 693, 1.600, 2.171, 0.6720, 0.876, 0.01334, 0.901), (1100, 622, 1.563, 2.444, 0.6790, 0.885, 0.01591, 0.909),
    (900, 551, 1.525, 2.862, 0.6863, 0.898, 0.01965, 0.927), (700, 479, 1.486, 3.557, 0.6944, 0.913, 0.02559, 0.966),
    (500, 400, 1.440, 4.881, 0.7039, 0.932, 0.03626, 1.051), (300, 309, 1.382, 8.138, 0.7161, 0.955, 0.06075, 1.230),
    (185, 242, 1.335, 13.302, 0.7256, 0.970, 0.09727, 1.423), (120, 195, 1.298, 20.439, 0.7328, 0.979, 0.14562, 1.593),
]
BIG_BUTTE = dict(t_f=247.0, pb=1936.0, rho_sat=0.6484, rsdb=933.0, bodb=1.730, rsfb=646.0, bofb=1.527)
# Table 3-7: psig, Rs, Bo
T37 = [(6500, 646, 1.431), (6000, 646, 1.439), (5500, 646, 1.447), (5000, 646, 1.456), (4500, 646, 1.465),
       (4000, 646, 1.475), (3500, 646, 1.486), (3000, 646, 1.497), (2500, 646, 1.510), (2400, 646, 1.513),
       (2300, 646, 1.516), (2200, 646, 1.519), (2100, 646, 1.522), (2000, 646, 1.525),
       (1700, 564, 1.482), (1500, 498, 1.446), (1300, 434, 1.412), (1100, 371, 1.379), (900, 309, 1.346),
       (700, 244, 1.311), (500, 175, 1.271), (300, 95, 1.220), (185, 36, 1.178), (120, None, 1.146)]
# Example 3-6, new saturation pressure 2500: psig, old, new
EX36 = [(6500, 0.9371, 0.9448), (6000, 0.9422, 0.9517), (5000, 0.9532, 0.9655), (4000, 0.9657, 0.9793),
        (3000, 0.9805, 0.9931), (2000, 0.9987, 1.1096), (1936, 1.0000, 1.1299), (1911, 1.0058, 1.1384),
        (1808, 1.0324, 1.1767), (1600, 1.1018, 1.1018), (600, 2.4960, 2.4960), (437, 3.4404, 3.4404)]
# Table 3-5 (Moses): sep psig, T, GOR stage 1, GOR stock tank, API, Bofb, printed total
T35 = [(50, 75, 737, 41, 40.5, 1.481, 778), (100, 75, 676, 92, 40.7, 1.474, 768),
       (200, 75, 602, 178, 40.4, 1.483, 780), (300, 75, 549, 246, 40.1, 1.495, 795)]
GPM_EXAMPLE = [  # name, y, M, specific gravity as liquid, printed GPM
    ("Ethane", 0.1163, 30.070, 0.35619, 1.069), ("Propane", 0.0597, 44.097, 0.50699, 1.676),
    ("iso-Butane", 0.0121, 58.123, 0.56287, 0.403), ("n-Butane", 0.0214, 58.123, 0.58401, 0.688),
    ("iso-Pentane", 0.0099, 72.150, 0.63112, 0.284), ("n-Pentane", 0.0077, 72.150, 0.63112, 0.284),
    ("Hexanes", 0.0160, 86.177, 0.66383, 0.670), ("Heptanes-plus", 0.1075, 185.0, 0.809, 7.936),
]
T39 = [(8100, 0.8733, 1.484), (7800, 0.8806, 1.441), (7500, 0.8880, 1.397), (7000, 0.9036, 1.327),
       (6500, 0.9195, 1.254), (6000, 0.9397, 1.184), (5511, 0.9641, 1.116), (5309, 0.9764, 1.089),
       (5100, 0.9909, 1.061), (5000, 0.9979, 1.048)]
T39_ALL = [(8100, 0.8733), (7800, 0.8806), (7500, 0.8880), (7000, 0.9036), (6500, 0.9195), (6000, 0.9397),
           (5511, 0.9641), (5309, 0.9764), (5100, 0.9909), (5000, 0.9979), (4968, 1.0), (4905, 1.0057),
           (4800, 1.0155), (4600, 1.0369), (4309, 1.0725), (4000, 1.1177), (3600, 1.1938), (3200, 1.2970),
           (2830, 1.4268), (2400, 1.6423), (2010, 1.9312), (1600, 2.4041), (1230, 3.1377), (1000, 3.8780),
           (861, 4.5249), (770, 5.0719)]
T310 = [(4300, 7.021, 0.972), (3500, 17.957, 0.897), (2800, 30.268, 0.845), (2000, 46.422, 0.788),
        (1300, 61.745, 0.720), (700, 75.172, 0.603)]          # psig, cumulative percent produced, two-phase z
T311 = [(4968, 0.0), (4905, 19.3), (4800, 25.0), (4600, 29.9), (4300, 33.1), (3500, 34.4), (2800, 34.1),
        (2000, 32.5), (1300, 30.2), (700, 27.3), (0, 21.8)]
NAMELESS = dict(pd=4968.0, zd=1.043)

# Table 3-12, the problem set (no published solution)
MTECH = dict(
    t_f=260.0, pb=2051.0, pb_new=2500.0, rho_sat=0.5989, rsdb=1004.0, bodb=1.808,
    cce=[(5000, 0.9460), (4500, 0.9530), (4000, 0.9607), (3500, 0.9691), (3000, 0.9785), (2500, 0.9890),
         (2300, 0.9938), (2200, 0.9962), (2100, 0.9987), (2051, 1.0000), (2047, 1.0010), (2041, 1.0025),
         (2024, 1.0069), (2002, 1.0127), (1933, 1.0320), (1843, 1.0602), (1742, 1.0966), (1612, 1.1524),
         (1467, 1.2299), (1297, 1.3431), (1102, 1.5325), (862, 1.8992), (653, 2.4711), (482, 3.4050)],
    dl=[(1900, 930, 1.764, 0.880), (1700, 838, 1.708, 0.884), (1500, 757, 1.660, 0.887), (1300, 678, 1.612, 0.892),
        (1100, 601, 1.566, 0.899), (900, 529, 1.521, 0.906), (700, 456, 1.476, 0.917), (500, 379, 1.424, 0.933),
        (300, 291, 1.362, 0.955), (170, 223, 1.309, 0.974)],
    separator=[(200, 71, 490, 223, 48.2, 1.549, 713), (100, 72, 566, 127, 48.6, 1.529, 693),
               (50, 71, 632, 54, 48.6, 1.532, 686), (25, 70, 682, 25, 48.4, 1.558, 707)],
)


def _row(label, published, value, digits=4, note=""):
    """digits is the number of decimals printed in the source. A row matches when the difference is within one
    unit of the last printed digit or within 0.1 percent."""
    diff = None if published is None or value is None else value - published
    ok = None
    if diff is not None:
        ok = abs(diff) <= 1.0001 * 10 ** -digits or (published != 0 and abs(diff / published) <= 0.001)
    return {"label": label, "published": published, "tool": value, "diff": diff, "digits": digits, "ok": ok, "note": note}


def lab_checks():
    """Published against this tool. Each section is a table of rows plus notes on printed-text decisions."""
    out = []
    bb = BIG_BUTTE

    # Example 3-1
    s = [_row("Density at 4,000 psi (gm/cc)", 0.6714, density_above_pb(bb["rho_sat"], 0.9657)),
         _row("Density at 6,500 psi (gm/cc)", 0.6919, density_above_pb(bb["rho_sat"], 0.9371))]
    worst = max(abs(density_above_pb(bb["rho_sat"], v) - d) for p, v, d, _ in T32 if d and p > bb["pb"])
    out.append({"title": "Density above the bubble point (Example 3-1)", "rows": s,
                "notes": [f"All {sum(1 for r in T32 if r[2] and r[0] > bb['pb'])} printed densities above the bubble point reproduce from "
                          f"the saturation density and the relative volume. Largest difference {worst:.4f} gm/cc."]})

    # Y-function and smoothing
    ys = [(p, y, y_function(bb["pb"], p, v)) for p, v, _, y in T32 if y]
    fit_a, fit_b = fit_line([p for p, v, _, y in T32 if y], [y_function(bb["pb"], p, v) for p, v, _, y in T32 if y])
    s = [_row(f"Y-function at {p} psig", y, calc, 3) for p, y, calc in ys]
    s += [_row("Intercept a", 1.0981, fit_a, 3), _row("Slope b", 0.000591, fit_b, 6)]
    err = max(abs(vrel_from_y(bb["pb"], p, 1.0981, 0.000591) - v) for p, v in SMOOTHED.items())
    s += [_row("Largest difference in smoothed relative volume, 16 rows (Eq. 3-5 with the printed a and b)", None, err, 4)]
    out.append({"title": "Y-function and smoothed relative volume (Example 3-2)", "rows": s,
                "notes": ["Printed Y-function values reproduce only with 14.7 psi added to p in the denominator of Eq. 3-3. "
                          "Without it the value at 1,709 psig is 2.125 against 2.108 printed.",
                          "The straight line is fitted against gauge pressure. The smoothed table reproduces with gauge pressure in Eq. 3-5.",
                          "Example 3-5 uses a relative volume of 1.2579 at 1,300 psi. It reproduces with 14.7 added to p in both places "
                          f"of Eq. 3-5 ({vrel_from_y(bb['pb'], 1300, 1.0981, 0.000591, 14.7):.4f}). With gauge pressure it is "
                          f"{vrel_from_y(bb['pb'], 1300, 1.0981, 0.000591):.4f}."]})

    # Compressibility
    vmap = {p: v for p, v, _, _ in T32}
    s = []
    for hi, lo, pub in T33:
        s.append(_row(f"co {hi} to {lo} psig (1e-6 per psi)", pub,
                      compressibility_interval(vmap[hi], vmap[lo], hi, lo) * 1e6, 2))
    ex = compressibility_interval(vmap[2500], vmap[2000], 2500, 2000) * 1e6
    out.append({"title": "Average compressibility above the bubble point (Eq. 3-7, Example 3-4)", "rows": s,
                "notes": [f"Example 3-4 prints 19.43e-6 for 2,500 to 2,000 psi and Table 3-3 prints 19.47e-6. From the printed relative volumes this tool gives {ex:.2f}e-6.",
                          "Table 3-3 differs from the printed relative volumes by up to 2 percent, most on the short last interval (20.31 against 20.79), so it was probably computed from unrounded laboratory values.",
                          "Example 3-3 reads a slope of -14.92e-6 from a graph and gets 15.23e-6 at 3,000 psi. A central difference on Table 3-2 "
                          f"gives {compressibility_slope(0.9805, (0.9890 - 0.9728) / (2500 - 3500)) * 1e6:.2f}e-6, so the graphical value is not reproducible from the table."]})

    # Differential liberation
    s = []
    for p, rsd, bod, btd_pub, rho, z, bg_pub, gg in T34:
        bg = bg_from_z(z, p + 14.7, bb["t_f"] + 460)
        s.append(_row(f"Bg at {p} psig (ft3/scf)", bg_pub, bg, 5))
    for p, rsd, bod, btd_pub, rho, z, bg_pub, gg in T34:
        bg = bg_from_z(z, p + 14.7, bb["t_f"] + 460)
        s.append(_row(f"Btd at {p} psig (bbl/STB)", btd_pub, btd(bod, bb["rsdb"], rsd, bg), 3))
    out.append({"title": "Differential liberation, gas formation volume factor and relative total volume (Eqs. 3-9, 3-11)", "rows": s,
                "notes": ["Eq. 3-9 labels Bg as bbl/scf while Eq. 3-11 and Table 3-4 give ft3/scf. The ft3/scf value is divided by 5.615 inside Eq. 3-9, which reproduces the printed Btd.",
                          "Pressure in Eq. 3-11 is gauge plus 14.7 with standard conditions of 14.73 psia and 520 degR."]})

    # Adjustment to separator conditions
    s = []
    dlmap = {r[0]: r for r in T34}
    for p, rs_pub, bo_pub in T37:
        if p > bb["pb"]:
            s.append(_row(f"Bo at {p} psig", bo_pub, bo_above_pb(bb["bofb"], vmap[p]), 3))
    for p, rs_pub, bo_pub in T37:
        if p in dlmap:
            _, rsd, bod, *_ = dlmap[p]
            s.append(_row(f"Bo at {p} psig", bo_pub, bo_below_pb(bb["bofb"], shrinkage(bod, bb["bodb"])), 3))
            if rs_pub is not None:
                s.append(_row(f"Rs at {p} psig", float(rs_pub), rs_adjusted(bb["rsfb"], bb["rsdb"], rsd, bb["bofb"], bb["bodb"]), 0))
    s += [_row("Example 3-5, Bo at 4,000 psi", 1.4746, bo_above_pb(1.527, 0.9657), 4),
          _row("Example 3-5, Bo at 1,100 psi", 1.379, bo_below_pb(1.527, 1.563 / 1.730), 3),
          _row("Example 3-5, Rs at 1,100 psi", 371.0, rs_adjusted(646, 933, 622, 1.527, 1.730), 0),
          _row("Example 3-5, Bt from Eq. 3-18 at 1,300 psi", 1.921, bt_from_vrel(1.527, 1.2579), 3),
          _row("Example 3-5, Bt from Eq. 3-19 at 1,300 psi", 1.916, bt_from_btd(2.171, 1.527, 1.73), 3)]
    out.append({"title": "Adjustment of differential data to separator conditions (Eqs. 3-14 to 3-19, Example 3-5, Table 3-7)", "rows": s,
                "notes": ["Example 3-5 step 2 prints 1.57 in place of 1.527. The product 0.9657 x 1.527 is 1.4746, which matches the printed result.",
                          "Printed Rs values in Table 3-7 differ from the calculation by up to 1.3 scf/STB (for example 564.8 against 564 printed, 245.3 against 244). Several look truncated and the table was probably computed from unrounded laboratory values.",
                          "Rsfb is printed as 646 and the separator rows add to 645 (632 + 13). The printed 646 is used."]})

    # New bubble point
    s = []
    for p, old, new in EX36:
        pub = new
        if p >= 2500:
            calc = vrel_above_new_pb(2500, p, -0.0000138)
        else:
            calc = vrel_from_y(2500, p, 1.0981, 0.000591)
        note = "printed value equals the old value" if abs(old - new) < 1e-9 else ""
        s.append(_row(f"New relative volume at {p} psig", pub, calc, 4, note))
    s += [_row("Example 3-7, Rsfb at the new bubble point", 785.0, rsfb_new(646, 1134, 933), 0),
          _row("Example 3-7, separator GOR", 772.0, rsfb_new(646, 1134, 933) - 13, 0),
          _row("Example 3-7, Bofb at the new bubble point", 1.777, bofb_new(1.527, 2.013, 1.730), 3)]
    out.append({"title": "Correcting to a new bubble point (Eqs. 3-20 to 3-23, Examples 3-6 and 3-7)", "rows": s,
                "notes": ["Eq. 3-21 reproduces the printed values above the new bubble point. Eq. 3-20 reproduces them from 2,000 to 1,808 psig with gauge pressure.",
                          "For 1,600, 600 and 437 psig the printed new values equal the old values. Eq. 3-20 gives 1.2752, 3.1798 and 4.4805. The printed rows look like copies of the old column.",
                          "The solution text cites Eqs. 3-30 and 3-31, which should be 3-20 and 3-21. The example states a bubble point of 1,930 psig while the table uses 1,936.",
                          "The new differential values (Bodb 2.013, Rsdb 1,134) come from a graphical extrapolation. This tool's numerical version of that procedure gives "
                          "1,136.5 for Rsdb, close to the printed value, and 1.838 for Bodb against 2.013 printed. The Bod extrapolation is not reproduced, so the new values are inputs to Eqs. 3-22 and 3-23."]})

    # Separator tests
    s = []
    for sp, t, g1, g2, api, bofb, pub in T35:
        s.append(_row(f"Total GOR at {sp} psig separator", float(pub), float(g1 + g2), 0))
    best = min(T35, key=lambda r: r[5])
    s.append(_row("Optimum separator pressure (psig, minimum Bofb)", 100.0, float(best[0]), 0))
    out.append({"title": "Separator tests (Eqs. 3-12 and 3-13, Table 3-5)", "rows": s,
                "notes": ["Total GOR is the sum of the separator and stock tank gas-oil ratios, both per barrel of stock tank oil.",
                          "The text calls the optimum separator pressure 100 psia while the table lists 100 psig."]})

    # Gas condensate
    s = []
    for name, y, m, g, pub in GPM_EXAMPLE:
        s.append(_row(f"GPM, {name}", pub, gpm_component(y, m, g), 3,
                      "printed cell is inconsistent with the printed total" if name in ("Ethane", "iso-Pentane") else ""))
    total = sum(gpm_component(y, m, g) for _, y, m, g, _ in GPM_EXAMPLE)
    s.append(_row("GPM, total (all components)", 15.20, total, 2))
    s.append(_row("GPM constant 11.173 x 15.025 / 520", 0.3228, gpm_factor(), 4))
    out.append({"title": "Gas plant products (Eq. 3-24, Example 3-8)", "rows": s,
                "notes": ["Ethane is printed as 1.069 gal/Mscf. Assuming full recovery gives 3.17. The printed total of 15.20 only adds up with 3.17, so the total assumes 100% plant efficiency as stated and the ethane cell does not.",
                          "iso-Pentane is printed as 0.284, the same as n-Pentane. The calculation gives 0.365, which is also what Table 3-8 prints (0.369) and what the total needs.",
                          "Table 3-8 prints 7.944 for heptanes-plus and the example 7.936. The example value reproduces."]})

    s = []
    for p, v, zpub in T39:
        s.append(_row(f"z at {p} psig", zpub, z_from_cce(1.043, p + 15.025, 4968 + 15.025, v), 3))
    s += [_row("Example 3-9, z at 6,000 psi", 1.184, z_from_cce(1.043, 6015.025, 4983.025, 0.9397), 3),
          _row("Example 3-9, z at 8,100 psi", 1.483, z_from_cce(1.043, 8115.025, 4983.025, 0.8733), 3)]
    out.append({"title": "Gas z-factor from constant composition expansion (Eq. 3-26, Example 3-9)", "rows": s,
                "notes": ["The calculation adds 15.025 psi, the base pressure of the laboratory report. The example text says 8,000 psi but the calculation uses 8,100 psig.",
                          "Differences of 0.001 come from rounding of the printed relative volumes."]})

    s = []
    for p, gp, zpub in T310:
        s.append(_row(f"Two-phase z at {p} psig", zpub, z_two_phase(1.043, 4968 + 15.025, p + 15.025, gp / 100.0), 3))
    s.append(_row("Example 3-10, two-phase z at 2,000 psi", 0.787, z_two_phase(1.043, 4968 + 15.025, 2015.025, 0.46422), 3))
    out.append({"title": "Two-phase compressibility factor (Eq. 3-31, Example 3-10, Table 3-10)", "rows": s,
                "notes": ["Example 3-10 prints 0.787 and Table 3-10 prints 0.788 for the same pressure. The calculation gives 0.787."]})
    return out


def example_data():
    """Inputs for the example buttons on the page."""
    bb = BIG_BUTTE
    return {
        "oil": {
            "cce": {"psat": bb["pb"], "rho_sat": bb["rho_sat"], "points": [{"p": p, "vrel": v} for p, v, _, _ in T32]},
            "dl": {"t_f": bb["t_f"], "rsdb": bb["rsdb"], "bodb": bb["bodb"],
                   "rows": [{"p": p, "rsd": rsd, "bod": bod, "z": z} for p, rsd, bod, _, _, z, _, _ in T34]},
            "adjust": {"pb": bb["pb"], "rsdb": bb["rsdb"], "bodb": bb["bodb"], "rsfb": bb["rsfb"], "bofb": bb["bofb"],
                       "dl": [{"p": p, "rsd": rsd, "bod": bod} for p, rsd, bod, *_ in T34],
                       "cce": [{"p": p, "vrel": v} for p, v, _, _ in T32],
                       "btd": [{"p": p, "vrel": b} for p, _, _, b, *_ in T34]},
            "separator": {"tests": [{"pressure": sp, "temperature": t, "gor_separator": g1, "gor_stock_tank": g2,
                                     "api": api, "bofb": bofb} for sp, t, g1, g2, api, bofb, _ in T35]},
            "new_pb": {"psat_old": bb["pb"], "psat_new": 2500.0, "a": 1.0981, "b": 0.000591, "slope": -0.0000138,
                       "pressures": [6500, 6000, 5000, 4000, 3000, 2000, 1911, 1808],
                       "rsfb_old": 646.0, "rsdb_old": 933.0, "rsdb_new": 1134.0,
                       "bofb_old": 1.527, "bodb_old": 1.730, "bodb_new": 2.013, "stock_tank_gor": 13.0},
        },
        "oil_problem": {
            "cce": {"psat": MTECH["pb"], "rho_sat": MTECH["rho_sat"], "points": [{"p": p, "vrel": v} for p, v in MTECH["cce"]]},
            "dl": {"t_f": MTECH["t_f"], "rsdb": MTECH["rsdb"], "bodb": MTECH["bodb"],
                   "rows": [{"p": p, "rsd": rsd, "bod": bod, "z": z} for p, rsd, bod, z in MTECH["dl"]]},
            "separator": {"tests": [{"pressure": sp, "temperature": t, "gor_separator": g1, "gor_stock_tank": g2,
                                     "api": api, "bofb": bofb} for sp, t, g1, g2, api, bofb, _ in MTECH["separator"]]},
        },
        "gas": {
            "gpm": {"components": [{"name": n, "y": y, "m": m, "gamma_oi": g} for n, y, m, g, _ in GPM_EXAMPLE]},
            "cond": {"pd": NAMELESS["pd"], "zd": NAMELESS["zd"],
                     "cce": [{"p": p, "vrel": v} for p, v in T39_ALL],
                     "cvd": [{"p": p, "value": g} for p, g, _ in T310],
                     "ldo": [{"p": p, "value": v} for p, v in T311]},
        },
    }
