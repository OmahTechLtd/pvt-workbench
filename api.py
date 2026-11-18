import math

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from registry import REGISTRIES, run_method

app = FastAPI(title="Oil Properties Workbench API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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