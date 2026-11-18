import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Dataset from "./pages/Dataset.jsx";
import Classification from "./pages/Classification.jsx";
import PlusFraction from "./pages/PlusFraction.jsx";
import PhaseDiagram from "./pages/PhaseDiagram.jsx";
import Properties from "./pages/Properties.jsx";
import Viscosity from "./pages/Viscosity.jsx";
import LabPVT from "./pages/LabPVT.jsx";
import MaterialBalance from "./pages/MaterialBalance.jsx";
import SurfaceTension from "./pages/SurfaceTension.jsx";
import Library from "./pages/Library.jsx";
import About from "./pages/About.jsx";
import { GROUPS } from "./nav.js";

function useTheme() {
  const [theme, setTheme] = useState(() => {
    try {
      const t = localStorage.getItem("pvt-theme");
      return t === "light" || t === "dark" ? t : "auto";
    } catch (e) {
      return "auto";
    }
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "auto") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      if (theme === "auto") localStorage.removeItem("pvt-theme");
      else localStorage.setItem("pvt-theme", theme);
    } catch (e) {
      /* storage can be blocked, the theme still applies for this visit */
    }
  }, [theme]);
  return [theme, setTheme];
}

function App() {
  const [theme, setTheme] = useTheme();
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  useEffect(() => {
    setOpen(false);
    window.scrollTo(0, 0);
  }, [loc.pathname]);

  return (
    <div className="layout">
      <nav className={"sidebar" + (open ? " open" : "")} aria-label="Main">
        <Link to="/" className="brand">
          <strong>PVT Workbench</strong>
          <span>Estimate. Compare. Evaluate.</span>
        </Link>
        <button className="menubtn" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
          {open ? "Close" : "Menu"}
        </button>
        <div className="navwrap">
          <div className="navgroup">
            <NavLink to="/" end className="navlink">
              Home
            </NavLink>
          </div>
          {GROUPS.map((g, i) => (
            <div className="navgroup" key={g.title}>
              <h3>
                {g.step ? <b>{g.step}</b> : null}
                {g.title}
              </h3>
              {g.items.map((item) => (
                <NavLink key={item.to} to={item.to} className="navlink">
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
          <div className="sidebar-foot">
            <small>Appearance</small>
            <div className="themeswitch" role="group" aria-label="Theme">
              {[["auto", "Auto"], ["light", "Light"], ["dark", "Dark"]].map(([k, l]) => (
                <button key={k} className={theme === k ? "on" : ""} onClick={() => setTheme(k)} aria-pressed={theme === k}>
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/single" element={<Navigate to="/properties" replace />} />
          <Route path="/dataset" element={<Dataset />} />
          <Route path="/classification" element={<Classification />} />
          <Route path="/phase" element={<PhaseDiagram />} />
          <Route path="/fraction" element={<PlusFraction />} />
          <Route path="/properties" element={<Properties />} />
          <Route path="/viscosity" element={<Viscosity />} />
          <Route path="/lab" element={<LabPVT />} />
          <Route path="/balance" element={<MaterialBalance />} />
          <Route path="/tension" element={<SurfaceTension />} />
          <Route path="/library" element={<Library />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
