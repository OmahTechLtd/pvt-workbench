import { Link } from "react-router-dom";
import { GROUPS } from "../nav.js";

const STARTS = [
  { to: "/properties/rs", title: "Gravity, gas-oil ratio and temperature", text: "Estimate Rs, bubble point and Bo with every method that applies, side by side." },
  { to: "/lab", title: "A PVT lab report", text: "Check it for consistency and adjust it to a new bubble point or separator conditions." },
  { to: "/balance", title: "Production history", text: "Find the oil in place and see which drive is pushing the reservoir." },
];

function Row({ to, title, text }) {
  return (
    <Link to={to} className="row">
      <strong>{title}</strong>
      <span>{text}</span>
      <i>&rarr;</i>
    </Link>
  );
}

export default function Home() {
  return (
    <div>
      <h1>PVT Workbench</h1>
      <p className="subtitle">
        Published oil PVT correlations, coded from their sources and checked against the worked examples printed there. Compare them on your own
        fluid, check a lab report, and carry the result into material balance.
      </p>

      <div className="sectionlabel">Start from what you have</div>
      <div className="index">
        {STARTS.map((s) => (
          <Row key={s.to} {...s} />
        ))}
      </div>

      <div className="sectionlabel">Everything in the workbench</div>
      <div className="index">
        {GROUPS.map((g) => (
          <div key={g.title}>
            <div className="head">{g.title}</div>
            {g.items.map((i) => (
              <Row key={i.to} to={i.to} title={i.label} text={i.text} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
