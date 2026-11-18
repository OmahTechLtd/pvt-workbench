"""Dataset analysis: score correlations against many measured records.

Two sources are supported. The built-in source is the converted Mendeley PVT
workbook (data/mendeley_pvt_bo.csv), which can only score Bo because it has no
pressure, bubble-point or separator data. An uploaded CSV can score Rs, Pb or Bo
as long as it has the columns the chosen methods need.
"""
import io
import math
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from metrics import summarize_errors
from registry import REGISTRIES, MEASURED_COLUMN, run_method

router = APIRouter()

BUILTIN_CSV = Path(__file__).parent / "data" / "mendeley_pvt_bo.csv"
MEASUREMENT_KEY = ["t_f", "rs_measured", "api", "gamma_g", "bo"]
# The sheet that repeats rows found in other sheets. Its copies are the ones dropped.
DUPLICATE_SHEET = "Middle East (b)"
SUSPECT_GAS_GRAVITY = 1.5
MAX_CSV_BYTES = 5_000_000
MAX_ROWS_RETURNED = 5000
FAILURES = (ValueError, ZeroDivisionError, OverflowError, TypeError)


class AnalyzeRequest(BaseModel):
    prop: str
    methods: list[str]
    source: Literal["builtin", "upload"] = "builtin"
    csv_text: Optional[str] = None
    regions: Optional[list[str]] = None
    exclude_duplicates: bool = True
    max_gas_gravity: Optional[float] = None


def load_builtin() -> pd.DataFrame:
    df = pd.read_csv(BUILTIN_CSV)
    same = df.duplicated(subset=MEASUREMENT_KEY, keep=False)
    df["is_duplicate"] = same & (df["region"] == DUPLICATE_SHEET)
    df["suspect_gas"] = df["gamma_g"] > SUSPECT_GAS_GRAVITY
    return df


@router.get("/dataset/builtin")
def builtin_summary():
    df = load_builtin()
    regions = []
    for name, g in df.groupby("region", sort=False):
        regions.append({
            "name": name,
            "n": int(len(g)),
            "n_duplicates": int(g["is_duplicate"].sum()),
            "n_suspect_gas": int(g["suspect_gas"].sum()),
        })
    return {
        "n_rows": int(len(df)),
        "regions": regions,
        "n_duplicates": int(df["is_duplicate"].sum()),
        "n_suspect_gas": int(df["suspect_gas"].sum()),
        "suspect_gas_limit": SUSPECT_GAS_GRAVITY,
        "duplicate_sheet": DUPLICATE_SHEET,
        "scoreable": ["bo"],
    }


def parse_upload(text: str) -> pd.DataFrame:
    if len(text.encode("utf-8")) > MAX_CSV_BYTES:
        raise HTTPException(413, "The CSV is larger than 5 MB.")
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        raise HTTPException(400, f"Could not read the CSV: {e}")
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def column_or_blank(df, name):
    return df[name] if name in df.columns else pd.Series([None] * len(df), index=df.index)


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    if req.prop not in REGISTRIES:
        raise HTTPException(404, f"Unknown property: {req.prop}")
    registry = REGISTRIES[req.prop]
    if not req.methods:
        raise HTTPException(400, "Select at least one method.")
    for key in req.methods:
        if key not in registry:
            raise HTTPException(404, f"Unknown method: {key}")

    notes = []
    if req.source == "builtin":
        if req.prop != "bo":
            raise HTTPException(
                400,
                "The built-in dataset can only score Bo. It has no pressure, bubble-point "
                "or separator data. Upload a CSV to score Rs or Pb.",
            )
        df = load_builtin()
        loaded = len(df)
        if req.regions is not None:
            df = df[df["region"].isin(req.regions)]
        if req.exclude_duplicates:
            dropped = int(df["is_duplicate"].sum())
            df = df[~df["is_duplicate"]]
            if dropped:
                notes.append(f"Left out {dropped} rows from {DUPLICATE_SHEET} that repeat rows in other sheets.")
        if req.max_gas_gravity is not None:
            dropped = int((df["gamma_g"] > req.max_gas_gravity).sum())
            df = df[df["gamma_g"] <= req.max_gas_gravity]
            if dropped:
                notes.append(f"Left out {dropped} rows with gas gravity above {req.max_gas_gravity}.")
        else:
            suspect = int(df["suspect_gas"].sum())
            if suspect:
                notes.append(
                    f"{suspect} rows have gas gravity above {SUSPECT_GAS_GRAVITY}, "
                    "which is unusually high. Check them before trusting these results."
                )
    else:
        if not req.csv_text:
            raise HTTPException(400, "No CSV was supplied.")
        df = parse_upload(req.csv_text)
        loaded = len(df)

    measured_col = MEASURED_COLUMN[req.prop]
    needed = {measured_col}
    for key in req.methods:
        needed.update(registry[key]["inputs"])
    missing = sorted(needed - set(df.columns))
    if missing:
        raise HTTPException(400, "The data is missing these columns: " + ", ".join(missing))

    df = df.copy()
    for col in needed | {"psep_psia", "tsep_f"}:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=list(needed)).reset_index(drop=True)
    if df.empty:
        raise HTTPException(400, "No usable rows are left after filtering.")

    measured = df[measured_col].to_numpy(dtype=float)
    predictions = {}
    for key in req.methods:
        entry = registry[key]
        optional = [c for c in entry.get("optional_inputs", []) if c in df.columns]
        out = np.full(len(df), np.nan)
        for i in range(len(df)):
            row = {c: float(df.at[i, c]) for c in entry["inputs"]}
            for c in optional:
                if pd.notna(df.at[i, c]):
                    row[c] = float(df.at[i, c])
            try:
                value = run_method(key, row, registry)
                if value is not None and math.isfinite(value):
                    out[i] = value
            except FAILURES:
                pass
        predictions[key] = out

    summary = []
    for key in req.methods:
        s = summarize_errors(predictions[key], measured)
        s.update({"key": key, "name": registry[key]["name"], "failed": int(np.isnan(predictions[key]).sum())})
        summary.append(s)

    by_region = {}
    if "region" in df.columns:
        for region, idx in df.groupby("region", sort=False).groups.items():
            idx = list(idx)
            by_region[str(region)] = {
                key: summarize_errors(predictions[key][idx], measured[idx]) | {"key": key}
                for key in req.methods
            }
        if req.source == "builtin":
            if {"Glaso", "Marhoun"} & set(req.methods) and set(by_region) & {"North Sea", "Middle East (a)", "Middle East (b)"}:
                notes.append(
                    "North Sea and Middle East data overlap with the data used to fit the Glaso and "
                    "Marhoun correlations, so those two may look better here than on new data."
                )
            notes.append("Many oils in this dataset are volatile oils, which black oil correlations are not designed for.")

    rows = []
    for i in range(min(len(df), MAX_ROWS_RETURNED)):
        rec = {
            "oil": str(df.at[i, "oil"]) if "oil" in df.columns else str(i + 1),
            "region": str(df.at[i, "region"]) if "region" in df.columns else None,
            "measured": float(measured[i]),
        }
        for key in req.methods:
            v = predictions[key][i]
            rec[key] = None if np.isnan(v) else float(v)
        rows.append(rec)

    return {
        "prop": req.prop,
        "source": req.source,
        "rows_loaded": int(loaded),
        "rows_used": int(len(df)),
        "summary": summary,
        "by_region": by_region,
        "rows": rows,
        "notes": notes,
    }