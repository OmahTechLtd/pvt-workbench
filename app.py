import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from rs_correlations import psig_to_psia
from registry import BO_REGISTRY, RS_REGISTRY, PB_REGISTRY, REGISTRIES,run_method, calc_aae
from plots import compare_plot

st.title("Solution Gas-Oil Ratio Workbench")

df = pd.read_csv("data/example_2_16.csv")
df.columns = df.columns.str.lower()
df["p_psia"] = df["pb_psig"].apply(psig_to_psia)
df["psep_psia"] = df["psep_psig"].apply(psig_to_psia)

prop = st.radio("Property to estimate", ["Rs", "Pb", "Bo"])
suffix = prop.lower()
registry = REGISTRIES[suffix]
methods = st.multiselect("Methods", list(registry), default=list(registry))

for key in methods:
    df[f"{key}_{suffix}"] = df.apply(lambda row: run_method(key, row, registry), axis=1)

measured = "rs_measured" if suffix == "rs" else "p_psia"
columns = ["oil", measured] + [f"{k}_{suffix}" for k in methods]
st.subheader("Predictions")
st.dataframe(df[columns].round(1))

st.subheader("Average absolute error (%)")
aae_table = pd.DataFrame({
    "Method": methods,
    "AAE (%)": [round(calc_aae(df, m, suffix), 2) for m in methods],
})
st.table(aae_table)

st.subheader("Predicted versus measured")
if methods:
    fig = compare_plot(df, methods, suffix)
    st.pyplot(fig)
    plt.close(fig)
else:
    st.info("Select at least one method to see the chart.")