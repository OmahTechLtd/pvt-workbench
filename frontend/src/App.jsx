import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import SingleFluid from "./pages/Singlefluid.jsx";
import Placeholder from "./pages/Placeholder.jsx";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/single", label: "Single Fluid Analysis" },
  { to: "/dataset", label: "Dataset Analysis" },
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
          <Route path="/dataset" element={<Placeholder title="Dataset Analysis" />} />
          <Route path="/library" element={<Placeholder title="Method Library" />} />
          <Route path="/about" element={<Placeholder title="About" />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;