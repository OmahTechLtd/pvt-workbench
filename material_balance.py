"""Material balance for oil reservoirs.

Drive indexes, the general material balance equation solved for the initial oil in place, the water influx or the
gas cap ratio, the straight line method of Havlena and Odeh for the volumetric, saturated, gas cap and pot aquifer
cases, oil and gas saturations with the field relative permeability ratio, the Tracy form, and the average pressure
procedure.

Source for the equations and the worked examples: Ahmed, Reservoir Engineering Handbook, 5th ed., pp. 751 to 818.

Units. Pressure psi, Bo and Bt bbl/STB, Rs scf/STB, Bg bbl/scf, volumes in STB, scf and bbl unless a scale is given.
The request models carry a scale for each cumulative volume so the data can be entered the way it is usually
reported (MSTB, MMscf and so on).
"""
from typing import List, Optional

import numpy as np
from fastapi import HTTPException
from pydantic import BaseModel

from lab_pvt import _row, fit_line

BBL_FT3 = 5.615

# Recovery ranges quoted for each drive mechanism (percent of the initial oil in place).
DRIVES = [
    {"drive": "Rock and liquid expansion", "recovery": "3 to 5", "note": "Undersaturated oil, no water influx"},
    {"drive": "Solution gas (depletion)", "recovery": "5 to 30", "note": "Gas comes out of solution as pressure falls"},
    {"drive": "Gas cap", "recovery": "20 to 40", "note": "Expansion of free gas above the oil"},
    {"drive": "Water drive", "recovery": "35 to 75", "note": "Aquifer influx supports the pressure"},
    {"drive": "Gravity drainage", "recovery": "Can exceed 80", "note": "Depends on the production rate staying below the critical rate"},
]


# --------------------------------------------------------------------------------------
# Equations
# --------------------------------------------------------------------------------------

def bt_from(bo, rs, bg, rsi):
    """Two-phase formation volume factor, Bt = Bo + (Rsi - Rs) Bg."""
    return bo + (rsi - rs) * bg


def underground_withdrawal(np_, rp, wp, bw, bo=None, rs=None, bg=None, bt=None, rsi=None):
    """F. With Bt known: Np [Bt + (Rp - Rsi) Bg] + Wp Bw. Otherwise Np [Bo + (Rp - Rs) Bg] + Wp Bw."""
    if bt is not None:
        return np_ * (bt + (rp - rsi) * bg) + wp * bw
    return np_ * (bo + (rp - rs) * bg) + wp * bw


def oil_expansion(bo=None, rs=None, bg=None, boi=None, rsi=None, bt=None, bti=None):
    """Eo = Bt - Bti, or (Bo - Boi) + (Rsi - Rs) Bg."""
    if bt is not None:
        return bt - (bti if bti is not None else boi)
    return (bo - boi) + (rsi - rs) * bg


def gas_cap_expansion(bg, bgi, boi):
    """Eg = Boi (Bg/Bgi - 1)."""
    return boi * (bg / bgi - 1.0)


def rock_water_expansion(boi, m, swi, cw, cf, dp):
    """Ef,w = Boi (1 + m) [(Swi cw + cf) / (1 - Swi)] dp. The printed form of Eq. 11-31 shows (1 + Sw) once; the other forms
    print (1 - Swi) and that is what the expression needs."""
    return boi * (1.0 + m) * (swi * cw + cf) / (1.0 - swi) * dp


def solve_n(f, eo, eg, efw, m, we=0.0):
    """General equation F = N (Eo + m Eg + Ef,w) + We solved for N."""
    d = eo + m * eg + efw
    if d == 0:
        raise HTTPException(422, "The expansion term is zero, so N cannot be found at this point. Use a point at a lower pressure.")
    return (f - we) / d


def solve_we(f, n, eo, eg, efw, m):
    """The same equation solved for the cumulative water influx."""
    return f - n * (eo + m * eg + efw)


def solve_m(f, n, eo, eg, efw, we):
    """The same equation solved for the gas cap ratio m."""
    if n == 0 or eg == 0:
        raise HTTPException(422, "N and the gas expansion term must be non-zero to solve for m.")
    return (f - n * (eo + efw) - we) / (n * eg)


def drive_indexes(n, m, np_, rp, wp, bw, bt, bti, bg, bgi, rsi, we, boi, swi, cw, cf, dp):
    """Eqs. 11-18 to 11-23. A is the total underground withdrawal without the water term."""
    a = np_ * (bt + (rp - rsi) * bg)
    ddi = n * (bt - bti) / a
    sdi = n * m * bti * (bg / bgi - 1.0) / a
    wdi = (we - wp * bw) / a
    edi = n * bti * (1.0 + m) * (swi * cw + cf) / (1.0 - swi) * dp / a
    return {"a": a, "ddi": ddi, "sdi": sdi, "wdi": wdi, "edi": edi, "sum": ddi + sdi + wdi + edi}


def oil_saturation(n_p, n, bo, boi, swi):
    """So = (1 - Swi)(1 - Np/N) Bo/Boi."""
    return (1.0 - swi) * (1.0 - n_p / n) * bo / boi


def drainage_oil_volume(re_ft, h_ft, phi, swi, boi):
    """N = pi re^2 h phi (1 - Swi) / (5.615 Boi), in STB."""
    return np.pi * re_ft ** 2 * h_ft * phi * (1.0 - swi) / (BBL_FT3 * boi)


def relative_permeability_ratio(gor, rs, mu_ratio_o_over_g, bg, bo):
    """krg/kro = (GOR - Rs) (mu_g Bg) / (mu_o Bo)."""
    return (gor - rs) * bg / (mu_ratio_o_over_g * bo)


def tracy_functions(bo, rs, bg, boi, rsi, bgi, m):
    """Eqs. 11-54 to 11-57."""
    den = (bo - boi) + (rsi - rs) * bg + m * boi * (bg / bgi - 1.0)
    if den == 0:
        raise HTTPException(422, "Tracy's denominator is zero at the initial pressure. Use a lower pressure.")
    return {"den": den, "phi_o": (bo - rs * bg) / den, "phi_g": bg / den, "phi_w": 1.0 / den}


def tracy_n(np_, gp, wp, we, bw, phi_o, phi_g, phi_w):
    """Eq. 11-53."""
    return np_ * phi_o + gp * phi_g + (wp * bw - we) * phi_w


# --------------------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------------------

