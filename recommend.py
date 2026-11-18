"""Method recommendation from measured data.

Given the oil gravity of the user's crude, find measured oils of similar gravity in the built-in dataset, score each
correlation on those oils and report the best one with the evidence behind it. The dataset only holds Bo, so Rs and Pb
return a plain statement that there is no measured data to rank them on.

The evidence levels are this tool's own rule of thumb, not a published standard. They describe how many similar oils the
ranking rests on and how close the top two methods are.
"""
import math
from typing import Optional

import numpy as np
from fastapi import HTTPException
from pydantic import BaseModel

from analyze import FAILURES, load_builtin
from metrics import summarize_errors
from registry import REGISTRIES, run_method

STRONG_N = 100
MODERATE_N = 30
MIN_N = 10
TIE_POINTS = 0.5  # percentage points of average absolute error


class RecommendRequest(BaseModel):
    prop: str = "bo"
    api: float
    regions: Optional[list[str]] = None
    api_window: float = 5.0
    exclude_duplicates: bool = True
    exclude_suspect_gas: bool = True


def _evidence(n):
    if n >= STRONG_N:
        return "strong"
    if n >= MODERATE_N:
        return "moderate"
    if n >= MIN_N:
        return "weak"
    return "none"


def recommend(req: RecommendRequest):
    if req.prop not in REGISTRIES:
        raise HTTPException(404, f"Unknown property: {req.prop}")
    if not (0 < req.api < 80):
        raise HTTPException(400, "Oil gravity should be between 0 and 80 °API.")
    if not (0 < req.api_window <= 20):
        raise HTTPException(400, "The gravity window should be between 0 and 20 °API.")

    if req.prop != "bo":
        return {
            "available": False,
            "prop": req.prop,
            "reason": "The workbench has no measured Rs or bubble point data to rank these methods on. "
                      "Upload your own measurements in the Test on data view to rank them on your oils.",
        }

    df = load_builtin()
    regions_all = [{"name": str(n), "n": int(len(g))} for n, g in df.groupby("region", sort=False)]
    notes = []
    if req.regions is not None:
        df = df[df["region"].isin(req.regions)]
    if req.exclude_duplicates:
        df = df[~df["is_duplicate"]]
    if req.exclude_suspect_gas:
        dropped = int(df["suspect_gas"].sum())
        df = df[~df["suspect_gas"]]
        if dropped:
            notes.append(f"Left out {dropped} oils with gas gravity above 1.5, which is unusually high.")
    lo, hi = req.api - req.api_window, req.api + req.api_window
    df = df[(df["api"] >= lo) & (df["api"] <= hi)].reset_index(drop=True)

    registry = REGISTRIES["bo"]
    base = {"available": True, "prop": "bo", "window": [round(lo, 1), round(hi, 1)], "regions": regions_all, "notes": notes}
    if len(df) < MIN_N:
        return base | {
            "n": int(len(df)), "evidence": "none", "ranking": [], "verdict": None,
            "message": f"Only {len(df)} measured {'oil falls' if len(df) == 1 else 'oils fall'} in this range. That is not enough to rank the methods. "
                       "Widen the gravity window, include more regions, or test the methods on your own data.",
        }

    measured = df["bo"].to_numpy(dtype=float)
    ranking = []
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
        s = summarize_errors(out, measured)
        if s["aae"] is not None:
            ranking.append({"key": key, "name": entry["name"], "n": s["n"], "aae": s["aae"], "bias": s["bias"]})
    ranking.sort(key=lambda r: r["aae"])

    n = int(len(df))
    best = ranking[0]
    second = ranking[1] if len(ranking) > 1 else None
    gap = (second["aae"] - best["aae"]) if second else None
    tie = gap is not None and gap < TIE_POINTS
    leaders = [r["name"] for r in ranking if r["aae"] - best["aae"] < TIE_POINTS]
    behind = [r["name"] for r in ranking if r["aae"] - best["aae"] >= TIE_POINTS]
    used_regions = sorted(set(df["region"]))
    if {"North Sea", "Middle East (a)", "Middle East (b)"} & set(used_regions) and {"Glaso", "Marhoun"} & {r["key"] for r in ranking if r["aae"] - best["aae"] < TIE_POINTS}:
        notes.append(
            "North Sea and Middle East oils overlap with the data used to fit the Glaso and Marhoun correlations, "
            "so those two can look better here than they would on new oils."
        )
    notes.append("Many oils in this dataset are volatile oils, which black oil correlations are not designed for.")

    return base | {
        "n": n,
        "used_regions": used_regions,
        "evidence": _evidence(n),
        "ranking": ranking,
        "verdict": {
            "key": best["key"], "name": best["name"], "aae": best["aae"],
            "runner_up": second["name"] if second else None,
            "gap": gap, "tie": tie, "leaders": leaders, "behind": behind,
        },
        "notes": notes,
    }
