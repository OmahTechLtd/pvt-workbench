"""Oil formation volume factor (Bo) correlations at the bubble point. Bo is in bbl/STB.

Rs is the solution gas-oil ratio at the bubble point (scf/STB). Temperatures are passed in
degF; each function converts to degR only where its equation needs it. Stock-tank oil
gravity is calculated from API inside each function, as in the Rs and Pb modules.
"""
import math
from rs_correlations import f_to_rankine, api_to_sg, gas_gravity_at_100psig

# ---------- Standing (Eq. 2-84) ----------
def bo_standing(rs, t_f, api, gamma_g):
    gamma_o = api_to_sg(api)
    return 0.9759 + 0.000120 * (rs * (gamma_g / gamma_o) ** 0.5 + 1.25 * t_f) ** 1.2

# ---------- Vasquez-Beggs (Eq. 2-85, gamma_gs from the separator correction) ----------
def bo_vasquez_beggs(rs, t_f, api, gamma_g, psep_psia=None, tsep_f=None):
    gamma_gs = gas_gravity_at_100psig(gamma_g, api, psep_psia, tsep_f)
    if api <= 30:
        c1, c2, c3 = 4.677e-4, 1.751e-5, -1.811e-8
    else:
        c1, c2, c3 = 4.670e-4, 1.100e-5, 1.337e-9
    # (T - 520) with T in degR is the same as (t_f - 60)
    return 1.0 + c1 * rs + (f_to_rankine(t_f) - 520) * (api / gamma_gs) * (c2 + c3 * rs)

# ---------- Glaso (Eq. 2-86 to 2-88) ----------
def bo_glaso(rs, t_f, api, gamma_g):
    gamma_o = api_to_sg(api)
    bob_star = rs * (gamma_g / gamma_o) ** 0.526 + 0.968 * t_f
    log_b = math.log10(bob_star)
    a = -6.58511 + 2.91329 * log_b - 0.27683 * log_b ** 2
    return 1.0 + 10 ** a

# ---------- Marhoun (Eq. 2-89 and 2-90) ----------
def bo_marhoun(rs, t_f, api, gamma_g):
    gamma_o = api_to_sg(api)
    f = rs ** 0.742390 * gamma_g ** 0.323294 * gamma_o ** -1.202040
    t_r = f_to_rankine(t_f)
    return 0.497069 + 0.862963e-3 * t_r + 0.182594e-2 * f + 0.318099e-5 * f ** 2

# ---------- Petrosky-Farshad (Eq. 2-91) ----------
def bo_petrosky_farshad(rs, t_f, api, gamma_g):
    gamma_o = api_to_sg(api)
    inner = rs ** 0.3738 * (gamma_g ** 0.2914 / gamma_o ** 0.6265) + 0.24626 * t_f ** 0.5371
    return 1.0113 + 7.2046e-5 * inner ** 3.0936

# ---------- Material balance (Eq. 2-92), uses the measured oil density ----------
def bo_material_balance(rs, api, gamma_g, rho_o):
    gamma_o = api_to_sg(api)
    return (62.4 * gamma_o + 0.0136 * rs * gamma_g) / rho_o