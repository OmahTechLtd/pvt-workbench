import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import SingleFluid from "./Singlefluid.jsx";
import OilProperties from "./OilProperties.jsx";

const VIEWS = [
  ["compare", "Compare methods", "Rs, bubble point and Bo from every published correlation that applies, side by side"],
  ["other", "Other oil properties", "Gravity, compressibility, Bo above the bubble point, density and total formation volume factor"],
];

// One page for everything about the oil itself. Both views stay mounted so nothing typed is lost when switching.
export default function Properties() {
  const [params, setParams] = useSearchParams();
  const initial = params.get("view") === "other" ? "other" : "compare";
  const [view, setView] = useState(initial);

  const pick = (v) => {
    setView(v);
    setParams(v === "compare" ? {} : { view: v }, { replace: true });
  };

  return (
    <div>
      <h1>Oil Properties</h1>
      <p className="subtitle">
        Estimate the properties of a crude oil from published correlations. Compare several methods on one fluid, or work out a single property from
        the equations in the source. Each calculation is checked against published worked examples.
      </p>

      <div className="viewswitch" role="tablist">
        {VIEWS.map(([k, title, text]) => (
          <button key={k} role="tab" aria-selected={view === k} className={view === k ? "on" : ""} onClick={() => pick(k)}>
            <strong>{title}</strong>
            <span>{text}</span>
          </button>
        ))}
      </div>

      <div style={{ display: view === "compare" ? "block" : "none" }}>
        <SingleFluid embedded />
      </div>
      <div style={{ display: view === "other" ? "block" : "none" }}>
        <OilProperties embedded />
      </div>
    </div>
  );
}
