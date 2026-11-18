import { useSearchParams } from "react-router-dom";
import SingleFluid from "./Singlefluid.jsx";
import OilProperties from "./OilProperties.jsx";
import Dataset from "./Dataset.jsx";

const VIEWS = [
  ["compare", "Compare methods", "Rs, bubble point and Bo from every published correlation that applies, side by side."],
  ["other", "Other properties", "Gravity, compressibility, Bo above the bubble point, density and total formation volume factor."],
  ["data", "Test on data", "Score the correlations against many measured oils, or your own CSV, and see which fits best."],
];

// One page for everything about the oil itself. All views stay mounted so nothing typed is lost when switching.
export default function Properties() {
  const [params, setParams] = useSearchParams();
  const p = params.get("view");
  const view = p === "other" || p === "data" ? p : "compare";

  const pick = (v) => setParams(v === "compare" ? {} : { view: v });

  return (
    <div>
      <h1>Oil Properties</h1>

      <div className="segmented" role="tablist">
        {VIEWS.map(([k, title]) => (
          <button key={k} role="tab" aria-selected={view === k} className={view === k ? "seg active" : "seg"} onClick={() => pick(k)}>
            {title}
          </button>
        ))}
      </div>
      <p className="subtitle">{VIEWS.find(([k]) => k === view)[2]}</p>

      <div style={{ display: view === "compare" ? "block" : "none" }}>
        <SingleFluid embedded />
      </div>
      <div style={{ display: view === "other" ? "block" : "none" }}>
        <OilProperties embedded />
      </div>
      <div style={{ display: view === "data" ? "block" : "none" }}>
        <Dataset embedded />
      </div>
    </div>
  );
}