class Fluid(BaseModel):
    pi: float
    boi: float
    rsi: Optional[float] = None
    bgi: Optional[float] = None
    bti: Optional[float] = None
    swi: float = 0.0
    cw: float = 0.0
    cf: float = 0.0
    bw: float = 1.0


class Row(BaseModel):
    p: float
    bo: Optional[float] = None
    rs: Optional[float] = None
    bg: Optional[float] = None
    bt: Optional[float] = None
    n_p: float = 0.0
    g_p: Optional[float] = None     # cumulative gas, or Rp when gas_basis is "rp"
    w_p: float = 0.0
    f: Optional[float] = None       # F, Eo and Eg can be given directly instead of the production and PVT columns
    eo: Optional[float] = None
    eg: Optional[float] = None


class SeriesIn(BaseModel):
    case: str                       # volumetric_undersaturated, saturated, gas_cap, water_drive_pot
    fluid: Fluid
    rows: List[Row]
    m: Optional[float] = None       # known gas cap ratio, used by the gas cap case and the saturated case
    include_efw: bool = False
    gas_basis: str = "gp"           # "gp" cumulative gas, "rp" cumulative gas-oil ratio
    np_scale: float = 1.0
    gp_scale: float = 1.0
    wp_scale: float = 1.0


CASES = ["volumetric_undersaturated", "saturated", "gas_cap", "water_drive_pot"]


def _terms(fl: Fluid, r: Row, i: SeriesIn, m_for_efw: float):
    """Returns F, Eo, Eg, Ef,w for one row."""
    if r.f is not None:
        if r.eo is None:
            raise HTTPException(422, f"Row at {r.p} psi has F but no Eo.")
        efw = rock_water_expansion(fl.boi, m_for_efw, fl.swi, fl.cw, fl.cf, fl.pi - r.p)
        return r.f, r.eo, (r.eg or 0.0), efw
    rsi = fl.rsi
    rs = r.rs if r.rs is not None else rsi
    bg = r.bg if r.bg is not None else 0.0
    np_ = r.n_p * i.np_scale
    wp = r.w_p * i.wp_scale
    if np_ > 0 and r.g_p is not None:
        rp = r.g_p if i.gas_basis == "rp" else r.g_p * i.gp_scale / np_
    else:
        rp = rs if rs is not None else 0.0
    if r.bt is not None:
        if rsi is None:
            raise HTTPException(422, "The initial solution gas-oil ratio is needed when Bt is given.")
        f = underground_withdrawal(np_, rp, wp, fl.bw, bg=bg, bt=r.bt, rsi=rsi)
        eo = oil_expansion(bt=r.bt, bti=fl.bti, boi=fl.boi)
    else:
        if r.bo is None:
            raise HTTPException(422, f"Row at {r.p} psi needs Bo or Bt.")
        if rs is None:
            rs = 0.0
            rsi = 0.0
        f = underground_withdrawal(np_, rp, wp, fl.bw, bo=r.bo, rs=rs, bg=bg)
        eo = oil_expansion(bo=r.bo, rs=rs, bg=bg, boi=fl.boi, rsi=rsi if rsi is not None else rs)
    eg = gas_cap_expansion(bg, fl.bgi, fl.boi) if (fl.bgi and r.bg is not None) else 0.0
    efw = rock_water_expansion(fl.boi, m_for_efw, fl.swi, fl.cw, fl.cf, fl.pi - r.p)
    return f, eo, eg, efw


def series_analysis(i: SeriesIn):
    if i.case not in CASES:
        raise HTTPException(422, "Unknown case.")
    fl = i.fluid
    if len(i.rows) < 2:
        raise HTTPException(422, "At least two pressure rows are needed.")
    if i.case in ("gas_cap",) and not fl.bgi:
        raise HTTPException(422, "The gas cap case needs the initial gas formation volume factor.")
    m_efw = i.m if (i.m is not None and i.case in ("gas_cap", "saturated")) else 0.0
    use_efw = i.case == "volumetric_undersaturated" or i.include_efw
    out_rows = []
    for r in i.rows:
        if r.p >= fl.pi:
            continue
        f, eo, eg, efw = _terms(fl, r, i, m_efw)
        if not use_efw:
            efw = 0.0
        dp = fl.pi - r.p
        row = {"p": r.p, "dp": dp, "f": f, "eo": eo, "eg": eg, "efw": efw}
        out_rows.append(row)
    if len(out_rows) < 2 and i.case != "volumetric_undersaturated":
        raise HTTPException(422, "At least two rows below the initial pressure are needed.")
    if not out_rows:
        raise HTTPException(422, "No rows below the initial pressure.")

    fit = {}
    notes = []
    if i.case == "volumetric_undersaturated":
        for r in out_rows:
            r["x"], r["y"] = r["eo"] + r["efw"], r["f"]
            r["n_point"] = r["y"] / r["x"] if r["x"] else None
        xs = np.array([r["x"] for r in out_rows]); ys = np.array([r["y"] for r in out_rows])
        n = float((xs * ys).sum() / (xs * xs).sum())
        fit = {"n": n, "slope": n, "intercept": 0.0, "through_origin": True,
               "x_label": "Eo + Ef,w (bbl/STB)", "y_label": "F (bbl)"}
        notes.append("The line is forced through the origin and its slope is N. A curve instead of a line points to water influx.")
    elif i.case == "saturated":
        for r in out_rows:
            r["x"] = r["eo"] + (r["efw"] if use_efw else 0.0) + ((i.m or 0.0) * r["eg"])
            r["y"] = r["f"]
            r["n_point"] = r["y"] / r["x"] if r["x"] else None
        xs = np.array([r["x"] for r in out_rows]); ys = np.array([r["y"] for r in out_rows])
        n = float((xs * ys).sum() / (xs * xs).sum())
        fit = {"n": n, "slope": n, "intercept": 0.0, "through_origin": True,
               "x_label": "Eo" + (" + m Eg" if i.m else "") + " (bbl/STB)", "y_label": "F (bbl)"}
        notes.append("Volumetric saturated reservoir with no water influx. The values of F/Eo at each point should agree. A rising trend means water influx.")
    elif i.case == "gas_cap":
        if i.m is not None:
            for r in out_rows:
                r["x"] = r["eo"] + i.m * r["eg"] + r["efw"]
                r["y"] = r["f"]
                r["n_point"] = r["y"] / r["x"] if r["x"] else None
            xs = np.array([r["x"] for r in out_rows]); ys = np.array([r["y"] for r in out_rows])
            n = float((xs * ys).sum() / (xs * xs).sum())
            fit = {"n": n, "slope": n, "intercept": 0.0, "m": i.m, "through_origin": True,
                   "x_label": "Eo + m Eg (bbl/STB)", "y_label": "F (bbl)"}
            notes.append("With m known, F plotted against Eo + m Eg is a line through the origin and its slope is N.")
        else:
            rows2 = [r for r in out_rows if r["eo"] != 0]
            if len(rows2) < 2:
                raise HTTPException(422, "At least two rows with a non-zero Eo are needed.")
            for r in out_rows:
                r["x"] = r["eg"] / r["eo"] if r["eo"] else None
                r["y"] = r["f"] / r["eo"] if r["eo"] else None
                r["n_point"] = None
            a, b = fit_line([r["x"] for r in rows2], [r["y"] for r in rows2])
            m = b / a if a else None
            fit = {"n": a, "slope": b, "intercept": a, "m": m, "through_origin": False,
                   "x_label": "Eg/Eo", "y_label": "F/Eo (STB)"}
            notes.append("F/Eo plotted against Eg/Eo gives N as the intercept and N m as the slope. m is the slope divided by the "
                         "intercept, so it moves a lot when the points scatter.")
    else:  # water_drive_pot
        rows2 = [r for r in out_rows if r["eo"] != 0]
        if len(rows2) < 2:
            raise HTTPException(422, "At least two rows with a non-zero Eo are needed.")
        for r in out_rows:
            r["x"] = r["dp"] / r["eo"] if r["eo"] else None
            r["y"] = r["f"] / r["eo"] if r["eo"] else None
            r["n_point"] = r["y"]
        a, b = fit_line([r["x"] for r in rows2], [r["y"] for r in rows2])
        fit = {"n": a, "slope": b, "intercept": a, "k": b, "through_origin": False,
               "x_label": "Δp/Eo", "y_label": "F/Eo (STB)"}
        notes.append("Pot aquifer model, We = K Δp with the rock and water term neglected. N is the intercept and K, the aquifer constant, is the slope. "
                     "A line is a sign that the pot aquifer is a fair description.")
    xs = [r["x"] for r in out_rows if r.get("x") is not None]
    if xs:
        x0, x1 = (0.0 if fit.get("through_origin") else min(xs)), max(xs)
        fit["line"] = [{"x": x0, "y": fit["intercept"] + fit["slope"] * x0}, {"x": x1, "y": fit["intercept"] + fit["slope"] * x1}]
    return {"rows": out_rows, "fit": fit, "notes": notes}


