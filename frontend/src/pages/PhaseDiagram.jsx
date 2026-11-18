import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

const API = "http://127.0.0.1:8000";

// Drawing area inside the SVG
const W = 640;
const H = 400;
const L = 54;
const R = 620;
const T = 16;
const B = 356;
const X = (u) => L + u * (R - L);
const Y = (v) => B - v * (B - T);

// Shapes only. cx and cy place the critical point, s widens the envelope, tRes is the
// reservoir temperature, and t lists where the quality lines meet the bottom edge,
// from the bubble-point end (0) to the dew-point end (1).
const TYPES = [
  {
    key: "ordinary_black",
    name: "Ordinary black oil",
    cx: 0.62, cy: 0.66, s: 1.0, tRes: 0.28,
    t: [0.2, 0.4, 0.6, 0.8],
    spacing: "Quality lines are roughly evenly spaced.",
  },
  {
    key: "low_shrinkage",
    name: "Low-shrinkage oil",
    cx: 0.62, cy: 0.64, s: 0.9, tRes: 0.25,
    t: [0.72, 0.8, 0.87, 0.93],
    spacing: "Quality lines are closely spaced near the dew-point curve.",
  },
  {
    key: "volatile",
    name: "Volatile oil",
    cx: 0.56, cy: 0.68, s: 0.95, tRes: 0.36, left: true,
    t: [0.04, 0.09, 0.16, 0.3, 0.5],
    spacing: "Quality lines are close together near the bubble-point curve and more widely spaced at lower pressures.",
  },
  {
    key: "near_critical",
    name: "Near-critical oil",
    cx: 0.54, cy: 0.7, s: 0.9, tRes: 0.505, left: true, cbLeft: true,
    t: [0.03, 0.06, 0.1, 0.2, 0.4],
    spacing: "All quality lines converge at the critical point, and the reservoir temperature is just below it.",
  },
];

const SHRINKAGE = {
  ordinary_black: (p) => 100 - 30 * (1 - p),
  low_shrinkage: (p) => 100 - 15 * (1 - p),
  volatile: (p) => (p > 0.88 ? 100 - ((1 - p) / 0.12) * 30 : 70 - ((0.88 - p) / 0.88) * 40),
  near_critical: (p) => (p > 0.96 ? 100 - ((1 - p) / 0.04) * 45 : 55 - ((0.96 - p) / 0.96) * 40),
};
const SHRINK_COLOURS = {
  ordinary_black: "#2563eb",
  low_shrinkage: "#0f766e",
  volatile: "#d97706",
  near_critical: "#9333ea",
};

function quad(p0, p1, p2, n = 30) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const a = (1 - t) * (1 - t);
    const b = 2 * (1 - t) * t;
    const c = t * t;
    pts.push([a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1]]);
  }
  return pts;
}

function cubic(p0, p1, p2, p3, n = 40) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const a = (1 - t) ** 3;
    const b = 3 * (1 - t) ** 2 * t;
    const c = 3 * (1 - t) * t * t;
    const d = t ** 3;
    pts.push([
      a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
      a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
    ]);
  }
  return pts;
}

function geometry(type) {
  const { cx, cy, s } = type;
  const A = [cx - 0.56 * s, 0.03];
  const D = [cx - 0.13 * s, cy + 0.13];
  const C = [cx, cy];
  const E = [cx + 0.19 * s, cy - 0.3];
  const Bp = [cx + 0.27 * s, 0.03];
  const bubble = [
    ...cubic(A, [A[0] + 0.1 * s, A[1] + 0.36], [D[0] - 0.14 * s, D[1] - 0.24], D),
    ...quad(D, [cx - 0.04 * s, cy + 0.15], C).slice(1),
  ];
  const dew = [
    ...quad(C, [cx + 0.07 * s, cy - 0.03], E),
    ...cubic(E, [E[0] + 0.02 * s, E[1] - 0.12], [Bp[0] - 0.01 * s, Bp[1] + 0.14], Bp).slice(1),
  ];
  const quality = type.t.map((t) => {
    const Q = [A[0] + t * (Bp[0] - A[0]), 0.03];
    const ctrl = [(C[0] + Q[0]) / 2 + 0.03 * s, Q[1] + (C[1] - Q[1]) * 0.28];
    return quad(C, ctrl, Q, 30);
  });
  return { A, D, C, E, B: Bp, bubble, dew, quality };
}

function crossing(poly, u) {
  for (let i = 0; i < poly.length - 1; i++) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[i + 1];
    if ((x1 - u) * (x2 - u) <= 0 && x1 !== x2) {
      return y1 + ((u - x1) / (x2 - x1)) * (y2 - y1);
    }
  }
  return null;
}

