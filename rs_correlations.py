"""Solution gas-oil ratio (Rs) correlations.

Every function takes plain numbers and returns Rs in scf/STB.
Unit conversions live in the helpers at the top, so each
correlation only ever sees the units its equation expects.
"""
import math

# ---------- helpers: all unit conversions happen here ----------
def psig_to_psia(p_psig):
    return p_psig + 14.7

def f_to_rankine(t_f):
    return t_f + 460            # the book rounds to 460

def api_to_sg(api):
    return 141.5 / (131.5 + api)

def gas_gravity_at_100psig(gamma_g, api, psep_psia, tsep_f):
    """Eq. 2-71. If separator conditions are unknown, the book allows the unadjusted gas gravity."""
    if psep_psia is None or tsep_f is None or math.isnan(psep_psia) or math.isnan(tsep_f):
        return gamma_g
    return gamma_g * (1 + 5.912e-5 * api * tsep_f * math.log10(psep_psia / 114.7))

# ---------- Standing (1981 form, Eq. 2-69) ----------
def rs_standing(p_psia, t_f, api, gamma_g):
    """Valid at and below the bubble point."""
    x = 0.0125 * api - 0.00091 * t_f
    return gamma_g * ((p_psia / 18.2 + 1.4) * 10 ** x) ** 1.2048

# ---------- Vasquez-Beggs (Eq. 2-70 and 2-71) ----------
def rs_vasquez_beggs(p_psia, t_f, api, gamma_g, psep_psia=None, tsep_f=None):
    """Gas gravity is first corrected to the 100 psig reference
    separator pressure (Eq. 2-71), then Eq. 2-70 is applied."""
    gamma_gs = gas_gravity_at_100psig(gamma_g, api, psep_psia, tsep_f)    
    if api <= 30:
        c1, c2, c3 = 0.0362, 1.0937, 25.7240
    else:
        c1, c2, c3 = 0.0178, 1.1870, 23.931
    t_r = f_to_rankine(t_f)
    return c1 * gamma_gs * p_psia ** c2 * math.exp(c3 * (api / t_r))

# ---------- Glaso (Eq. 2-72) ----------
def rs_glaso(p_psia, t_f, api, gamma_g):
    """The book's page does not label units for Glaso; psia and degF
    are used here, matching the other correlations."""
    x = 2.8869 - (14.1811 - 3.3093 * math.log10(p_psia)) ** 0.5
    pb_star = 10 ** x
    return gamma_g * ((api ** 0.989 / t_f ** 0.172) * pb_star) ** 1.2255

# ---------- Petrosky-Farshad (Eq. 2-74) ----------
def rs_petrosky_farshad(p_psia, t_f, api, gamma_g):
    x = 7.916e-4 * api ** 1.5410 - 4.561e-5 * t_f ** 1.3911
    return ((p_psia / 112.727 + 12.340) * gamma_g ** 0.8439 * 10 ** x) ** 1.73184

# ---------- Marhoun (Eq. 2-73) ----------
def rs_marhoun(p_psia, t_f, api, gamma_g):
    a, b, c, d, e = 185.843208, 1.877840, -3.1437, -1.32657, 1.398441
    gamma_o = api_to_sg(api)
    t_r = f_to_rankine(t_f)
    return (a * gamma_g**b * gamma_o**c * t_r**d * p_psia) ** e
