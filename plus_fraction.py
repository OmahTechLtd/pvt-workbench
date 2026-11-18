"""Characterization of undefined petroleum fractions.

Given the molecular weight M and specific gravity of a heptanes-plus (C7+) fraction,
this module estimates boiling point, critical temperature, critical pressure and
critical volume with the Riazi and Daubert (1987) equation, the acentric factor with
Edmister's equation, and the critical compressibility factor with the methods in
Table 1-5.

Source pages in Ahmed, Tarek. Reservoir Engineering Handbook, 5th edition
  Eq. 1-2 and Table 1-4   p. 24   Riazi-Daubert
  Eq. 1-3                 p. 24   Edmister acentric factor
  Eq. 1-4, Table 1-5      p. 25   critical compressibility factor
  Example 1-1             pp. 25-26

The module name avoids "fractions" so it does not shadow the Python standard library.
"""
import math

from fastapi import HTTPException
from pydantic import BaseModel

# Universal gas constant as printed under Eq. 1-4, psia ft3 / (lb-mol °R)
R_GAS = 10.73

# Table 1-4, correlation constants for Eq. 1-2: theta = a M^b g^c exp(d M + e g + f M g)
RIAZI_DAUBERT = {
    "tc": dict(a=544.4, b=0.2998, c=1.0555, d=-1.3478e-4, e=-0.61641, f=0.0),
    "pc": dict(a=4.5203e4, b=-0.8063, c=1.6015, d=-1.8078e-3, e=-0.3084, f=0.0),
    "vc": dict(a=1.206e-2, b=0.20378, c=-1.3036, d=-2.657e-3, e=0.5287, f=2.6012e-3),
    "tb": dict(a=6.77857, b=0.401673, c=-1.58262, d=3.77409e-3, e=2.984036, f=-4.25288e-3),
}

PROPERTY_INFO = {
    "tb": ("Boiling point, Tb", "°R"),
    "tc": ("Critical temperature, Tc", "°R"),
    "pc": ("Critical pressure, pc", "psia"),
    "vc": ("Critical volume, Vc", "ft3/lb"),
}


def riazi_daubert(prop: str, m: float, gamma: float, constants: dict | None = None) -> float:
    k = constants or RIAZI_DAUBERT[prop]
    return k["a"] * m ** k["b"] * gamma ** k["c"] * math.exp(k["d"] * m + k["e"] * gamma + k["f"] * m * gamma)


def edmister_omega(pc: float, tc: float, tb: float) -> float:
    """Eq. 1-3. Needs Tc above Tb and pc above atmospheric pressure."""
    if tc <= tb:
        raise ValueError("Critical temperature must be above the boiling point.")
    if pc <= 14.70:
        raise ValueError("Critical pressure must be above 14.70 psia.")
    return 3.0 * math.log10(pc / 14.70) / (7.0 * (tc / tb - 1.0)) - 1.0


def zc_from_omega(omega: float) -> dict:
    """Table 1-5. The printed Nath equation shows no acentric factor term. It is coded
    here as 0.2918 - 0.0928 omega, which is how the other three methods are written."""
    return {
        "haugen": 1.0 / (1.28 * omega + 3.41),
        "reid_prausnitz_sherwood": 0.291 - 0.080 * omega,
        "salerno": 0.291 - 0.080 * omega - 0.016 * omega ** 2,
        "nath": 0.2918 - 0.0928 * omega,
    }


def zc_from_critical_constants(pc: float, vc: float, m: float, tc: float) -> float:
    """Eq. 1-4"""
    return pc * vc * m / (R_GAS * tc)


ZC_NAMES = {
    "haugen": "Haugen (1959), Eq. 1-5",
    "reid_prausnitz_sherwood": "Reid, Prausnitz and Sherwood (1977), Eq. 1-6",
    "salerno": "Salerno et al. (1985), Eq. 1-7",
    "nath": "Nath (1985), Eq. 1-8",
}


