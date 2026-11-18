"""Oil viscosity correlations from Ahmed, Reservoir Engineering Handbook, 5th ed., pp. 105-109.
Temperatures are in degF (converted to degR inside where the book uses T in degR). Viscosity in cp."""
import math


def mu_dead_beal(api, t_f):
    """Beal (1946), as curve-fit by Standing. Eq. printed in Example 2-36, p. 108."""
    t_r = t_f + 460
    a = 10 ** (0.43 + 8.33 / api)
    return (0.32 + 1.8e7 / api ** 4.53) * (360 / (t_r - 260)) ** a


def mu_dead_beggs_robinson(api, t_f):
    """Beggs and Robinson (1975). x = Y T^-1.163 with T in degF; the book prints (T - 460) with T in degR."""
    z = 3.0324 - 0.02023 * api
    y = 10 ** z
    x = y * t_f ** -1.163
    return 10 ** x - 1


def mu_dead_glaso(api, t_f):
    """Glaso (1980). Temperature in degF; the book prints (T - 460) with T in degR."""
    a = 10.313 * math.log10(t_f) - 36.447
    return 3.141e10 * t_f ** -3.444 * math.log10(api) ** a


def mu_sat_chew_connally(mu_od, rs):
    """Chew and Connally (1959), Eq. 2-109 with the Standing curve fit."""
    a = rs * (2.2e-7 * rs - 7.4e-4)
    c = 8.62e-5 * rs
    d = 1.1e-3 * rs
    e = 3.74e-3 * rs
    b = 0.68 / 10 ** c + 0.25 / 10 ** d + 0.062 / 10 ** e
    return 10 ** a * mu_od ** b


def mu_sat_beggs_robinson(mu_od, rs):
    """Beggs and Robinson (1975), Eq. 2-120."""
    a = 10.715 * (rs + 100) ** -0.515
    b = 5.44 * (rs + 150) ** -0.338
    return a * mu_od ** b


def mu_under_beal(mu_ob, p, pb):
    """Beal (1946) curve-fit by Standing (1981), p. 107."""
    return mu_ob + 0.001 * (p - pb) * (0.024 * mu_ob ** 1.6 + 0.038 * mu_ob ** 0.56)


def mu_under_vasquez_beggs(mu_ob, p, pb, m_coeff=2.6):
    """Vasquez and Beggs (1980), Eq. 2-121. The coefficient is 2.6 on p. 107 and 26 in Example 2-36 on p. 109."""
    a = -3.9e-5 * p - 5
    m = m_coeff * p ** 1.187 * 10 ** a
    return mu_ob * (p / pb) ** m
