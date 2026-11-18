"""Crude oil classification.

The source describes four types of crude oil and gives typical property limits for
each (pp. 4 to 8). It also classifies an oil reservoir by where its initial pressure
and temperature sit on the phase diagram (p. 3).

The limits are descriptions of typical behaviour, not sharp cut-offs, and the printed
ranges leave gaps. For example no class covers a gas-oil ratio between 700 and
2,000 scf/STB. This module applies the printed limits as written and says plainly
when an oil falls outside all of them.

Ranges quoted as "between a and b" are treated as inclusive.
"""
import math
from typing import Optional

import numpy as np
from fastapi import HTTPException
from pydantic import BaseModel

from analyze import load_builtin
from metrics import summarize_errors
from registry import REGISTRIES, run_method

FAILURES = (ValueError, ZeroDivisionError, OverflowError, TypeError)

PARAMS = {
    "gor": ("Gas-oil ratio", "scf/STB"),
    "bo": ("Oil formation volume factor", "bbl/STB"),
    "api": ("Oil gravity", "°API"),
    "c7plus": ("Heptanes-plus content", "mol%"),
}


def _between(lo, hi):
    return (lambda v: lo <= v <= hi), f"{lo:g} to {hi:g}"


def _below(x):
    return (lambda v: v < x), f"below {x:g}"


def _above(x):
    return (lambda v: v > x), f"above {x:g}"


def _at_least(x):
    return (lambda v: v >= x), f"{x:g} or higher"


# Each criterion is (parameter, test, printed rule). Pages refer to the 5th edition.
CLASSES = [
    {
        "key": "ordinary_black",
        "name": "Ordinary black oil",
        "page": "p. 4",
        "colour": "Stock-tank oil is usually brown to dark green.",
        "criteria": [("gor", *_between(200, 700)), ("api", *_between(15, 40))],
    },
    {
        "key": "low_shrinkage",
        "name": "Low-shrinkage oil",
        "page": "pp. 4 to 5",
        "colour": "Black or deeply coloured.",
        "criteria": [("bo", *_below(1.2)), ("gor", *_below(200)), ("api", *_below(35))],
    },
    {
        "key": "volatile",
        "name": "Volatile (high-shrinkage) oil",
        "page": "pp. 5 to 6",
        "colour": "Greenish to orange.",
        "criteria": [("bo", *_below(2.0)), ("gor", *_between(2000, 3200)), ("api", *_between(45, 55))],
    },
    {
        "key": "near_critical",
        "name": "Near-critical oil",
        "page": "pp. 7 to 8",
        "colour": "",
        "criteria": [("gor", *_above(3000)), ("bo", *_at_least(2.0)), ("c7plus", *_between(12.5, 20))],
    },
]
CLASS_BY_KEY = {c["key"]: c for c in CLASSES}

GAP_NOTE = (
    "The printed limits leave gaps. For example no class covers a gas-oil ratio between 700 and "
    "2,000 scf/STB, and the ranges for the four classes also overlap on oil gravity. An oil outside "
    "every class is not necessarily unusual. It means the table does not describe it."
)


