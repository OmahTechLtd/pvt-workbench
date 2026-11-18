import { Link } from "react-router-dom";
import { GROUPS } from "../nav.js";

const STARTS = [
  { to: "/single", title: "I have gravity, gas-oil ratio and temperature", text: "Estimate Rs, bubble point and Bo with every method that applies, side by side." },
  { to: "/lab", title: "I have a PVT lab report", text: "Check the report for consistency and adjust it to a new bubble point or separator conditions." },
  { to: "/balance", title: "I have production history", text: "Find the oil in place and see which drive is pushing the reservoir." },
];

export default function Home() {
  return (
    <div>
      <section className="hero">
        <p className="tag">Estimate. Compare. Evaluate.</p>
        <h1>PVT Workbench</h1>
        <p className="subtitle" style={{ fontSize: 17 }}>
          Published oil PVT correlations, coded from their sources and checked against the worked examples printed there. Compare them on your own fluid,
          check a lab report, and carry the result into material balance.
        </p>
      </section>

      <h3>Where are you starting from?</h3>
      <div className="steps">
        {STARTS.map((s) => (
          <Link to={s.to} className="step" key={s.to}>
            <strong>{s.title}</strong>
            <p>{s.text}</p>
            <small>Open →</small>
          </Link>
        ))}
      </div>

      <h3>The path through the workbench</h3>
      <p className="muted">Work down the list, or jump to the step you need. Each page says where its method comes from and shows its own checks at the bottom.</p>
      <div className="steps">
        {GROUPS.filter((g) => g.step).map((g) => (
          <div className="step" key={g.title} style={{ cursor: "default" }}>
            <span className="n">{g.step}</span>
            <strong>{g.title}</strong>
            <p>{g.blurb}</p>
            {g.items.map((i) => (
              <div key={i.to} style={{ marginTop: 6 }}>
                <Link to={i.to}>{i.label}</Link>
              </div>
            ))}
          </div>
        ))}
      </div>

      <p className="note">
        New here? <Link to="/library">The Method Library</Link> lists every correlation and where it comes from, and <Link to="/about">About</Link> explains how the checks work and what the tool does not do.
      </p>
    </div>
  );
}