class PointIn(BaseModel):
    solve: str                      # "n", "we" or "m"
    fluid: Fluid
    p: float
    bo: Optional[float] = None
    rs: Optional[float] = None
    bg: Optional[float] = None
    bt: Optional[float] = None
    n_p: float
    g_p: Optional[float] = None
    w_p: float = 0.0
    gas_basis: str = "gp"
    np_scale: float = 1.0
    gp_scale: float = 1.0
    wp_scale: float = 1.0
    n: Optional[float] = None       # STB
    we: Optional[float] = None      # bbl
    m: Optional[float] = None
    include_efw: bool = True


def point_balance(i: PointIn):
    if i.solve not in ("n", "we", "m"):
        raise HTTPException(422, "Solve for n, we or m.")
    fl = i.fluid
    if fl.rsi is None or fl.bgi is None:
        raise HTTPException(422, "The initial solution gas-oil ratio and gas formation volume factor are needed.")
    m_known = i.m if i.m is not None else 0.0
    row = Row(p=i.p, bo=i.bo, rs=i.rs, bg=i.bg, bt=i.bt, n_p=i.n_p, g_p=i.g_p, w_p=i.w_p)
    ser = SeriesIn(case="saturated", fluid=fl, rows=[row, row], gas_basis=i.gas_basis, np_scale=i.np_scale,
                   gp_scale=i.gp_scale, wp_scale=i.wp_scale)
    f, eo, eg, efw = _terms(fl, row, ser, m_known)
    if not i.include_efw:
        efw = 0.0
    res = {"f": f, "eo": eo, "eg": eg, "efw": efw}
    if i.solve == "n":
        if i.we is None or i.m is None:
            raise HTTPException(422, "Give We (0 if none) and m (0 if none).")
        res["n"] = solve_n(f, eo, eg, efw, i.m, i.we)
    elif i.solve == "we":
        if i.n is None or i.m is None:
            raise HTTPException(422, "Give N and m.")
        res["we"] = solve_we(f, i.n, eo, eg, efw, i.m)
    else:
        if i.n is None or i.we is None:
            raise HTTPException(422, "Give N and We.")
        res["m"] = solve_m(f, i.n, eo, eg, efw, i.we)
    n = i.n if i.n is not None else res.get("n")
    we = i.we if i.we is not None else res.get("we")
    m = i.m if i.m is not None else res.get("m")
    if n is not None and we is not None and m is not None and fl.rsi is not None and fl.bgi is not None:
        np_ = i.n_p * i.np_scale
        rp = (i.g_p if i.gas_basis == "rp" else i.g_p * i.gp_scale / np_) if (np_ > 0 and i.g_p is not None) else (i.rs or fl.rsi)
        bt = i.bt if i.bt is not None else bt_from(i.bo, i.rs if i.rs is not None else fl.rsi, i.bg or 0.0, fl.rsi)
        bti = fl.bti if fl.bti is not None else fl.boi
        idx = drive_indexes(n, m, np_, rp, i.w_p * i.wp_scale, fl.bw, bt, bti, i.bg or 0.0, fl.bgi, fl.rsi, we, fl.boi,
                            fl.swi, fl.cw, fl.cf, fl.pi - i.p)
        res["indexes"] = idx
        res["net_influx"] = we - i.w_p * i.wp_scale
    return res


class SatRow(BaseModel):
    p: float
    bo: float
    rs: float
    bg: Optional[float] = None
    n_p: float = 0.0
    gor: Optional[float] = None
    qo: Optional[float] = None      # STB/day
    qg: Optional[float] = None      # MMscf/day
    mu_ratio: Optional[float] = None  # mu_o / mu_g


class SatIn(BaseModel):
    boi: float
    swi: float
    n: Optional[float] = None
    re_ft: Optional[float] = None
    h_ft: Optional[float] = None
    phi: Optional[float] = None
    np_scale: float = 1.0
    rows: List[SatRow]


