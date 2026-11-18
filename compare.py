import pandas as pd
from rs_correlations import psig_to_psia
from registry import REGISTRIES,MEASURED_COLUMN, run_method, calc_aae
from plots import compare_plot

df = pd.read_csv("data/example_2_16.csv")
df.columns = df.columns.str.lower()
df["p_psia"] = df["pb_psig"].apply(psig_to_psia)
df["psep_psia"] = df["psep_psig"].apply(psig_to_psia)


for prop, registry in REGISTRIES.items():
    for key in registry:
        df[key + "_" + prop] = df.apply(lambda row: run_method(key, row, registry), axis=1)

    print(df[["oil", MEASURED_COLUMN[prop]] + [k + "_" + prop for k in registry]].round(3 if prop == "bo" else 1))
    for key in registry:
        print(f"{key}: {calc_aae(df, key, prop):.1f}%")


for prop, registry in REGISTRIES.items():
    compare_plot(df, list(registry), prop)


