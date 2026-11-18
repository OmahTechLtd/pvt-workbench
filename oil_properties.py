"""Oil gravity, compressibility, formation volume factor above the bubble point, density and total
formation volume factor, with the calculations behind the Oil Properties page.
Source for the equations: Ahmed, Reservoir Engineering Handbook, 5th ed., pp. 68-103.
Temperatures in degF. Where the source prints (T - 460) with T in degR, the degF value is used directly. Pressures in psia."""
import csv
import math
import os
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel

from rs_correlations import gas_gravity_at_100psig, api_to_sg

# ---- Gravity, pp. 68-70 ----
def api_from_sg(gamma_o):          # Eq. 2-67
    return 141.5 / gamma_o - 131.5

def sg_from_api(api):
    return 141.5 / (api + 131.5)

def sg_from_density(rho_o):        # lb/ft3 at standard conditions, p. 69
    return rho_o / 62.4

def solution_gas_gravity(rsep, gsep, rst, gst):   # Eq. 2-68
    num = sum(r * g for r, g in zip(rsep, gsep)) + rst * gst
    den = sum(rsep) + rst
    return num / den

# ---- Undersaturated oil compressibility, pp. 90-93 ----
def co_vasquez_beggs(rsb, t_f, api, gamma_gs, p):          # Eq. 2-97
    return (-1433 + 5 * rsb + 17.2 * t_f - 1180 * gamma_gs + 12.61 * api) / (1e5 * p)

def co_petrosky_farshad(rsb, t_f, api, gamma_g, p):        # Eq. 2-98
    return 1.705e-7 * rsb ** 0.6935 * gamma_g ** 0.1885 * api ** 0.3272 * t_f ** 0.6729 * p ** -0.5906

def co_mccain(p, pb, t_f, api, rsb, with_pb=True):        # Eq. 2-99 to 2-101. T in degR inside.
    t_r = t_f + 460
    if with_pb:
        a = -7.573 - 1.45 * math.log(p) - 0.383 * math.log(pb) + 1.402 * math.log(t_r) + 0.256 * math.log(api) + 0.449 * math.log(rsb)
    else:
        a = -7.633 - 1.497 * math.log(p) + 1.115 * math.log(t_r) + 0.533 * math.log(api) + 0.184 * math.log(rsb)
    return math.exp(a)

def co_below_pb(p, t_f, rs, bo, bg, gamma_g, gamma_o):
    """Eq. 2-104 (McCain, Standing derivatives). The printed form uses (T - 460) with T in degR, so t_f here."""
    r = math.sqrt(gamma_g / gamma_o)
    bracket = rs * r + 1.25 * t_f
    return (-rs / (bo * (0.83 * p + 21.75))) * (0.00014 * r * bracket ** 0.12 - bg)

# ---- Undersaturated Bo, pp. 94-95 ----
def bo_under_generic(bob, co, p, pb):                      # Eq. 2-107
    return bob * math.exp(-co * (p - pb))

def a_vb(rsb, t_f, api, gamma_gs):
    return 1e-5 * (-1433 + 5 * rsb + 17.2 * t_f - 1180 * gamma_gs + 12.61 * api)

def bo_under_vasquez_beggs(bob, p, pb, rsb, t_f, api, gamma_gs):   # Eq. 2-108
    return bob * math.exp(-a_vb(rsb, t_f, api, gamma_gs) * math.log(p / pb))

def a_pf(rsb, t_f, api, gamma_g):                           # Eq. 2-110
    return 4.1646e-7 * rsb ** 0.69357 * gamma_g ** 0.1885 * api ** 0.3272 * t_f ** 0.6729

def bo_under_petrosky_farshad(bob, p, pb, rsb, t_f, api, gamma_g, exp_p=0.4094, exp_pb=0.4094):   # Eq. 2-109
    return bob * math.exp(-a_pf(rsb, t_f, api, gamma_g) * (p ** exp_p - pb ** exp_pb))

# ---- Oil density, pp. 96-97 ----
def density_from_bo(gamma_o, rs, gamma_g, bo):              # Eq. 2-111
    return (62.4 * gamma_o + 0.0136 * rs * gamma_g) / bo

