import { useState } from "react";
import { Navigate, useParams } from "react-router-dom";
import SingleFluid from "./Singlefluid.jsx";
import OilProperties from "./OilProperties.jsx";
import Viscosity from "./Viscosity.jsx";
import SurfaceTension from "./SurfaceTension.jsx";
import Dataset from "./Dataset.jsx";

// One page per oil property, in the order of the source list. A page with several modes shows them as tabs.
// Calculate and Test on data sit side by side wherever there are correlations to score on measured data.
export const PAGES = {
  gravity: {
    title: "Oil gravity",
    modes: [["Calculate", <OilProperties embedded only="gravity" />]],
  },
  gasgravity: {
    title: "Solution gas gravity",
    modes: [["Calculate", <OilProperties embedded only="gasgravity" />]],
  },
  rs: {
    title: "Gas solubility, Rs",
    about: "How much gas is dissolved in the oil at a given pressure.",
    modes: [
      ["Calculate", <SingleFluid embedded fixedProp="rs" />],
      ["Test on data", <Dataset embedded fixedProp="rs" />],
    ],
  },
  pb: {
    title: "Bubble-point pressure, Pb",
    about: "The pressure at which the first gas comes out of the oil.",
    modes: [
      ["Calculate", <SingleFluid embedded fixedProp="pb" />],
      ["Test on data", <Dataset embedded fixedProp="pb" />],
    ],
  },
  bo: {
    title: "Oil formation volume factor, Bo",
    about: "How much a barrel of stock tank oil swells at reservoir conditions.",
    modes: [
      ["Saturated oil", <SingleFluid embedded fixedProp="bo" />],
      ["Above the bubble point", <OilProperties embedded only="bo" />],
      ["Test on data", <Dataset embedded fixedProp="bo" />],
    ],
  },
  co: {
    title: "Compressibility of oil",
    modes: [["Calculate", <OilProperties embedded only="co" />]],
  },
  rho: {
    title: "Oil density",
    modes: [["Calculate", <OilProperties embedded only="rho" />]],
  },
  bt: {
    title: "Total formation volume factor",
    modes: [["Calculate", <OilProperties embedded only="bt" />]],
  },
  viscosity: {
    title: "Crude oil viscosity",
    modes: [["Calculate", <Viscosity embedded />]],
  },
  tension: {
    title: "Surface tension",
    modes: [["Calculate", <SurfaceTension embedded />]],
  },
};

function Body({ page }) {
  const [mode, setMode] = useState(0);
  return (
    <div>
      <h1>{page.title}</h1>
      {page.about && <p className="subtitle">{page.about}</p>}
      {page.modes.length > 1 && (
        <div className="segmented" role="tablist">
          {page.modes.map(([label], i) => (
            <button key={label} role="tab" aria-selected={mode === i} className={mode === i ? "seg active" : "seg"} onClick={() => setMode(i)}>
              {label}
            </button>
          ))}
        </div>
      )}
      {page.modes.map(([label, el], i) => (
        <div key={label} style={{ display: mode === i ? "block" : "none" }}>
          {el}
        </div>
      ))}
    </div>
  );
}

export default function Property() {
  const { key } = useParams();
  const page = PAGES[key];
  if (!page) return <Navigate to="/properties/rs" replace />;
  return <Body key={key} page={page} />;
}

// Old links (/properties?view=...) go to the matching property page.
export function PropertiesRedirect() {
  const v = new URLSearchParams(window.location.search).get("view");
  const map = { compare: "rs", other: "gravity", viscosity: "viscosity", tension: "tension", data: "bo" };
  return <Navigate to={"/properties/" + (map[v] || "rs")} replace />;
}