def _clean(value) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def classify(gor=None, bo=None, api=None, c7plus=None) -> dict:
    values = {"gor": _clean(gor), "bo": _clean(bo), "api": _clean(api), "c7plus": _clean(c7plus)}
    given = [k for k, v in values.items() if v is not None]
    if not given:
        raise ValueError("Enter at least one property.")

    results = []
    for cls in CLASSES:
        checks = []
        for param, test, rule in cls["criteria"]:
            v = values[param]
            if v is None:
                continue
            checks.append(
                {
                    "param": param,
                    "label": PARAMS[param][0],
                    "unit": PARAMS[param][1],
                    "value": v,
                    "rule": rule,
                    "passed": bool(test(v)),
                }
            )
        tested = len(checks)
        passed = sum(c["passed"] for c in checks)
        results.append(
            {
                "key": cls["key"],
                "name": cls["name"],
                "page": cls["page"],
                "colour": cls["colour"],
                "checks": checks,
                "tested": tested,
                "passed": passed,
                "consistent": tested > 0 and passed == tested,
                "criteria_total": len(cls["criteria"]),
            }
        )

    matches = [r["key"] for r in results if r["consistent"]]
    notes = []
    if len(given) < 3:
        notes.append("Only some properties were entered, so more than one class can still fit. More inputs narrow the result.")
    if values["gor"] is not None and 700 < values["gor"] < 2000:
        notes.append("A gas-oil ratio between 700 and 2,000 scf/STB falls between the ranges the source gives.")

    if len(matches) == 1:
        verdict = f"Consistent with {CLASS_BY_KEY[matches[0]]['name'].lower()}."
    elif len(matches) > 1:
        names = " and ".join(CLASS_BY_KEY[k]["name"].lower() for k in matches)
        verdict = f"Consistent with more than one class, {names}."
    else:
        scored = [r for r in results if r["tested"] > 0]
        best = max(r["passed"] / r["tested"] for r in scored)
        closest = [r["name"].lower() for r in scored if r["passed"] / r["tested"] == best]
        verdict = "Outside all four classes as the source states them."
        if best > 0:
            notes.append("Closest on the properties entered: " + " and ".join(closest) + ".")
        notes.append(GAP_NOTE)

    return {"inputs": values, "verdict": verdict, "matches": matches, "classes": results, "notes": notes}


def reservoir_state(pi: float, pb: float, tolerance: float = 1.0) -> dict:
    """Ahmed p. 3. Initial pressure above, at or below the bubble point."""
    if pi <= 0 or pb <= 0:
        raise ValueError("Pressures must be positive.")
    if abs(pi - pb) <= tolerance:
        key, name = "saturated", "Saturated oil reservoir"
        text = "The initial pressure equals the bubble-point pressure."
    elif pi > pb:
        key, name = "undersaturated", "Undersaturated oil reservoir"
        text = "The initial pressure is above the bubble-point pressure."
    else:
        key, name = "gas_cap", "Gas-cap (two-phase) reservoir"
        text = "The initial pressure is below the bubble-point pressure, so a gas phase overlies the oil."
    return {"key": key, "name": name, "text": text, "tolerance_psi": tolerance}


def reservoir_kind(t: float, tc: float) -> dict:
    """Ahmed p. 3. Reservoir temperature against the critical temperature of the fluid."""
    if t < tc:
        return {"key": "oil", "name": "Oil reservoir", "text": "The reservoir temperature is below the critical temperature of the fluid."}
    return {"key": "gas", "name": "Gas reservoir", "text": "The reservoir temperature is above the critical temperature of the fluid."}


class ClassifyRequest(BaseModel):
    gor: Optional[float] = None
    bo: Optional[float] = None
    api: Optional[float] = None
    c7plus: Optional[float] = None
    pi: Optional[float] = None
    pb: Optional[float] = None
    t: Optional[float] = None
    tc: Optional[float] = None


def classify_endpoint(req: ClassifyRequest):
    out = {"oil": None, "pressure_state": None, "reservoir_kind": None}
    any_oil = any(v is not None for v in (req.gor, req.bo, req.api, req.c7plus))
    try:
        if any_oil:
            out["oil"] = classify(req.gor, req.bo, req.api, req.c7plus)
        if req.pi is not None and req.pb is not None:
            out["pressure_state"] = reservoir_state(req.pi, req.pb)
        if req.t is not None and req.tc is not None:
            out["reservoir_kind"] = reservoir_kind(req.t, req.tc)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not any_oil and out["pressure_state"] is None and out["reservoir_kind"] is None:
        raise HTTPException(400, "Enter at least one property.")
    return out


def criteria():
    return [
        {
            "key": c["key"],
            "name": c["name"],
            "page": c["page"],
            "colour": c["colour"],
            "criteria": [
                {"param": p, "label": PARAMS[p][0], "unit": PARAMS[p][1], "rule": rule}
                for p, _, rule in c["criteria"]
            ],
        }
        for c in CLASSES
    ]