def density_standing(gamma_o, rs, gamma_g, t_f):            # Eq. 2-112, T printed in degR so (T - 460) is degF
    bo = 0.972 + 0.000147 * (rs * math.sqrt(gamma_g / gamma_o) + 1.25 * t_f) ** 1.175
    return (62.4 * gamma_o + 0.0136 * rs * gamma_g) / bo

def density_under_pb(rho_ob, co, p, pb):                    # Eq. 2-113
    return rho_ob * math.exp(co * (p - pb))

def density_under_vb(rho_ob, p, pb, rsb, t_f, api, gamma_gs):   # Eq. 2-114
    return rho_ob * math.exp(a_vb(rsb, t_f, api, gamma_gs) * math.log(p / pb))

def density_under_pf(rho_ob, p, pb, rsb, t_f, api, gamma_g, exp_p=0.4094, exp_pb=0.4094):   # Eq. 2-115. The source prints 0.4096 on p; consistency with Eq. 2-109 needs 0.4094.
    return rho_ob * math.exp(a_pf(rsb, t_f, api, gamma_g) * (p ** exp_p - pb ** exp_pb))

# ---- Total formation volume factor, pp. 98-103 ----
def bt_definition(bo, rsb, rs, bg):
    return bo + (rsb - rs) * bg

def _a_star(rs, t_f, gamma_o, gamma_g, p):
    c = 2.9 * 10 ** (-0.00027 * rs)
    return rs * t_f ** 0.5 * gamma_o ** c / gamma_g ** 0.3, c

def bt_standing(rs, t_f, gamma_o, gamma_g, p):
    base, c = _a_star(rs, t_f, gamma_o, gamma_g, p)
    log_a = math.log10(base) - (10.1 - 96.8 / (6.604 + math.log10(p)))
    return 10 ** (-5.223 - 47.4 / (-12.22 + log_a))

def bt_glaso(rs, t_f, gamma_o, gamma_g, p):
    base, c = _a_star(rs, t_f, gamma_o, gamma_g, p)
    a = base * p ** -1.1089
    la = math.log10(a)
    return 10 ** (0.080135 + 0.47257 * la + 0.17351 * la ** 2)

def bt_marhoun(rs, t_f, gamma_o, gamma_g, p):
    f = rs ** 0.644516 * gamma_g ** -1.079340 * gamma_o ** 0.724874 * (t_f + 460) ** 2.006210 * p ** -0.761910
    return 0.314693 + 0.106253e-4 * f + 0.18883e-10 * f ** 2, f

def pseudo_critical_gas(gamma_g):      # Eq. 3-18 and 3-19 as printed in Example 2-35
    return 168 + 325 * gamma_g - 12.5 * gamma_g ** 2, 667 + 15 * gamma_g - 37.5 * gamma_g ** 2

def bg_from_z(z, t_r, p):              # Eq. 3-54
    return 0.00504 * z * t_r / p


def row(name, value, unit="", note=None, measured=None):
    r = {"name": name, "value": value, "unit": unit}
    if note:
        r["note"] = note
    if measured and value is not None:
        r["error_pct"] = 100 * (value - measured) / measured
    return r


def need(d, *keys):
    miss = [k for k in keys if d.get(k) is None]
    if miss:
        raise HTTPException(422, "Missing input: " + ", ".join(miss))
    return [d[k] for k in keys]


class Inputs(BaseModel):
    api: Optional[float] = None
    gamma_o: Optional[float] = None
    rho_o_sc: Optional[float] = None
    gamma_g: Optional[float] = None
    gamma_gs: Optional[float] = None
    psep_psia: Optional[float] = None
    tsep_f: Optional[float] = None
    t_f: Optional[float] = None
    rs: Optional[float] = None
    rsb: Optional[float] = None
    p: Optional[float] = None
    pb: Optional[float] = None
    bo: Optional[float] = None
    bob: Optional[float] = None
    bg: Optional[float] = None
    z: Optional[float] = None
    co: Optional[float] = None
    rho_ob: Optional[float] = None
    measured: Optional[float] = None
    sep_rates: Optional[list[float]] = None
    sep_gravities: Optional[list[float]] = None


def _gs(i):
    if i.gamma_gs is not None:
        return i.gamma_gs
    if i.gamma_g is None or i.api is None:
        return None
    return gas_gravity_at_100psig(i.gamma_g, i.api, i.psep_psia, i.tsep_f)


