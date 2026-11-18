from rs_correlations import (rs_standing, rs_vasquez_beggs, rs_glaso, rs_petrosky_farshad, rs_marhoun)
from pb_correlations import (pb_standing, pb_vasquez_beggs, pb_glaso, pb_marhoun, pb_petrosky_farshad)
from bo_correlations import (bo_standing, bo_vasquez_beggs, bo_glaso, bo_marhoun, bo_petrosky_farshad)
from metrics import aae

RS_REGISTRY = {
    "Standing": {
        "name": "Standing (1981)",
        "func": rs_standing,
        "inputs": ["p_psia", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-69, p. 71",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-69, p. 71",
    },

    "Vasquez-Beggs": {
        "name": "Vasquez-Beggs (1980)",
        "func": rs_vasquez_beggs,
        "inputs": ["p_psia", "t_f", "api", "gamma_g"],
        "optional_inputs": ["psep_psia", "tsep_f"],
        "source": "Ahmed, Tarek. Eq. 2-70 and 2-71, p. 73",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-70 and 2-71, p. 73",
    },

    "Glaso": {
        "name": "Glaso (1980)",
        "func": rs_glaso,
        "inputs": ["p_psia", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-72, p. 74",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-72, p. 74",
    },

    "Marhoun": {
        "name": "Marhoun (1988)",
        "func": rs_marhoun,
        "inputs": ["p_psia", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-73, p. 75",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-73, p. 75",
    },

    "Petrosky-Farshad": {
        "name": "Petrosky-Farshad (1993)",
        "func": rs_petrosky_farshad,
        "inputs": ["p_psia", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-74, p. 76",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-74, p. 76",
    },
}

PB_REGISTRY = {
    "Standing": {
        "name": "Standing (1981)",
        "func": pb_standing,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-76 and 2-77, p. 78",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-76 and 2-77, p. 78",
    },

    "Vasquez-Beggs": {
        "name": "Vasquez-Beggs (1980)",
        "func": pb_vasquez_beggs,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "optional_inputs": ["psep_psia", "tsep_f"],
        "source": "Ahmed, Tarek. Eq. 2-78, p. 80",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-78, p. 80",
    },

    "Glaso": {
        "name": "Glaso (1980)",
        "func": pb_glaso,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-79 and 2-80, p. 81",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-79 and 2-80, p. 81",
    },

    "Marhoun": {
        "name": "Marhoun (1988)",
        "func": pb_marhoun,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-81, p. 82",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-81, p. 82",
    },

    "Petrosky-Farshad": {
        "name": "Petrosky-Farshad (1993)",
        "func": pb_petrosky_farshad,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-82, p. 83",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-82, p. 83",
    },
}

BO_REGISTRY = {
    "Standing": {
        "name": "Standing (1981)",
        "func": bo_standing,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-84, p.85",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-84, p.85",
    },

    "Vasquez-Beggs": {
        "name": "Vasquez-Beggs (1980)",
        "func": bo_vasquez_beggs,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "optional_inputs": ["psep_psia", "tsep_f"],
        "source": "Ahmed, Tarek. Eq. 2-85, p. 85",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-85, p. 85",
    },  

    "Glaso": {
        "name": "Glaso (1980)",
        "func": bo_glaso,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-86 to 2-88, p. 86",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-86 to 2-88, p. 86",   
    },

    "Marhoun": {
        "name": "Marhoun (1988)",
        "func": bo_marhoun,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-89 and 2-90, p. 87",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-89 and 2-90, p. 87",
    },

    "Petrosky-Farshad": {
        "name": "Petrosky-Farshad (1993)",
        "func": bo_petrosky_farshad,
        "inputs": ["rs_measured", "t_f", "api", "gamma_g"],
        "source": "Ahmed, Tarek. Eq. 2-91, p. 87",
        "valid_range": "none specified",
        "status": "verified against example data from Ahmed, Tarek. Eq. 2-91, p. 87",
    }
}

REGISTRIES = {"rs": RS_REGISTRY, "pb": PB_REGISTRY, "bo": BO_REGISTRY}
MEASURED_COLUMN = {"rs": "rs_measured", "pb": "p_psia", "bo": "bo"}
UNITS = {"rs": "scf/STB", "pb": "psia", "bo": "bbl/STB"}
NAMES = {"rs": "Rs", "pb": "Pb", "bo": "Bo"}

def run_method(key, row, registry=RS_REGISTRY):
    entry = registry[key]
    values = [row[data] for data in entry["inputs"]]
    values += [row.get(name) for name in entry.get("optional_inputs", [])]
    return entry["func"](*values)

def calc_aae(df, method, prop="rs"):
    return aae(df[f"{method}_{prop}"], df[MEASURED_COLUMN[prop]])