import matplotlib.pyplot as plt
from registry import UNITS, MEASURED_COLUMN, NAMES

def cross_plot(df, method, prop="rs"):
    calculated = df[f"{method}_{prop}"]
    measured = df[MEASURED_COLUMN[prop]]

    plt.scatter(measured, calculated)   # x is measured, y is calculated
    top = max(measured.max(), calculated.max())
    bottom = min(measured.min(), calculated.min())
    plt.plot([bottom, top], [bottom, top])   # the perfect-prediction line
    plt.xlabel(f"Measured {NAMES[prop]} ({UNITS[prop]})")
    plt.ylabel(f"{method} {NAMES[prop]} ({UNITS[prop]})")
    plt.title(method)
    plt.show()

def compare_plot(df, methods, prop="rs"):
    measured = df[MEASURED_COLUMN[prop]]
    bottom, top = measured.min(), measured.max()

    fig, ax = plt.subplots()
    for method in methods:
        calculated = df[method + "_" + prop]
        ax.scatter(measured, calculated, label=method)
        top = max(top, df[method + "_" + prop].max())
        bottom = min(bottom, df[method + "_" + prop].min())

    ax.plot([bottom, top], [bottom, top], color="black", linestyle="--", label="Perfect prediction")
    ax.set_xlabel(f"Measured {NAMES[prop]} ({UNITS[prop]})")
    ax.set_ylabel(f"Calculated {NAMES[prop]} ({UNITS[prop]})")
    ax.legend()
    ax.set_title(f"Comparison of {NAMES[prop]} prediction methods")
    plt.show()
    return fig