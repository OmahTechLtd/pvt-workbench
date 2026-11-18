"""Error measures for comparing calculated Rs with measured Rs."""

def percent_error(calc, measured):
    """Absolute percent error of one prediction."""
    return abs(calc - measured) / measured * 100

def aae(calc_values, measured_values):
    """Average absolute (percent) error over a set of records."""
    errors = [percent_error(c, m) for c, m in zip(calc_values, measured_values)]
    return sum(errors) / len(errors)