def saturation_table(i: SatIn):
    n = i.n
    if n is None:
        if None in (i.re_ft, i.h_ft, i.phi):
            raise HTTPException(422, "Give N, or the drainage radius, thickness and porosity.")
        n = drainage_oil_volume(i.re_ft, i.h_ft, i.phi, i.swi, i.boi)
    out = []
    for r in i.rows:
        so = oil_saturation(r.n_p * i.np_scale, n, r.bo, i.boi, i.swi)
        gor = r.gor if r.gor is not None else (r.qg * 1e6 / r.qo if (r.qg is not None and r.qo) else None)
        kr = None
        if gor is not None and r.bg and r.mu_ratio:
            kr = relative_permeability_ratio(gor, r.rs, r.mu_ratio, r.bg, r.bo)
        out.append({"p": r.p, "so": so, "sg": 1.0 - i.swi - so, "gor": gor, "krg_kro": kr, "n_p": r.n_p})
    return {"n": n, "rows": out}


class TracyRow(BaseModel):
    p: float
    bo: float
    rs: float
    bg: float
    n_p: float
    g_p: float
    w_p: float = 0.0
    we: float = 0.0


class TracyIn(BaseModel):
    boi: float
    rsi: float
    bgi: float
    m: float = 0.0
    bw: float = 1.0
    np_scale: float = 1.0
    gp_scale: float = 1.0
    wp_scale: float = 1.0
    rows: List[TracyRow]


def tracy_table(i: TracyIn):
    out = []
    for r in i.rows:
        t = tracy_functions(r.bo, r.rs, r.bg, i.boi, i.rsi, i.bgi, i.m)
        n = tracy_n(r.n_p * i.np_scale, r.g_p * i.gp_scale, r.w_p * i.wp_scale, r.we, i.bw, t["phi_o"], t["phi_g"], t["phi_w"])
        out.append({"p": r.p, "phi_o": t["phi_o"], "phi_g": t["phi_g"], "phi_w": t["phi_w"], "n": n})
    return {"rows": out, "notes": ["Tracy's functions go to infinity at the bubble point, so the first points below it are the most sensitive. "
                                   "Small errors in pressure or production move N a lot there. Use the later points when they agree."]}


class PvtRow(BaseModel):
    p: float
    bo: float
    rs: float
    bg: float


class AvgPIn(BaseModel):
    fluid: Fluid
    n: float                        # STB
    m: float = 0.0
    n_p: float
    g_p: float
    w_p: float = 0.0
    np_scale: float = 1.0
    gp_scale: float = 1.0
    wp_scale: float = 1.0
    pvt: List[PvtRow]


def average_pressure(i: AvgPIn):
    """Case 6. Finds the pressure at which the left side of F = N (Eo + m Eg) equals the right side."""
    fl = i.fluid
    if fl.rsi is None or fl.bgi is None:
        raise HTTPException(422, "The initial solution gas-oil ratio and gas formation volume factor are needed.")
    pv = sorted(i.pvt, key=lambda r: r.p)
    if len(pv) < 2:
        raise HTTPException(422, "At least two PVT rows are needed.")
    ps = np.array([r.p for r in pv])
    bo = np.array([r.bo for r in pv]); rs = np.array([r.rs for r in pv]); bg = np.array([r.bg for r in pv])
    np_, gp, wp = i.n_p * i.np_scale, i.g_p * i.gp_scale, i.w_p * i.wp_scale
    rp = gp / np_ if np_ > 0 else fl.rsi

    def sides(p):
        b, s, g = np.interp(p, ps, bo), np.interp(p, ps, rs), np.interp(p, ps, bg)
        lhs = np_ * (b + (rp - s) * g) + wp * fl.bw
        eo = (b - fl.boi) + (fl.rsi - s) * g
        eg = gas_cap_expansion(g, fl.bgi, fl.boi)
        return lhs, i.n * (eo + i.m * eg)

    grid = np.linspace(ps.min(), min(ps.max(), fl.pi), 41)
    table, prev, root = [], None, None
    for p in grid:
        l, r = sides(float(p))
        table.append({"p": float(p), "lhs": l, "rhs": r, "diff": l - r})
        if prev is not None and root is None and (prev["diff"] == 0 or prev["diff"] * (l - r) < 0):
            lo, hi = prev["p"], float(p)
            flo = prev["diff"]
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                lm, rm = sides(mid)
                if flo * (lm - rm) <= 0:
                    hi = mid
                else:
                    lo, flo = mid, lm - rm
            root = 0.5 * (lo + hi)
        prev = table[-1]
    notes = ["The average pressure is where the two sides of the equation cross. Between the PVT points the properties are interpolated linearly, "
             "so use PVT data at a close pressure spacing."]
    if root is None:
        notes.append("The two sides do not cross inside the pressure range of the PVT table. Check N, m and the production, or widen the PVT range.")
    return {"pressure": root, "rows": table, "notes": notes}


# --------------------------------------------------------------------------------------
# Published examples
# --------------------------------------------------------------------------------------

EX111 = dict(n=10e6, m=0.25, np_=1e6, gp=1100e6, wp=50000.0, pi=3000.0, p=2800.0, swi=0.20, cw=1.5e-6, cf=1e-6,
             bo=(1.58, 1.48), rs=(1040.0, 850.0), bg=(0.00080, 0.00092), bt=(1.58, 1.655), bw=1.0)

EX112 = dict(p=2500.0, boi=1.35, bo=1.33, rsi=600.0, rs=500.0, np_=5e6, gp=5.5e9, bw=1.0, we=3e6, wp=0.2e6,
             bgi=0.0011, bg=0.0015, v_oil=100000.0, v_gas=20000.0)

# Example 11-3. Pressure, Bo, Np (MSTB), Wp (MSTB), then the printed F (Mbbl), Eo, Ef,w (x1e-6) and Eo + Ef,w.
EX113_BASE = dict(pi=3685.0, boi=1.3102, swi=0.24, cw=3.62e-6, cf=4.95e-6, pb=1500.0, n_vol=270.6e6, n_plot=287e6)
EX113 = [
    (3685, 1.3102, 0.0, 0.0, None, None, None, None),
    (3680, 1.3104, 20.481, 0.0, 26.84, 0.0002, 50, 0.00025),
    (3676, 1.3104, 34.750, 0.0, 45.54, 0.0002, 90, 0.00029),
    (3667, 1.3105, 78.557, 0.0, 102.95, 0.0003, 180, 0.00048),
    (3664, 1.3105, 101.846, 0.0, 133.47, 0.0003, 210, 0.00051),
    (3640, 1.3109, 215.681, 0.0, 282.74, 0.0007, 450, 0.00115),
    (3605, 1.3116, 364.613, 0.0, 478.23, 0.0014, 800, 0.00220),
    (3567, 1.3122, 542.985, 0.159, 712.66, 0.0020, 1180, 0.00318),
    (3515, 1.3128, 841.591, 0.805, 1105.65, 0.0026, 1700, 0.00430),
    (3448, 1.3130, 1273.530, 2.579, 1674.72, 0.0028, 2370, 0.00517),
    (3360, 1.3150, 1691.887, 5.008, 2229.84, 0.0048, 3250, 0.00805),
    (3275, 1.3160, 2127.077, 6.500, 2805.73, 0.0058, 4100, 0.00990),
    (3188, 1.3170, 2575.330, 8.000, 3399.71, 0.0068, 4970, 0.01170),
]