const path = (pts) => "M" + pts.map(([u, v]) => `${X(u).toFixed(1)},${Y(v).toFixed(1)}`).join("L");

function Envelope({ type }) {
  const g = geometry(type);
  const pb = crossing(g.bubble, type.tRes);
  const pi = pb === null ? null : Math.min(pb + 0.14, 0.97);
  const region = [...g.bubble, ...g.dew.slice(1), [g.A[0], 0.03]];
  const label = (u, v, text, opts = {}) => (
    <text x={X(u)} y={Y(v)} fontSize="12" fill="#374151" textAnchor={opts.anchor || "start"} {...opts.props}>
      {text}
    </text>
  );
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`Schematic p-T diagram for ${type.name}`}>
      <rect x={L} y={T} width={R - L} height={B - T} fill="#fff" stroke="#9ca3af" />
      <path d={path(region) + "Z"} fill="#eff6ff" stroke="none" />
      {g.quality.map((q, i) => (
        <path key={i} d={path(q)} fill="none" stroke="#9ca3af" strokeWidth="1" strokeDasharray="4 3" />
      ))}
      <path d={path(g.bubble)} fill="none" stroke="#2563eb" strokeWidth="2.5" />
      <path d={path(g.dew)} fill="none" stroke="#b45309" strokeWidth="2.5" />

      {/* reservoir temperature and pressure decline */}
      <line x1={X(type.tRes)} x2={X(type.tRes)} y1={Y(0.97)} y2={Y(0.06)} stroke="#111827" strokeWidth="1.5" />
      {pb !== null && (
        <>
          <circle cx={X(type.tRes)} cy={Y(pi)} r="5" fill="#111827" />
          <circle cx={X(type.tRes)} cy={Y(pb)} r="5" fill="#fff" stroke="#111827" strokeWidth="2" />
          {label(type.left ? type.tRes - 0.015 : type.tRes + 0.015, pi, "Initial pressure, pi", { anchor: type.left ? "end" : "start" })}
          {label(type.left ? type.tRes - 0.015 : type.tRes + 0.015, type.left ? pb : pb - 0.035, "Bubble point, pb", { anchor: type.left ? "end" : "start" })}
        </>
      )}
      <text x={X(type.tRes) - 6} y={Y(0.1)} fontSize="12" fill="#374151" textAnchor="end">
        Reservoir
      </text>
      <text x={X(type.tRes) - 6} y={Y(0.1) + 14} fontSize="12" fill="#374151" textAnchor="end">
        temperature
      </text>

      <circle cx={X(g.C[0])} cy={Y(g.C[1])} r="5" fill="#dc2626" />
      {label(g.C[0] + 0.015, g.C[1] + 0.045, "Critical point")}
      <circle cx={X(g.D[0])} cy={Y(g.D[1])} r="4" fill="#2563eb" />
      {(type.cbLeft ? label(g.D[0] - 0.015, g.D[1] + 0.012, "Cricondenbar", { anchor: "end" }) : label(g.D[0] - 0.02, g.D[1] + 0.05, "Cricondenbar"))}
      <circle cx={X(g.E[0])} cy={Y(g.E[1])} r="4" fill="#b45309" />
      {label(g.E[0] + 0.015, g.E[1], "Cricondentherm")}

      {label(g.C[0] - 0.2 * type.s, 0.3, "Two-phase region", { props: { fontWeight: 600 } })}
      {label(g.A[0] + 0.02 * type.s, 0.5, "Bubble-point curve", {
        props: { fill: "#1d4ed8", transform: `rotate(-62 ${X(g.A[0] + 0.05)} ${Y(0.5)})` },
      })}
      {label(g.E[0] + 0.045 * type.s, 0.2, "Dew-point curve", { props: { fill: "#92400e" } })}
      {label(Math.max(g.C[0] - 0.07 * type.s, type.tRes + 0.08), 0.1, "Quality lines (dashed)", { props: { fill: "#6b7280" } })}

      <text x={(L + R) / 2} y={H - 8} fontSize="13" fill="#111827" textAnchor="middle">
        Temperature
      </text>
      <text transform={`translate(14 ${(T + B) / 2}) rotate(-90)`} fontSize="13" fill="#111827" textAnchor="middle">
        Pressure
      </text>
    </svg>
  );
}