def _go(i):
    if i.gamma_o is not None:
        return i.gamma_o
    if i.api is not None:
        return sg_from_api(i.api)
    if i.rho_o_sc is not None:
        return sg_from_density(i.rho_o_sc)
    return None


def compute_gravity(i: Inputs):
    out, notes = [], []
    if i.rho_o_sc is not None:
        g = sg_from_density(i.rho_o_sc)
        out += [row("Specific gravity of the oil (Eq. 2-66)", g), row("Oil gravity (Eq. 2-67)", api_from_sg(g), "°API")]
    elif i.api is not None:
        out.append(row("Specific gravity of the oil", sg_from_api(i.api)))
    elif i.gamma_o is not None:
        out.append(row("Oil gravity (Eq. 2-67)", api_from_sg(i.gamma_o), "°API"))
    if i.sep_rates and i.sep_gravities:
        if len(i.sep_rates) != len(i.sep_gravities) or len(i.sep_rates) < 2:
            raise HTTPException(422, "Give a gas-oil ratio and a gas gravity for each separator, with the stock tank last.")
        out.append(row("Solution gas gravity (Eq. 2-68)", solution_gas_gravity(i.sep_rates[:-1], i.sep_gravities[:-1], i.sep_rates[-1], i.sep_gravities[-1])))
    if not out:
        raise HTTPException(422, "Give the stock-tank oil density, the API gravity, or the separator data.")
    return {"results": out, "notes": notes}


def compute_compressibility(i: Inputs):
    rsb, t, api, gg, p = need(i.dict(), "rsb", "t_f", "api", "gamma_g", "p")
    out, notes = [], []
    gs = _gs(i)
    out.append(row("Vasquez-Beggs (Eq. 2-97)", co_vasquez_beggs(rsb, t, api, gs, p) * 1e6, "10⁻⁶ psi⁻¹", measured=i.measured and i.measured))
    out.append(row("Petrosky-Farshad (Eq. 2-98)", co_petrosky_farshad(rsb, t, api, gg, p) * 1e6, "10⁻⁶ psi⁻¹", measured=i.measured))
    out.append(row("McCain without pb (Eq. 2-100)", co_mccain(p, i.pb or 1, t, api, rsb, with_pb=False) * 1e6, "10⁻⁶ psi⁻¹", measured=i.measured))
    if i.pb:
        out.append(row("McCain with pb (Eq. 2-101)", co_mccain(p, i.pb, t, api, rsb, with_pb=True) * 1e6, "10⁻⁶ psi⁻¹", measured=i.measured))
    else:
        notes.append("Give the bubble-point pressure to add McCain's equation that uses it.")
    if i.rs is not None and i.bo and i.bg and _go(i):
        out.append(row("Below pb, Eq. 2-104", co_below_pb(p, t, i.rs, i.bo, i.bg, gg, _go(i)) * 1e6, "10⁻⁶ psi⁻¹", "Applies below the bubble point, using Rs, Bo and Bg at p.", i.measured))
    notes.append("Vasquez-Beggs, Petrosky-Farshad and the McCain equations apply above the bubble point.")
    if i.pb and p < i.pb:
        notes.append("The pressure is below the bubble point, so use the Eq. 2-104 result. The first four lines do not apply here.")
    return {"results": out, "notes": notes}


def compute_bo_above_pb(i: Inputs):
    bob, p, pb = need(i.dict(), "bob", "p", "pb")
    if p < pb:
        raise HTTPException(422, "These equations apply at or above the bubble point. Pressure is below pb.")
    out, notes = [], []
    if i.co is not None:
        out.append(row("From a known compressibility (Eq. 2-107)", bo_under_generic(bob, i.co * 1e-6, p, pb), "bbl/STB", measured=i.measured))
    if all(v is not None for v in (i.rsb, i.t_f, i.api, i.gamma_g)):
        gs = _gs(i)
        out.append(row("Vasquez-Beggs (Eq. 2-108)", bo_under_vasquez_beggs(bob, p, pb, i.rsb, i.t_f, i.api, gs), "bbl/STB", measured=i.measured))
        out.append(row("Petrosky-Farshad (Eq. 2-109)", bo_under_petrosky_farshad(bob, p, pb, i.rsb, i.t_f, i.api, i.gamma_g), "bbl/STB", measured=i.measured))
    if not out:
        raise HTTPException(422, "Give Rsb, temperature, API and gas gravity, or a compressibility.")
    return {"results": out, "notes": notes}