# Example 11-4, relative permeability ratio. Printed values from the two pages (p. 795 and the landscape table).
EX114K = dict(re_ft=700.0, h_ft=100.0, phi=0.2, swi=0.25, n_printed=2.7786e6, boi=1.48)
EX114K_ROWS = [
    # p, Qo, Qg, Bo, Rs, Bg, muo/mug, Np (MMSTB), printed GOR, So, Sg, krg/kro
    (3600, None, None, 1.48, 1160.0, None, 4.48, 0.0, None, 0.75, 0.0, None),
    (3480, 779.92, 1.49618, 1.42, 1058.4, 0.0006376, 4.816, 0.0634532, 1918.371, 0.7032, 0.0468, 0.0802),
    (3248, 560.06, 1.63759, 1.336, 914.4, 0.000672, 5.792, 0.1656649, 2923.953, 0.6366, 0.1134, 0.1745),
    (3072, 391.33, 1.50281, 1.2888, 829.6, 0.0007048, 6.536, 0.2370831, 3840.293, 0.5974, 0.1526, 0.2519),
    (2880, 289.13, 1.28058, 1.2528, 766.4, 0.0007328, 7.48, 0.2898497, 4429.131, 0.5686, 0.1814, 0.2864),
    (2784, 304.96, 1.67928, 1.2184, 705.6, 0.0007672, 7.96, 0.3455046, 5506.593, 0.5406, 0.2094, 0.3798),
    (2608, 233.01, 1.56996, 1.1792, 632.8, 0.000812, 8.88, 0.3880289, 6737.831, 0.5141, 0.2359, 0.4734),
    (2480, 175.00, 1.38978, 1.152, 587.2, 0.000852, 9.52, 0.4199666, 7941.789, 0.4955, 0.2545, 0.5714),
    (2352, 158.50, 1.29939, 1.1272, 545.6, 0.0008968, 10.24, 0.4488938, 8198.066, 0.4789, 0.2711, 0.5946),
    (2240, 153.51, 1.24187, 1.1056, 509.6, 0.000936, 10.8, 0.476899, 8089.732, 0.4641, 0.2859, 0.5942),
]

# Example 11-4, gas cap drive. Printed columns.
EX114G = dict(pi=4415.0, rsi=975.0, bti=1.6291, bgi=0.00077, n_pub=9e6, nm_pub=3.1e7, m_pub=3.44, g_pub=66e6)
EX114G_ROWS = [
    # p, Np (MSTB), Gp (Mscf), Bt, Bg, printed Rp, F, Eo, Eg, F/Eo, Eg/Eo
    (3875, 492.5, 751.3, 1.6839, 0.00079, 1525, 2.04e6, 0.0548, 0.0529, 3.72e7, 0.96),
    (3315, 1015.7, 2409.6, 1.7835, 0.00087, 2372, 8.77e6, 0.1540, 0.2220, 5.69e7, 1.44),
    (2845, 1322.5, 3901.6, 1.9110, 0.00099, 2950, 17.05e6, 0.2820, 0.4720, 6.00e7, 1.67),
]

# Example 11-5, pot aquifer. p, F, Eo and the printed F/Eo and dp/Eo.
EX115 = dict(pi=3500.0, n_pub=35e6, k_pub=9983.0)
EX115_ROWS = [(3488, 2.04e6, 0.0548, 37.23e6, 219.0), (3162, 8.77e6, 0.1540, 56.95e6, 2194.8), (2782, 17.05e6, 0.2820, 60.46e6, 2546.0)]

# Example 11-6, Tracy's form. The first and third tables of the example.
EX116_ROWS = [  # p, Np (MSTB), Gp (MMscf), phi_o, phi_g, printed Np phi_o (1e6), Gp phi_g (1e6), N (1e6)
    (1600, 398.0, 38.6, 36.60, 0.4000, 14.52, 15.42, 29.74),
    (1500, 1570.0, 155.8, 14.30, 0.1790, 22.45, 27.85, 50.30),
    (1100, 4470.0, 803.0, 2.10, 0.0508, 9.39, 40.79, 50.18),
]

# Practice data, a gas cap drive field (problem 5 of the source). No published solution is used for it here.
PRACTICE_GAS_CAP = dict(
    pi=3330.0, boi=1.2511, rsi=510.0, bgi=0.00087,
    rows=[(3150, 3.295, 1050.0, 1.2353, 477.0, 0.00092), (3000, 5.903, 1060.0, 1.2222, 450.0, 0.00096),
          (2850, 8.852, 1160.0, 1.2122, 425.0, 0.00101), (2700, 11.503, 1235.0, 1.2022, 401.0, 0.00107),
          (2550, 14.513, 1265.0, 1.1922, 375.0, 0.00113), (2400, 17.730, 1300.0, 1.1822, 352.0, 0.00120)],
)


def _ex111():
    e = EX111
    dp = e["pi"] - e["p"]
    rp = e["gp"] / e["np_"]
    bt, bti = e["bt"][1], e["bt"][0]
    bg, bgi = e["bg"][1], e["bg"][0]
    rsi = e["rs"][0]
    f = underground_withdrawal(e["np_"], rp, e["wp"], e["bw"], bt=bt, bg=bg, rsi=rsi)
    eo = bt - bti
    eg = bti * (bg / bgi - 1.0)
    efw = rock_water_expansion(bti, e["m"], e["swi"], e["cw"], e["cf"], dp)
    we = solve_we(f, e["n"], eo, eg, efw, e["m"])
    we_no = solve_we(f, e["n"], eo, eg, 0.0, e["m"])
    idx = drive_indexes(e["n"], e["m"], e["np_"], rp, e["wp"], e["bw"], bt, bti, bg, bgi, rsi, we, bti, e["swi"], e["cw"], e["cf"], dp)
    return {"rp": rp, "we": we, "we_no_efw": we_no, "net": we - e["wp"] * e["bw"], "idx": idx}