def classify_dataset(exclude_duplicates: bool = True):
    """Classify every oil in the built-in dataset and score the Bo methods inside each class.

    The gas-oil ratio is the measured Rs in the dataset, which is the solution gas-oil
    ratio at the bubble point. For an oil produced above its bubble point this equals
    the producing gas-oil ratio. Bo is the value at the bubble point."""
    df = load_builtin()
    loaded = len(df)
    notes = []
    if exclude_duplicates:
        dropped = int(df["is_duplicate"].sum())
        df = df[~df["is_duplicate"]]
        if dropped:
            notes.append(f"Left out {dropped} rows that repeat rows in other sheets.")
    df = df.dropna(subset=["rs_measured", "api", "bo", "t_f", "gamma_g"]).reset_index(drop=True)

    labels = []
    for i in range(len(df)):
        res = classify(df.at[i, "rs_measured"], df.at[i, "bo"], df.at[i, "api"], None)
        # The dataset has no heptanes-plus content, so near-critical is judged on gas-oil
        # ratio and Bo only. Count it as a match only when both are tested and pass.
        matches = res["matches"]
        labels.append(matches[0] if len(matches) == 1 else ("multiple" if len(matches) > 1 else "none"))
    df["class"] = labels

    registry = REGISTRIES["bo"]
    preds = {}
    for key, entry in registry.items():
        out = np.full(len(df), np.nan)
        for i in range(len(df)):
            row = {c: float(df.at[i, c]) for c in entry["inputs"]}
            try:
                v = run_method(key, row, registry)
                if v is not None and math.isfinite(v):
                    out[i] = v
            except FAILURES:
                pass
        preds[key] = out
    measured = df["bo"].to_numpy(dtype=float)

    def block(mask, key, name, page=None):
        idx = np.where(mask)[0]
        methods = []
        for mkey, entry in registry.items():
            s = summarize_errors(preds[mkey][idx], measured[idx])
            s.update({"key": mkey, "name": entry["name"]})
            methods.append(s)
        sub = df.loc[idx]
        return {
            "key": key,
            "name": name,
            "page": page,
            "n": int(len(idx)),
            "share": float(len(idx) / len(df)) if len(df) else 0.0,
            "gor_range": [float(sub["rs_measured"].min()), float(sub["rs_measured"].max())] if len(idx) else None,
            "api_range": [float(sub["api"].min()), float(sub["api"].max())] if len(idx) else None,
            "bo_range": [float(sub["bo"].min()), float(sub["bo"].max())] if len(idx) else None,
            "methods": methods,
        }

    classes = [block(df["class"].to_numpy() == c["key"], c["key"], c["name"], c["page"]) for c in CLASSES]
    outside = block(df["class"].to_numpy() == "none", "none", "Outside all four classes")
    multiple = int((df["class"] == "multiple").sum())

    gor = df["rs_measured"]
    in_gap = int(((gor > 700) & (gor < 2000)).sum())
    # Not a book classification. Plain gas-oil ratio bands, to show how accuracy changes with gas content.
    g = gor.to_numpy()
    bands = [
        block(g < 200, "lt200", "Below 200 scf/STB"),
        block((g >= 200) & (g <= 700), "200to700", "200 to 700 scf/STB"),
        block((g > 700) & (g < 2000), "700to2000", "Above 700 and below 2,000 scf/STB"),
        block(g >= 2000, "ge2000", "2,000 scf/STB and above"),
    ]
    high_gor = int((g >= 2000).sum())
    high_gor_bo_below_2 = int(((g >= 2000) & (measured < 2.0)).sum())
    notes.append(
        "Gas-oil ratio is the measured Rs at the bubble point. The dataset has no heptanes-plus content, "
        "so near-critical oil is judged on gas-oil ratio and Bo only, and could not be confirmed on composition."
    )
    notes.append(GAP_NOTE)

    return {
        "rows_loaded": int(loaded),
        "rows_used": int(len(df)),
        "classes": classes,
        "outside": outside,
        "multiple": multiple,
        "n_in_gor_gap": in_gap,
        "gor_bands": bands,
        "n_gor_2000_plus": high_gor,
        "n_gor_2000_plus_bo_below_2": high_gor_bo_below_2,
        "notes": notes,
    }
