import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyze import AnalyzeRequest, analyze, builtin_summary
from classification import ClassifyRequest, classify_dataset, classify_endpoint, criteria
from oil_properties import (Inputs, compute_bo_above_pb, compute_compressibility, compute_density, compute_gravity,
                            compute_total_fvf, property_checks)
from plus_fraction import FractionRequest, fraction_characterize, verification as fraction_checks
from registry import REGISTRIES, run_method
from surface_tension import TensionIn, compute_tension, tension_components
from viscosity import ViscosityIn, compute_viscosity, viscosity_checks

app = FastAPI(title="Oil Properties Workbench API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Methods and single-fluid calculation ----

class CalcRequest(BaseModel):
    prop: str
    methods: list[str]
    inputs: dict[str, float]


@app.get("/methods")
def list_methods():
    return {
        prop: [
            {
                "key": key,
                "name": entry["name"],
                "inputs": entry["inputs"],
                "optional_inputs": entry.get("optional_inputs", []),
                "source": entry["source"],
                "status": entry["status"],
            }
            for key, entry in registry.items()
        ]
        for prop, registry in REGISTRIES.items()
    }


@app.post("/calculate")
def calculate(req: CalcRequest):
    if req.prop not in REGISTRIES:
        raise HTTPException(status_code=404, detail=f"Unknown property: {req.prop}")
    registry = REGISTRIES[req.prop]

    results = []
    for key in req.methods:
        if key not in registry:
            raise HTTPException(status_code=404, detail=f"Unknown method: {key}")
        entry = registry[key]
        missing = [name for name in entry["inputs"] if name not in req.inputs]
        if missing:
            results.append({"key": key, "value": None, "error": "Missing inputs: " + ", ".join(missing)})
        else:
            try:
                value = run_method(key, req.inputs, registry)
                if not math.isfinite(value):
                    raise ValueError("result is not a finite number")
                results.append({"key": key, "value": value, "error": None})
            except (ValueError, ZeroDivisionError, OverflowError, TypeError) as e:
                results.append({"key": key, "value": None, "error": f"Could not calculate: {e}"})
    return {"prop": req.prop, "results": results}


# ---- Dataset analysis ----

@app.get("/dataset/builtin")
def dataset_builtin():
    return builtin_summary()


@app.post("/analyze")
def analyze_dataset(req: AnalyzeRequest):
    return analyze(req)


# ---- Oil classification ----

@app.post("/classify")
def classify(req: ClassifyRequest):
    return classify_endpoint(req)


@app.get("/classify/criteria")
def classify_criteria():
    return criteria()


@app.get("/classify/dataset")
def classify_builtin_dataset(exclude_duplicates: bool = True):
    return classify_dataset(exclude_duplicates)


# ---- Plus fraction ----

@app.post("/fraction/characterize")
def fraction(req: FractionRequest):
    return fraction_characterize(req)


@app.get("/fraction/verification")
def fraction_verification():
    return fraction_checks()


# ---- Oil properties ----

@app.post("/props/gravity")
def props_gravity(i: Inputs):
    return compute_gravity(i)


@app.post("/props/compressibility")
def props_compressibility(i: Inputs):
    return compute_compressibility(i)


@app.post("/props/bo_under")
def props_bo_above_pb(i: Inputs):
    return compute_bo_above_pb(i)


@app.post("/props/density")
def props_density(i: Inputs):
    return compute_density(i)


@app.post("/props/bt")
def props_total_fvf(i: Inputs):
    return compute_total_fvf(i)


@app.get("/props/verification")
def props_verification():
    return property_checks()


# ---- Viscosity ----

@app.post("/viscosity/compute")
def viscosity(i: ViscosityIn):
    return compute_viscosity(i)


@app.get("/viscosity/verification")
def viscosity_verification():
    return viscosity_checks()


# ---- Surface tension ----

@app.get("/tension/components")
def tension_component_list():
    return tension_components()


@app.post("/tension/compute")
def tension(i: TensionIn):
    return compute_tension(i)