def characterize(m: float, gamma: float) -> dict:
    if not (math.isfinite(m) and math.isfinite(gamma)) or m <= 0 or gamma <= 0:
        raise ValueError("Molecular weight and specific gravity must be positive numbers.")
    props = {p: riazi_daubert(p, m, gamma) for p in RIAZI_DAUBERT}
    omega = edmister_omega(props["pc"], props["tc"], props["tb"])
    zc = zc_from_omega(omega)
    return {
        "inputs": {"m": m, "gamma": gamma},
        "properties": {
            p: {"label": PROPERTY_INFO[p][0], "unit": PROPERTY_INFO[p][1], "value": props[p]}
            for p in ("tb", "tc", "pc", "vc")
        },
        "omega": omega,
        "zc": [
            {"key": key, "name": ZC_NAMES[key], "value": value, "source": "from the acentric factor"}
            for key, value in zc.items()
        ]
        + [
            {
                "key": "eos",
                "name": "Real gas equation at the critical point, Eq. 1-4",
                "value": zc_from_critical_constants(props["pc"], props["vc"], m, props["tc"]),
                "source": "from pc, Vc, M and Tc",
            }
        ],
    }


# Example 1-1, M = 150, specific gravity 0.78. Printed answers are on p. 26.
EXAMPLE_1_1 = {"m": 150.0, "gamma": 0.78}
BOOK_ANSWERS = {
    "tc": (1139.4, 0.1),
    "pc": (320.3, 0.1),
    "vc": (0.06035, 0.00001),
    "tb": (825.26, 0.01),
    "omega": (0.5067, 0.0001),
}


def verification() -> dict:
    """Compare this code with the printed answers of Example 1-1.

    A row counts as a match when it is within one unit of the last printed digit."""
    m, g = EXAMPLE_1_1["m"], EXAMPLE_1_1["gamma"]
    calc = {p: riazi_daubert(p, m, g) for p in RIAZI_DAUBERT}
    rows = []

    def add(key, label, unit, calculated, note=None):
        book, tol = BOOK_ANSWERS[key]
        diff = (calculated - book) / book * 100
        rows.append(
            {
                "label": label,
                "unit": unit,
                "book": book,
                "calculated": calculated,
                "diff_pct": diff,
                "match": abs(calculated - book) <= tol,
                "note": note,
            }
        )

    add("tb", "Boiling point, Tb", "°R", calc["tb"])
    add("pc", "Critical pressure, pc", "psia", calc["pc"])
    add("tc", "Critical temperature, Tc (Table 1-4 constant a = 544.4)", "°R", calc["tc"],
        "The worked line in the source prints a = 544.2, not the 544.4 given in Table 1-4.")
    tc_544_2 = riazi_daubert("tc", m, g, {**RIAZI_DAUBERT["tc"], "a": 544.2})
    add("tc", "Critical temperature, Tc (with a = 544.2 as printed in the worked line)", "°R", tc_544_2,
        "Using the constant printed in the worked line reproduces the published answer.")
    add("vc", "Critical volume, Vc", "ft3/lb", calc["vc"],
        "Does not match. The printed constants give 0.0636. Table 1-1 lists 0.0626 to 0.0640 for C8 to C20, "
        "so 0.0636 looks consistent and 0.06035 looks out of line. The cause is not identified.")
    omega_book_inputs = edmister_omega(320.3, 1139.4, 825.26)
    add("omega", "Acentric factor (from the published printed Tc, pc and Tb)", "", omega_book_inputs)
    omega_chain = edmister_omega(calc["pc"], calc["tc"], calc["tb"])
    add("omega", "Acentric factor (from this tool's own Tc, pc and Tb)", "", omega_chain,
        "Differs only because Tc differs by 0.4 °R, which comes from the 544.2 versus 544.4 constant.")
    return {
        "example": EXAMPLE_1_1,
        "rows": rows,
        "summary": "Tb, pc and the acentric factor reproduce. Tc reproduces once the constant printed in "
                   "the worked line is used. Vc does not reproduce.",
    }


class FractionRequest(BaseModel):
    m: float
    gamma: float


def fraction_characterize(req: FractionRequest):
    try:
        return characterize(req.m, req.gamma)
    except (ValueError, ZeroDivisionError, OverflowError) as e:
        raise HTTPException(400, str(e))
