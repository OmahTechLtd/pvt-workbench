import pandas as pd
from rs_correlations import *
from metrics import aae

df = pd.read_csv("data/example_2_16.csv")
df["p_psia"] = df["pb_psig"].apply(psig_to_psia)
df["psep_psia"] = df["psep_psig"].apply(psig_to_psia)

df["Standing"] = df.apply(
    lambda r: rs_standing(r.p_psia, r.T_F, r.API, r.gamma_g), axis=1)
df["Vasquez-Beggs"] = df.apply(
    lambda r: rs_vasquez_beggs(r.p_psia, r.T_F, r.API, r.gamma_g,
                               r.psep_psia, r.Tsep_F), axis=1)
df["Glaso"] = df.apply(
    lambda r: rs_glaso(r.p_psia, r.T_F, r.API, r.gamma_g), axis=1)
df["Marhoun"] = df.apply(
    lambda r: rs_marhoun(r.p_psia, r.T_F, r.API, r.gamma_g), axis=1)
df["Petrosky-Farshad"] = df.apply(
    lambda r: rs_petrosky_farshad(r.p_psia, r.T_F, r.API, r.gamma_g), axis=1)

methods = ["Standing", "Vasquez-Beggs", "Glaso", "Marhoun", "Petrosky-Farshad"]
print(df[["oil", "Rs_measured"] + methods].round(1).to_string(index=False))
print()
for m in methods:
    print(f"{m:18s} AAE = {aae(df[m], df['Rs_measured']):.2f} %")