def _ex113_rows():
    b = EX113_BASE
    rows = []
    for p, bo, np_k, wp_k, f_pub, eo_pub, efw_pub, sum_pub in EX113:
        if np_k == 0.0:
            continue
        dp = b["pi"] - p
        f = np_k * 1e3 * bo + wp_k * 1e3 * 1.0
        eo = bo - b["boi"]
        efw = rock_water_expansion(b["boi"], 0.0, b["swi"], b["cw"], b["cf"], dp)
        rows.append((p, f, eo, efw, f_pub, eo_pub, efw_pub, sum_pub))
    return rows


def mb_checks():
    """Published against this tool. Each section is a table of rows plus notes on printed-text decisions."""
    out = []

    # Example 11-1
    r = _ex111()
    i = r["idx"]
    out.append({"title": "Water influx and drive indexes (Example 11-1)", "rows": [
        _row("Cumulative gas-oil ratio Rp (scf/STB)", 1100.0, r["rp"], 0),
        _row("Cumulative water influx We (bbl)", 411281.0, r["we"], 0),
        _row("We without the rock and fluid term (bbl)", 417700.0, r["we_no_efw"], 0),
        _row("Net water influx (bbl)", 361281.0, r["net"], 0),
        _row("Total withdrawal A (bbl)", 1710000.0, i["a"], 0),
        _row("Depletion drive index", 0.4385, i["ddi"], 4),
        _row("Segregation (gas cap) drive index", 0.3465, i["sdi"], 4),
        _row("Water drive index", 0.2112, i["wdi"], 4),
        _row("Expansion drive index", 0.0038, i["edi"], 4),
        _row("Sum of the four indexes", 1.0, i["sum"], 4),
    ], "notes": [
        "The printed solution writes (Bg - Bti) in the first bracket of the We expression. The numbers only work with (Bt - Bti), and that is what is used.",
        "The printed A is 1,710,000, the value rounded. Computed without rounding it is 1,710,200, and the indexes still agree to four decimals.",
        "Rock and fluid expansion is small here, as the source says it can be neglected when there is a gas cap."]})

    # Example 11-2
    e = EX112
    m = e["v_gas"] / e["v_oil"]
    rp = e["gp"] / e["np_"]
    eo = (e["bo"] - e["boi"]) + (e["rsi"] - e["rs"]) * e["bg"]
    eg = gas_cap_expansion(e["bg"], e["bgi"], e["boi"])
    f = underground_withdrawal(e["np_"], rp, e["wp"], 1.0, bo=e["bo"], rs=e["rs"], bg=e["bg"])
    n = solve_n(f, eo, eg, 0.0, m, e["we"])
    eo_printed = (e["boi"] - e["bo"]) + (e["rsi"] - e["rs"]) * e["bg"]
    n_printed = solve_n(f, eo_printed, eg, 0.0, m, e["we"])
    out.append({"title": "Initial oil in place from the general equation (Example 11-2)", "rows": [
        _row("Gas cap ratio m", 0.2, m, 1),
        _row("Cumulative gas-oil ratio Rp (scf/STB)", 1100.0, rp, 0),
        _row("Initial oil in place N (MMSTB), Eo = (Bo - Boi) + (Rsi - Rs) Bg", 31.14, n / 1e6, 2,
             "Correct sign of the first term."),
        _row("Initial oil in place N (MMSTB), using the printed arithmetic", 31.14, n_printed / 1e6, 2,
             "First term entered as (Boi - Bo).")],
        "notes": ["The printed substitution writes the first denominator term as (1.35 - 1.33) = +0.02. The equation has (Bo - Boi), which is -0.02. "
                  "The printed answer of 31.14 MMSTB needs the +0.02. With the sign the equation gives, N is 36.59 MMSTB. "
                  "Both are shown. The calculation here uses the equation, so the first row differs from the printed answer.",
                  "The source puts the water terms in as (We - Wp) = 3 - 0.2 MMbbl with Bw = 1.00."]})

    # Example 11-3
    b = EX113_BASE
    rows = _ex113_rows()
    s = []
    for p, f, eo, efw, f_pub, eo_pub, efw_pub, sum_pub in rows:
        s.append(_row(f"F at {p} psi (Mbbl)", f_pub, f / 1e3, 2))
    for p, f, eo, efw, f_pub, eo_pub, efw_pub, sum_pub in rows:
        s.append(_row(f"Eo at {p} psi (bbl/STB)", eo_pub, eo, 4))
    for p, f, eo, efw, f_pub, eo_pub, efw_pub, sum_pub in rows:
        s.append(_row(f"Eo + Ef,w at {p} psi", sum_pub, eo + efw, 5))
    coef = rock_water_expansion(b["boi"], 0.0, b["swi"], b["cw"], b["cf"], 1.0) * 1e6
    s.append(_row("Ef,w coefficient (x 1e-6 per psi)", 10.0, coef, 1))
    xs = np.array([r[5] + r[6] * 1e-6 for r in rows]); ys = np.array([r[4] * 1e3 for r in rows])
    n_pub_inputs = float((xs * ys).sum() / (xs * xs).sum())
    xs2 = np.array([r[2] + r[3] for r in rows]); ys2 = np.array([r[1] for r in rows])
    n_calc = float((xs2 * ys2).sum() / (xs2 * xs2).sum())
    s.append(_row("N from the printed columns, line through the origin (MMSTB)", 287.0, n_pub_inputs / 1e6, 0))
    s.append(_row("N from this tool's own terms, line through the origin (MMSTB)", 287.0, n_calc / 1e6, 0))
    s.append(_row("Volumetric estimate of N (MMSTB), for comparison", 270.6, 270.6, 1))
    out.append({"title": "Volumetric undersaturated reservoir (Example 11-3)", "rows": s, "notes": [
        "The table headings cite Equations 10-35 and 10-36. They are Equations 11-35 and 11-36 in this chapter, and that is what is used.",
        "The printed Ef,w column uses 10.0e-6 per psi. The expression gives 10.03e-6, so the last digit of some printed Ef,w values and sums differs.",
        "The source reads N = 287 MMSTB from a plotted line, so the two N rows are compared against a graphical value."]})

    # Example 11-4, relative permeability ratio
    k = EX114K
    n_k = drainage_oil_volume(k["re_ft"], k["h_ft"], k["phi"], k["swi"], k["boi"])
    s = [_row("Drainage volume N (MMSTB)", 2.7786, n_k / 1e6, 4)]
    for p, qo, qg, bo, rs, bg, mu, npm, gor_p, so_p, sg_p, kr_p in EX114K_ROWS[1:]:
        so = oil_saturation(npm * 1e6, n_k, bo, k["boi"], k["swi"])
        gor = qg * 1e6 / qo
        s.append(_row(f"GOR at {p} psia (scf/STB)", gor_p, gor, 3))
    for p, qo, qg, bo, rs, bg, mu, npm, gor_p, so_p, sg_p, kr_p in EX114K_ROWS[1:]:
        so = oil_saturation(npm * 1e6, n_k, bo, k["boi"], k["swi"])
        s.append(_row(f"So at {p} psia", so_p, so, 4))
        s.append(_row(f"Sg at {p} psia", sg_p, 1.0 - k["swi"] - so, 4))
    for p, qo, qg, bo, rs, bg, mu, npm, gor_p, so_p, sg_p, kr_p in EX114K_ROWS[1:]:
        gor = qg * 1e6 / qo
        s.append(_row(f"krg/kro at {p} psia", kr_p, relative_permeability_ratio(gor, rs, mu, bg, bo), 4))
    out.append({"title": "Saturations and relative permeability ratio (Example 11-4)", "rows": s, "notes": [
        "The printed drainage volume formula shows 200 where the thickness is 100 ft. The printed result of 2.7786 MMSTB comes from 100 ft, and that is what is used.",
        "The first page prints Bg = 0.0006376 at 3480 psia and the landscape table prints 0.000638. The first page values are used because they carry more digits.",
        "The first row (3600 psia) has no rate or Bg, so it only supplies the starting saturation."]})

    # Example 11-4, gas cap
    g = EX114G
    s = []
    cal_f, cal_eo, cal_eg = [], [], []
    for p, npk, gpk, bt, bg, rp_p, f_p, eo_p, eg_p, fe_p, ge_p in EX114G_ROWS:
        rp = gpk * 1e3 / npk
        f = underground_withdrawal(npk * 1e3, rp, 0.0, 1.0, bt=bt, bg=bg, rsi=g["rsi"])
        eo = bt - g["bti"]
        eg = gas_cap_expansion(bg, g["bgi"], g["bti"])
        s.append(_row(f"Rp at {p} psi (scf/STB)", rp_p, rp, 0))
        cal_f.append(f); cal_eo.append(eo); cal_eg.append(eg)
    for (p, npk, gpk, bt, bg, rp_p, f_p, eo_p, eg_p, fe_p, ge_p), f, eo, eg in zip(EX114G_ROWS, cal_f, cal_eo, cal_eg):
        s.append(_row(f"F at {p} psi (MMbbl), recomputed from the printed data", f_p / 1e6, f / 1e6, 2,
                      "The printed F cannot be reproduced from the printed Np, Gp, Bt and Bg."))
        s.append(_row(f"Eo at {p} psi", eo_p, eo, 4))
        s.append(_row(f"Eg at {p} psi", eg_p, eg, 4))
    xs = [r[10] for r in EX114G_ROWS]; ys = [r[9] for r in EX114G_ROWS]
    a, sl = fit_line(xs, ys)
    s.append(_row("N from a least squares line through the printed F/Eo (MMSTB)", 9.0, a / 1e6, 1))
    s.append(_row("Slope N m from the same line (x 1e7)", 3.1, sl / 1e7, 1))
    s.append(_row("m from the same line", 3.44, sl / a, 2))
    s.append(_row("G from the printed N and m (Bscf)", 66.0, 3.44 * 9e6 * g["bti"] / g["bgi"] / 1e9, 0))
    ok_pts = [(eg / eo, f / eo) for f, eo, eg in zip(cal_f, cal_eo, cal_eg)]
    a2, s2 = fit_line([p[0] for p in ok_pts], [p[1] for p in ok_pts])
    s.append(_row("N from F recomputed from the printed data (MMSTB), no printed value", None, a2 / 1e6, 1))
    s.append(_row("m from F recomputed from the printed data, no printed value", None, s2 / a2, 2))
    out.append({"title": "Gas cap drive, F/Eo against Eg/Eo (Example 11-4)", "rows": s, "notes": [
        "Using F, Eo and Eg recomputed from the printed Np, Gp, Bt and Bg, the same plot gives about 19.8 MMSTB and a gas cap ratio close to zero, which is a different answer from the printed one.",
        "The Gp column is headed Mscf. The printed Rp (1525, 2372 and 2950) only follows if Gp is in MMscf, and that is how it is used here.",
        "The printed G = 66 MMscf is a unit slip. (3.44)(9e6)(1.6291)/0.00077 is 6.55e10 scf, which is 65.5 Bscf or about 65,500 MMscf.",
        "The cumulative gas-oil ratios reproduce. The printed F values (2.04, 8.77 and 17.05 million bbl) do not follow from the printed Np, Gp, Bt, Bg and Rsi. "
        "Recomputed, F is about 1.04, 3.05 and 5.11 million bbl. The printed F and Eo columns are the same ones used in Example 11-5, so they appear to have been carried over.",
        "The printed Eg values are also higher than Boi (Bg/Bgi - 1) gives with these Bg values, by 25 percent at the first point and 1 to 5 percent at the others.",
        "The source draws a line by eye (intercept 9 MMSTB, slope 3.1e7). A least squares line through the three printed points gives a lower N and a higher m. "
        "With three points and a ratio for m, the answer moves a lot with small changes.",
        "Because of these differences, N and m from this example should be treated as an illustration of the method."]})

    # Example 11-5
    e = EX115
    s = []
    for p, f, eo, fe_p, de_p in EX115_ROWS:
        s.append(_row(f"F/Eo at {p} psi (MMSTB)", fe_p / 1e6, f / eo / 1e6, 2))
        s.append(_row(f"Δp/Eo at {p} psi", de_p, (e["pi"] - p) / eo, 1))
    a, sl = fit_line([(e["pi"] - r[0]) / r[2] for r in EX115_ROWS], [r[1] / r[2] for r in EX115_ROWS])
    s.append(_row("N, intercept of F/Eo against Δp/Eo (MMSTB)", 35.0, a / 1e6, 0))
    s.append(_row("K, slope of the same line", 9983.0, sl, 0))
    out.append({"title": "Pot aquifer (Example 11-5)", "rows": s, "notes": [
        "The source takes the line from its plot (N = 35 MMSTB and K = 9983). With three points a least squares line gives close to the same values.",
        "The three values of N = F/Eo (37, 57 and 60 MMSTB) rise with falling pressure, which is how the example identifies water influx."]})

    # Example 11-6
    s = []
    for p, npk, gpm, po, pg, npo_p, gpg_p, n_p in EX116_ROWS:
        a_ = npk * 1e3 * po / 1e6
        b_ = gpm * pg
        s.append(_row(f"Np Φo at {p} psia (million)", npo_p, a_, 2))
        s.append(_row(f"Gp Φg at {p} psia (million)", gpg_p, b_, 2))
        s.append(_row(f"N at {p} psia (MMSTB)", n_p, a_ + b_, 2))
    out.append({"title": "Tracy's form (Example 11-6)", "rows": s, "notes": [
        "Small differences in Np Φo and Gp Φg (for example 27.85 printed against 27.89 from 155.8 x 0.1790) come from rounding or typing in the printed table.",
        "The printed Np column shows 155.8 at 1500 psia, which is the gas value. The oil value in the production table is 1570 MSTB and that is used.",
        "The first row (1600 psia) does not reproduce from the printed inputs and the source itself says the first calculation is probably wrong, "
        "because it is so close to the bubble point. The last two rows agree on about 50 MMSTB."]})
    return out


