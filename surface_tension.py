"""Surface tension of a hydrocarbon mixture, Katz et al. form of the Sugden correlation.
Ahmed, Reservoir Engineering Handbook, 5th ed., Eq. 2-122 to 2-124 and Table 2-1, pp. 110-112."""

from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel

MOLECULAR_WEIGHT = {"CO2": 44.01, "N2": 28.013, "C1": 16.043, "C2": 30.07, "C3": 44.097,
                    "iC4": 58.123, "nC4": 58.123, "iC5": 72.15, "nC5": 72.15, "nC6": 86.177, "nC7": 100.204, "nC8": 114.231}
PARACHOR = {"CO2": 78.0, "N2": 41.0, "C1": 77.0, "C2": 108.0, "C3": 150.3, "iC4": 181.5, "nC4": 189.9,
            "iC5": 225.0, "nC5": 231.5, "nC6": 271.0, "nC7": 312.5, "nC8": 351.5}


def parachor_plus(m):
    """Fanchi (1985), Eq. 2-123. Valid for components heavier than methane."""
    return 69.9 + 2.3 * m


def surface_tension(components, x, y, rho_o, rho_g, m_plus=None):
    """components: list of names from PARACHOR, plus optionally 'C7+' (needs m_plus).
    x, y: mole fractions in the oil and gas. Densities in lb/ft3. Returns dict with sigma in dynes/cm."""
    def mw(c):
        return m_plus if c == "C7+" else MOLECULAR_WEIGHT[c]
    def pch(c):
        return parachor_plus(m_plus) if c == "C7+" else PARACHOR[c]
    mo = sum(xi * mw(c) for c, xi in zip(components, x))
    mg = sum(yi * mw(c) for c, yi in zip(components, y))
    a = rho_o / (62.4 * mo)
    b = rho_g / (62.4 * mg)
    terms = [pch(c) * (a * xi - b * yi) for c, xi, yi in zip(components, x, y)]
    s = sum(terms)
    return {"mo": mo, "mg": mg, "A": a, "B": b, "terms": terms, "sum": s,
            "sigma": s ** 4 if s > 0 else None}


class TensionIn(BaseModel):
    components: list[str]
    x: list[float]
    y: list[float]
    rho_o: float
    rho_g: float
    m_plus: Optional[float] = None


def tension_components():
    return {"components": list(PARACHOR.keys()) + ["C7+"]}


def compute_tension(i: TensionIn):
    n = len(i.components)
    if not (n == len(i.x) == len(i.y)) or n == 0:
        raise HTTPException(422, "Give a name, an oil fraction and a gas fraction for each component.")
    if "C7+" in i.components and not i.m_plus:
        raise HTTPException(422, "Give the molecular weight of the C7+ fraction.")
    for c in i.components:
        if c != "C7+" and c not in PARACHOR:
            raise HTTPException(422, f"Unknown component {c}.")
    if i.rho_o <= 0 or i.rho_g <= 0:
        raise HTTPException(422, "Densities must be above zero.")
    r = surface_tension(i.components, i.x, i.y, i.rho_o, i.rho_g, i.m_plus)
    r["sum_x"] = sum(i.x)
    r["sum_y"] = sum(i.y)
    r["components"] = i.components
    if r["sigma"] is None:
        raise HTTPException(422, "The sum is not positive, so there is no surface tension. Check that the oil is denser than the gas and the compositions are in the right columns.")
    return r