function Shrinkage({ selected }) {
  const w = 640;
  const h = 330;
  const l = 54;
  const r = 620;
  const t = 16;
  const b = 290;
  const x = (p) => l + p * (r - l);
  const y = (v) => b - (v / 100) * (b - t);
  const curve = (fn) => {
    const pts = [];
    for (let i = 0; i <= 120; i++) {
      const p = i / 120;
      pts.push(`${x(p).toFixed(1)},${y(fn(p)).toFixed(1)}`);
    }
    return "M" + pts.join("L");
  };
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Schematic liquid shrinkage curves">
      <rect x={l} y={t} width={r - l} height={b - t} fill="#fff" stroke="#9ca3af" />
      {TYPES.map((tp) => (
        <path
          key={tp.key}
          d={curve(SHRINKAGE[tp.key])}
          fill="none"
          stroke={SHRINK_COLOURS[tp.key]}
          strokeWidth={tp.key === selected ? 3.5 : 1.5}
          opacity={tp.key === selected ? 1 : 0.55}
        />
      ))}
      {TYPES.map((tp) => (
        <text
          key={tp.key + "l"}
          x={x(0.03)}
          y={y(SHRINKAGE[tp.key](0.03)) - 6}
          fontSize="12"
          fill={SHRINK_COLOURS[tp.key]}
          fontWeight={tp.key === selected ? 700 : 400}
        >
          {tp.name}
        </text>
      ))}
      <text x={l - 6} y={y(100) + 4} fontSize="12" textAnchor="end" fill="#374151">100%</text>
      <text x={l - 6} y={y(0) + 4} fontSize="12" textAnchor="end" fill="#374151">0%</text>
      <text x={r} y={b + 16} fontSize="12" textAnchor="end" fill="#374151">Bubble point, pb</text>
      <text x={l} y={b + 16} fontSize="12" fill="#374151">0</text>
      <text x={(l + r) / 2} y={h - 6} fontSize="13" textAnchor="middle" fill="#111827">
        Pressure
      </text>
      <text transform={`translate(14 ${(t + b) / 2}) rotate(-90)`} fontSize="13" textAnchor="middle" fill="#111827">
        Liquid volume
      </text>
    </svg>
  );
}

function PhaseDiagram() {
  const [params, setParams] = useSearchParams();
  const requested = params.get("type");
  const type = TYPES.find((t) => t.key === requested) || TYPES[0];
  const [criteria, setCriteria] = useState(null);

  useEffect(() => {
    fetch(`${API}/classify/criteria`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setCriteria)
      .catch(() => setCriteria(null));
  }, []);

  const info = criteria ? criteria.find((c) => c.key === type.key) : null;

  return (
    <div>
      <h1>Phase Diagrams</h1>
      <p className="subtitle">
        Schematic pressure-temperature diagrams and liquid-shrinkage curves for the four oil types in Chapter 1.
      </p>

      <div className="segmented">
        {TYPES.map((t) => (
          <button
            key={t.key}
            className={t.key === type.key ? "seg active" : "seg"}
            onClick={() => setParams({ type: t.key })}
          >
            {t.name}
          </button>
        ))}
      </div>

      <section className="card">
        <h2>{type.name}, pressure-temperature diagram</h2>
        <Envelope type={type} />
        <p className="note">
          {type.spacing} The reservoir sits to the left of the critical point, so the oil is above its bubble point at the
          start. As pressure falls along the vertical line, gas first appears at the bubble point.
        </p>
      </section>

      <section className="card">
        <h2>Liquid shrinkage below the bubble point</h2>
        <Shrinkage selected={type.key} />
        <p className="note">
          Liquid volume as a share of the hydrocarbon volume, from the bubble point down to low pressure. Low-shrinkage oil
          loses the least liquid. Volatile oil loses much more, and loses most of it just below the bubble point. Near-critical
          oil can fall to 55% or less within 10 to 50 psi of the bubble point.
        </p>
      </section>

      {info && (
        <section className="card">
          <h2>Typical properties in the book</h2>
          <table>
            <thead>
              <tr>
                <th>Property</th>
                <th>Limit</th>
              </tr>
            </thead>
            <tbody>
              {info.criteria.map((k) => (
                <tr key={k.param}>
                  <td>
                    {k.label} ({k.unit})
                  </td>
                  <td>{k.rule}</td>
                </tr>
              ))}
              {info.colour && (
                <tr>
                  <td>Colour</td>
                  <td>{info.colour}</td>
                </tr>
              )}
            </tbody>
          </table>
          <p className="note">Ahmed, {info.page}.</p>
        </section>
      )}

      <p className="note">
        These diagrams are schematic. They illustrate the descriptions on pages 3 to 8 of the book and are not computed from
        a fluid composition, so the axes carry no numbers and the shapes should not be read for values.
      </p>
    </div>
  );
}

export default PhaseDiagram;