def _avg_pressure_example():
    """Round trip demonstration. Example 11-4 oil properties, with the cumulative gas worked out from the equation at 2880 psia,
    so the solver should return 2880 psia. It is not a published case."""
    k = EX114K
    n = drainage_oil_volume(k["re_ft"], k["h_ft"], k["phi"], k["swi"], k["boi"])
    rows = [r for r in EX114K_ROWS if r[5] is not None]
    p, _qo, _qg, bo, rs, bg, _mu, npm = rows[3][:8]
    bgi = rows[0][5]
    eo = (bo - k["boi"]) + (1160.0 - rs) * bg
    f = n * eo
    np_ = npm * 1e6
    rp = (f / np_ - bo) / bg + rs
    return {"fluid": {"pi": 3600.0, "boi": k["boi"], "rsi": 1160.0, "bgi": bgi, "swi": 0.0, "cw": 0.0, "cf": 0.0, "bw": 1.0},
            "n": n, "m": 0.0, "n_p": np_, "g_p": rp * np_, "w_p": 0.0, "answer": p,
            "pvt": [{"p": r[0], "bo": r[3], "rs": r[4], "bg": r[5]} for r in rows]}


def example_data():
    """Inputs for the example buttons on the page."""
    e1, e2 = EX111, EX112
    b3 = EX113_BASE
    k = EX114K
    g = EX114G
    pr = PRACTICE_GAS_CAP
    return {
        "drives": DRIVES,
        "point": {
            "ex111": {"fluid": {"pi": e1["pi"], "boi": 1.58, "rsi": 1040.0, "bgi": 0.0008, "bti": 1.58, "swi": e1["swi"], "cw": e1["cw"], "cf": e1["cf"], "bw": 1.0},
                      "p": e1["p"], "bt": 1.655, "bo": 1.48, "rs": 850.0, "bg": 0.00092, "n_p": 1e6, "g_p": 1100e6, "w_p": 50000.0, "n": 10e6, "m": 0.25},
            "ex112": {"fluid": {"pi": 3000.0, "boi": 1.35, "rsi": 600.0, "bgi": 0.0011, "swi": 0.0, "cw": 0.0, "cf": 0.0, "bw": 1.0},
                      "p": 2500.0, "bo": 1.33, "rs": 500.0, "bg": 0.0015, "n_p": 5e6, "g_p": 5.5e9, "w_p": 0.2e6, "we": 3e6, "m": 0.2},
        },
        "series": {
            "volumetric": {"fluid": {"pi": b3["pi"], "boi": b3["boi"], "swi": b3["swi"], "cw": b3["cw"], "cf": b3["cf"], "bw": 1.0},
                           "rows": [{"p": p, "bo": bo, "n_p": npk, "w_p": wpk} for p, bo, npk, wpk, *_ in EX113],
                           "np_scale": 1e3, "wp_scale": 1e3, "n_vol": b3["n_vol"]},
            "gas_cap": {"fluid": {"pi": g["pi"], "boi": g["bti"], "rsi": g["rsi"], "bgi": g["bgi"], "bti": g["bti"], "swi": 0.0, "cw": 0.0, "cf": 0.0, "bw": 1.0},
                        "rows": [{"p": p, "bt": bt, "bg": bg, "n_p": npk, "g_p": gpk} for p, npk, gpk, bt, bg, *_ in EX114G_ROWS],
                        "np_scale": 1e3, "gp_scale": 1e6},
            "water_drive": {"fluid": {"pi": EX115["pi"], "boi": 1.0, "swi": 0.0, "cw": 0.0, "cf": 0.0, "bw": 1.0},
                            "rows": [{"p": p, "f": f, "eo": eo} for p, f, eo, *_ in EX115_ROWS]},
            "gas_cap_printed": {"fluid": {"pi": g["pi"], "boi": g["bti"], "rsi": g["rsi"], "bgi": g["bgi"], "swi": 0.0, "cw": 0.0, "cf": 0.0, "bw": 1.0},
                                "rows": [{"p": p, "f": f_p, "eo": eo_p, "eg": eg_p} for p, _n, _g, _bt, _bg, _rp, f_p, eo_p, eg_p, _fe, _ge in EX114G_ROWS]},
            "practice": {"fluid": {"pi": pr["pi"], "boi": pr["boi"], "rsi": pr["rsi"], "bgi": pr["bgi"], "swi": 0.0, "cw": 0.0, "cf": 0.0, "bw": 1.0},
                         "rows": [{"p": p, "bo": bo, "rs": rs, "bg": bg, "n_p": npm, "g_p": rp} for p, npm, rp, bo, rs, bg in pr["rows"]],
                         "np_scale": 1e6},
        },
        "average_pressure": _avg_pressure_example(),
        "saturation": {"boi": k["boi"], "swi": k["swi"], "re_ft": k["re_ft"], "h_ft": k["h_ft"], "phi": k["phi"],
                       "rows": [{"p": p, "bo": bo, "rs": rs, "bg": bg, "n_p": npm, "qo": qo, "qg": qg, "mu_ratio": mu}
                                for p, qo, qg, bo, rs, bg, mu, npm, *_ in EX114K_ROWS]},
    }