def compute_density(i: Inputs):
    go = _go(i)
    out, notes = [], []
    if go and i.rs is not None and i.gamma_g is not None:
        if i.bo:
            out.append(row("From Bo (Eq. 2-111)", density_from_bo(go, i.rs, i.gamma_g, i.bo), "lb/ft³", measured=i.measured))
        if i.t_f is not None:
            out.append(row("Standing (Eq. 2-112)", density_standing(go, i.rs, i.gamma_g, i.t_f), "lb/ft³", measured=i.measured))
    if i.rho_ob and i.p and i.pb and i.p >= i.pb:
        if i.co is not None:
            out.append(row("Above pb with compressibility (Eq. 2-113)", density_under_pb(i.rho_ob, i.co * 1e-6, i.p, i.pb), "lb/ft³", measured=i.measured))
        if all(v is not None for v in (i.rsb, i.t_f, i.api, i.gamma_g)):
            out.append(row("Above pb, Vasquez-Beggs (Eq. 2-114)", density_under_vb(i.rho_ob, i.p, i.pb, i.rsb, i.t_f, i.api, _gs(i)), "lb/ft³", measured=i.measured))
            out.append(row("Above pb, Petrosky-Farshad (Eq. 2-115)", density_under_pf(i.rho_ob, i.p, i.pb, i.rsb, i.t_f, i.api, i.gamma_g), "lb/ft³", measured=i.measured))
            notes.append("Eq. 2-115 is coded with the exponent 0.4094 on both pressures. The source prints 0.4096 on p, which does not match Eq. 2-109.")
    if not out:
        raise HTTPException(422, "Give gravity, Rs and gas gravity (and Bo or temperature), or the bubble-point density with p and pb.")
    return {"results": out, "notes": notes}


def compute_total_fvf(i: Inputs):
    go = _go(i)
    rs, t, gg, p = need(i.dict(), "rs", "t_f", "gamma_g", "p")
    if go is None:
        raise HTTPException(422, "Give the oil gravity.")
    out, notes = [], []
    bg = i.bg
    if bg is None and i.z:
        bg = bg_from_z(i.z, t + 460, p)
        notes.append(f"Bg = 0.00504 z T / p = {bg:.6f} bbl/scf.")
    if i.bo and i.rsb is not None and bg is not None:
        out.append(row("From the definition (Bo + (Rsb - Rs) Bg)", bt_definition(i.bo, i.rsb, rs, bg), "bbl/STB", measured=i.measured))
    out.append(row("Standing", bt_standing(rs, t, go, gg, p), "bbl/STB", measured=i.measured))
    out.append(row("Glaso", bt_glaso(rs, t, go, gg, p), "bbl/STB", measured=i.measured))
    out.append(row("Marhoun", bt_marhoun(rs, t, go, gg, p)[0], "bbl/STB", measured=i.measured))
    return {"results": out, "notes": notes}


def _aae(c, m):
    return 100 * sum(abs(a - b) / b for a, b in zip(c, m)) / len(m)


