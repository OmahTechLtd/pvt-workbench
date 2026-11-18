import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import SingleFluid from "./pages/Singlefluid.jsx";
import Dataset from "./pages/Dataset.jsx";
import Classification from "./pages/Classification.jsx";
import PlusFraction from "./pages/PlusFraction.jsx";
import PhaseDiagram from "./pages/PhaseDiagram.jsx";
import OilProperties from "./pages/OilProperties.jsx";
import Viscosity from "./pages/Viscosity.jsx";
import LabPVT from "./pages/LabPVT.jsx";
import MaterialBalance from "./pages/MaterialBalance.jsx";
import SurfaceTension from "./pages/SurfaceTension.jsx";
import Placeholder from "./pages/Placeholder.jsx";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/single", label: "Single Fluid Analysis" },
  { to: "/dataset", label: "Dataset Analysis" },
  { to: "/classification", label: "Oil Classification" },
  { to: "/phase", label: "Phase Diagrams" },
  { to: "/fraction", label: "Plus Fraction" },
  { to: "/properties", label: "Oil Properties" },
  { to: "/viscosity", label: "Oil Viscosity" },
  { to: "/lab", label: "Lab PVT Analysis" },
  { to: "/balance", label: "Material Balance" },
  { to: "/tension", label: "Surface Tension" },
  { to: "/library", label: "Method Library" },
  { to: "/about", label: "About" },
];

function App() {
  return (
    <div className="layout">
      <nav className="sidebar">
        <h2>PVT Workbench</h2>
        {NAV.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === "/"}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/single" element={<SingleFluid />} />
          <Route path="/dataset" element={<Dataset />} />
          <Route path="/classification" element={<Classification />} />
          <Route path="/phase" element={<PhaseDiagram />} />
          <Route path="/fraction" element={<PlusFraction />} />
          <Route path="/properties" element={<OilProperties />} />
          <Route path="/viscosity" element={<Viscosity />} />
          <Route path="/lab" element={<LabPVT />} />
          <Route path="/balance" element={<MaterialBalance />} />
          <Route path="/tension" element={<SurfaceTension />} />
          <Route path="/library" element={<Placeholder title="Method Library" />} />
          <Route path="/about" element={<Placeholder title="About" />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;