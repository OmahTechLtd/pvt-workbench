"""Convert the Mendeley PVT workbook into the workbench schema.

Output columns: oil, region, t_f, rs_measured, api, gamma_g, bo
Units are read from each sheet's header text. A sheet whose units cannot be
identified is skipped with a message, so nothing is guessed silently.
"""
import re
import sys
import pandas as pd


SRC = sys.argv[1] if len(sys.argv) > 1 else "data/PVTData.xlsx"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/mendeley_pvt_bo.csv"


def unit_of(header):
    """Text inside the first brackets of a header, lowercased, without degree signs."""
    m = re.search(r"\(([^)]*)\)", str(header))
    return re.sub(r"[°\s]|deg", "", m.group(1).lower()) if m else ""


def find_header_row(raw):
    for i in range(len(raw)):
        if str(raw.iat[i, 1]).strip().lower() == "id":
            return i
    return None


def convert_sheet(name, raw):
    h = find_header_row(raw)
    if h is None:
        return None, "no header row with 'ID' in column B"
    heads = [raw.iat[h, c] for c in range(1, 7)]
    body = raw.iloc[h + 1:, 1:7].copy()
    body.columns = ["id", "rs", "go", "gg", "t", "bo"]
    body = body[pd.to_numeric(body["id"], errors="coerce").notna()]
    for col in ["rs", "go", "gg", "t", "bo"]:
        body[col] = pd.to_numeric(body[col], errors="coerce")
        before = len(body)
    body = body.dropna(subset=["rs", "go", "gg", "t", "bo"])
    if len(body) < before:
        print(f"{name}: dropped {before - len(body)} incomplete rows")
        
    # temperature unit
    tu = unit_of(heads[4])
    if tu == "f":
        t_f = body["t"]
    elif tu == "c":
        t_f = body["t"] * 1.8 + 32
    elif tu == "k":
        t_f = (body["t"] - 273.15) * 1.8 + 32
    elif tu == "r":
        t_f = body["t"] - 459.67
    else:
        return None, f"temperature unit not recognised in header {heads[4]!r}"

    # solution gas-oil ratio unit (ft3/bbl is read as scf/STB)
    ru = unit_of(heads[1])
    if "ft" in ru or "scf" in ru:
        rs = body["rs"]
    elif "m3" in ru or "m³" in ru:
        rs = body["rs"] * 5.614583
    else:
        return None, f"Rs unit not recognised in header {heads[1]!r}"

    # oil gravity: relative density, or API if the header says so
    if "api" in str(heads[2]).lower():
        api = body["go"]
    else:
        api = 141.5 / body["go"] - 131.5

    out = pd.DataFrame({
        "oil": [f"{name}-{int(i)}" for i in body["id"]],
        "region": name,
        "t_f": t_f.round(1).values,
        "rs_measured": rs.values,
        "api": api.round(1).values,
        "gamma_g": body["gg"].values,
        "bo": body["bo"].values,
    })
    return out, None


def main():
    sheets = pd.read_excel(SRC, sheet_name=None, header=None)
    parts = []
    for name, raw in sheets.items():
        df, problem = convert_sheet(name, raw)
        if df is None:
            print(f"SKIPPED {name}: {problem}")
            continue
        print(f"{name}: {len(df)} rows | API {df.api.min():.1f}-{df.api.max():.1f} | "
              f"T {df.t_f.min():.0f}-{df.t_f.max():.0f} F | Rs {df.rs_measured.min():.0f}-{df.rs_measured.max():.0f} | "
              f"Bo {df.bo.min():.3f}-{df.bo.max():.3f} | gas SG max {df.gamma_g.max():.3f}")
        parts.append(df)
    if not parts:
        sys.exit("Nothing converted.")
    all_rows = pd.concat(parts, ignore_index=True)
    key = ["t_f", "rs_measured", "api", "gamma_g", "bo"]
    dupes = all_rows[all_rows.duplicated(subset=key, keep=False)]
    print(f"Rows that exactly match another row: {len(dupes)}")
    print(dupes.groupby(key)["region"].agg(lambda s: tuple(sorted(set(s)))).value_counts())
    all_rows.to_csv(OUT, index=False)
    print(f"\nWrote {len(all_rows)} rows to {OUT}")
    high = all_rows[all_rows.gamma_g > 1.5]
    print(f"Rows with gas gravity above 1.5, check before using: {len(high)}")


if __name__ == "__main__":
    main()