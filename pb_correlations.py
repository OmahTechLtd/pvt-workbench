"""Bubble-point pressure (Pb) correlations. Every function returns Pb in psia.

Temperatures are passed in degF, and each function converts to degR only where its equation
needs it. Rs is the measured (or estimated) solution gas-oil ratio, scf/STB.
"""
import math
from rs_correlations import f_to_rankine, api_to_sg, gas_gravity_at_100psig

# ---------- Standing (Eq. 2-76 and 2-77) ----------
def pb_standing(rs, t_f, api, gamma_g):
    a = 0.00091 * t_f - 0.0125 * api
    return 18.2 * ((rs / gamma_g) ** 0.83 * 10 ** a - 1.4)

# ---------- Vasquez-Beggs (Eq. 2-78, with gamma_gs from Eq. 2-71) ----------
def pb_vasquez_beggs(rs, t_f, api, gamma_g, psep_psia=None, tsep_f=None):
    gamma_gs = gas_gravity_at_100psig(gamma_g, api, psep_psia, tsep_f)
    if api <= 30:
        c1, c2, c3 = 27.624, 0.914328, 11.172
    else:
        c1, c2, c3 = 56.18, 0.84246, 10.393
    a = -c3 * api / f_to_rankine(t_f)
    return ((c1 * rs / gamma_gs) * 10 ** a) ** c2

# ---------- Glaso (Eq. 2-79 and 2-80) ----------
def pb_glaso(rs, t_f, api, gamma_g, volatile_oil=False):
    a, b, c = 0.816, 0.172, -0.989
    if volatile_oil:
        b = 0.130          # Glaso's recommendation for volatile oils
    pb_star = (rs / gamma_g) ** a * t_f ** b * api ** c
    # NOTE: the book prints (pb*)^2 in Eq. 2-79; Glaso's original is [log(pb*)]^2
    log_pb = 1.7669 + 1.7447 * math.log10(pb_star) - 0.30218 * math.log10(pb_star) ** 2
    return 10 ** log_pb

# ---------- Marhoun (Eq. 2-81) ----------
def pb_marhoun(rs, t_f, api, gamma_g):
    a, b, c, d, e = 5.38088e-3, 0.715082, -1.87784, 3.1437, 1.32657
    gamma_o = api_to_sg(api)
    return a * rs ** b * gamma_g ** c * gamma_o ** d * f_to_rankine(t_f) ** e

# ---------- Petrosky-Farshad (Eq. 2-82, x from Eq. 2-74) ----------
def pb_petrosky_farshad(rs, t_f, api, gamma_g):
    x = 7.916e-4 * api ** 1.5410 - 4.561e-5 * t_f ** 1.3911
    return 112.727 * rs ** 0.577421 / (gamma_g ** 0.8439 * 10 ** x) - 1391.051