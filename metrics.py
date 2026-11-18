"""Error measures for comparing calculated values with measured values."""

import numpy as np


def percent_error(calc, measured):
    """Absolute percent error of one prediction."""
    return abs(calc - measured) / measured * 100

def aae(calc_values, measured_values):
    """Average absolute (percent) error over a set of records."""
    errors = [percent_error(c, m) for c, m in zip(calc_values, measured_values)]
    return sum(errors) / len(errors)


def summarize_errors(calc, measured):
    """Summary error measures for one method over many records.

    Error is calculated minus measured, so a positive bias means the method
    overpredicts. AAE is the mean absolute relative error in percent and
    matches aae() above. MAE, RMSE and bias are in the property's own units.
    Records where either value is missing, or the measured value is zero,
    are left out, and n counts only the records actually used.
    """
    c = np.asarray(calc, dtype=float)
    m = np.asarray(measured, dtype=float)
    ok = np.isfinite(c) & np.isfinite(m) & (m != 0)
    c, m = c[ok], m[ok]
    if len(m) == 0:
        return {"n": 0, "aae": None, "mae": None, "rmse": None, "bias": None}
    err = c - m
    rel = err / m * 100
    return {
        "n": int(len(m)),
        "aae": float(np.mean(np.abs(rel))),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "bias": float(np.mean(err)),
    }