def property_checks():
    path = os.path.join(os.path.dirname(__file__), "data", "example_2_16.csv")
    rows = list(csv.DictReader(open(path)))
    ex = []
    for r in rows:
        ex.append(dict(t=float(r["T_F"]), api=float(r["API"]), gg=float(r["gamma_g"]), rs=float(r["Rs_measured"]), bo=float(r["Bo"]),
                       pbg=float(r["pb_psig"]), psep=float(r["psep_psig"]) + 14.7, tsep=float(r["Tsep_F"])))
    sections = []

    # gravity
    g = [
        ["Example 2-16, specific gravity from 53 lb/ft³", "0.849", f"{sg_from_density(53):.3f}"],
        ["Example 2-16, API gravity (from the rounded 0.849)", "35.2", f"{api_from_sg(0.849):.1f}"],
        ["Example 2-17, solution gas gravity", "0.819", f"{solution_gas_gravity([724, 202], [0.743, 0.956], 58, 1.296):.3f}"],
    ]
    sections.append({"title": "Gravity (Examples 2-16 and 2-17)", "columns": ["Quantity", "Published", "This tool"], "rows": g, "notes": ["Given the density directly, the tool returns 35.1 °API. The source rounds the specific gravity to 0.849 first and gets 35.2."]})

    # compressibility (Example 2-31)
    P = [2689, 2810, 2526, 2942, 3273, 4370]
    meas = [22.14, 18.75, 22.60, 21.51, 24.16, 11.45]
    bvb = [22.88, 20.16, 23.78, 22.31, 20.16, 11.54]
    bpf = [22.24, 19.27, 22.92, 21.78, 20.39, 11.77]
    cv, cp = [], []
    for e, p in zip(ex, P):
        gs = gas_gravity_at_100psig(e["gg"], e["api"], e["psep"], e["tsep"])
        cv.append(co_vasquez_beggs(e["rs"], e["t"], e["api"], gs, p + 14.7) * 1e6)
        cp.append(co_petrosky_farshad(e["rs"], e["t"], e["api"], e["gg"], p + 14.7) * 1e6)
    cols = ["Method"] + [f"Oil {n}" for n in range(1, 7)] + ["AAE here", "AAE published"]
    sections.append({
        "title": "Undersaturated oil compressibility, 10⁻⁶ psi⁻¹ (Example 2-31)", "columns": cols,
        "rows": [["Measured"] + [str(x) for x in meas] + ["", ""],
                 ["Vasquez-Beggs"] + [f"{x:.2f}" for x in cv] + [f"{_aae(cv, meas):.2f}%", "6.18%"],
                 ["Vasquez-Beggs, as printed"] + [str(x) for x in bvb] + ["", ""],
                 ["Petrosky-Farshad"] + [f"{x:.2f}" for x in cp] + [f"{_aae(cp, meas):.2f}%", "4.05%"],
                 ["Petrosky-Farshad, as printed"] + [str(x) for x in bpf] + ["", ""]],
        "notes": ["The pressures in the table are gauge pressures and 14.7 psi is added. Without that, every value comes out about 0.5% high.",
                  "Oil 4 reproduces with 214 °F here, the same value that works in the Rs and Pb checks.",
                  "Petrosky-Farshad averages 4.02% here and the source prints 4.05%. The individual values match to 0.01, so the difference looks like rounding in the published average."]})

    # Example 2-32 compressibility below pb + McCain
    go = sg_from_api(47.1)
    m1 = co_mccain(1665, 2392, 250, 47.1, 751, True) * 1e6
    m2 = co_below_pb(1665, 250, 515, 1.393, 0.001936, 0.851, go) * 1e6
    sections.append({"title": "Compressibility, Example 2-32", "columns": ["Quantity", "Published", "This tool"],
                     "rows": [["McCain (Eq. 2-101)", "290.3", f"{m1:.1f}"], ["Eq. 2-104", "424", f"{m2:.0f}"]],
                     "notes": ["The measured compressibility is printed as 324.8 × 15⁻⁶ in the problem statement. It is almost certainly 10⁻⁶. It is not used in any calculation."]})

    # Bo undersaturated (Example 2-33)
    vb = bo_under_vasquez_beggs(1.528, 5015, 2392, 751, 250, 47.1, 0.873)
    pf = bo_under_petrosky_farshad(1.528, 5015, 2392, 751, 250, 47.1, 0.851)
    sections.append({"title": "Oil formation volume factor above pb (Example 2-33, oil 1 at 5,015 psia)", "columns": ["Quantity", "Published", "This tool"],
                     "rows": [["Parameter A, Vasquez-Beggs", "0.061858", f"{a_vb(751, 250, 47.1, 0.873):.6f}"],
                              ["Bo, Vasquez-Beggs (Eq. 2-108)", "1.459", f"{vb:.3f}"],
                              ["Parameter A, Petrosky-Farshad", "0.005778", f"{a_pf(751, 250, 47.1, 0.851):.6f}"],
                              ["Bo, Petrosky-Farshad (Eq. 2-109)", "1.453", f"{pf:.3f}"]],
                     "notes": ["Petrosky-Farshad uses the temperature in °F (250) in the equation, not °R. The published A of 0.005778 needs that. With 710 the result would be about 1.38.",
                               "Petrosky-Farshad Bo is 1.454 here and 1.453 in the source, a difference of 0.1% that looks like rounding in the published arithmetic.",
                               "The Bo equation prints the exponent as 0.4094 and the worked line uses 0.4096 on the bubble-point pressure. The result barely moves."]})

    # Density (Example 2-34)
    msd = [38.13, 40.95, 37.37, 42.25, 37.70, 46.79]
    from rs_correlations import api_to_sg
    d111 = [density_from_bo(api_to_sg(e["api"]), e["rs"], e["gg"], e["bo"]) for e in ex]
    d112 = [density_standing(api_to_sg(e["api"]), e["rs"], e["gg"], e["t"]) for e in ex]
    bk1 = [38.04, 40.85, 37.68, 41.52, 38.39, 46.86]
    bk2 = [38.31, 40.18, 38.26, 40.39, 38.08, 44.11]
    sections.append({
        "title": "Oil density at the bubble point, lb/ft³ (Example 2-34)", "columns": cols,
        "rows": [["Measured, as printed"] + [str(x) for x in msd] + ["", ""],
                 ["From Bo (Eq. 2-111)"] + [f"{x:.2f}" for x in d111] + [f"{_aae(d111, msd):.2f}%", "0.84%"],
                 ["Column headed Eq. 2-112, as printed"] + [str(x) for x in bk1] + ["", ""],
                 ["Standing (Eq. 2-112)"] + [f"{x:.2f}" for x in d112] + [f"{_aae(d112, msd):.2f}%", "2.65%"],
                 ["Column headed Eq. 2-113, as printed"] + [str(x) for x in bk2] + ["", ""]],
        "notes": ["Oils 1, 2, 3, 5 and 6 match the source to 0.01. Oil 4 does not. The published table has a measured density of 42.25 for oil 4 (38.92 in the Example 2-30 data) and results of 41.52 and 40.39, where the printed inputs give 39.01 and 38.76. The published own printed rows give its 0.84% and 2.65% averages, so the difference sits in the oil 4 inputs and not in the equations. Oil 4 probably comes from different data.",
                  "The column the source heads Eq. 2-112 is what Eq. 2-111 gives from the measured Bo. The column headed Eq. 2-113 is what Standing's Eq. 2-112 gives. The headings look shifted by one equation number.",
                  "Eq. 2-113, 2-114 and 2-115 (density above the bubble point) have no worked example in these pages, so they are coded from the printed equations and not checked against the source."]})

    # Total FVF (Example 2-35)
    go, gg = 0.843, 0.6744
    sections.append({"title": "Total formation volume factor (Example 2-35, 2,000 psia)", "columns": ["Method", "Published", "This tool"],
                     "rows": [["Definition, Bo + (Rsb - Rs) Bg, with Bg = 0.001225", "1.195", f"{bt_definition(1.1752, 603, 444, 0.001225):.3f}"],
                              ["Definition, with Bg = 0.0001225 (the value the published line uses)", "1.195", f"{bt_definition(1.1752, 603, 444, 0.0001225):.3f}"],
                              ["Standing", "1.200", f"{bt_standing(444, 140, go, gg, 2000):.3f}"],
                              ["Glaso", "1.138", f"{bt_glaso(444, 140, go, gg, 2000):.3f}"],
                              ["Marhoun", "1.2664", f"{bt_marhoun(444, 140, go, gg, 2000)[0]:.4f}"]],
                     "notes": ["The published Step 4 gives Bg = 0.001225 bbl/scf, but its Step 5 uses 0.0001225. With 0.001225 the definition gives 1.370, not 1.195. The published 1.195 only reproduces with the smaller value. Please check this in your copy.",
                               "Standing: the source prints log Bt = 0.0792. The same numbers give 0.0797 (the published arithmetic is slightly off), so the tool returns 1.202 where the source prints 1.200.",
                               "Marhoun: the tool's F is 78,639 where the source prints 78,590.68, which looks like intermediate rounding. Bt is 1.2670 against 1.2664.",
                               "Glaso reproduces. The correlating temperature is 140 °F, as in the published worked line."]})
    return {"sections": sections}
