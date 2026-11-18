import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

const FIELDS = [
  ["api", "Oil gravity (°API)"],
  ["t_f", "Reservoir temperature (°F)"],
  ["rs", "Solution gas-oil ratio at pb, Rs (scf/STB)"],
  ["p", "Pressure, p (psia)"],
  ["pb", "Bubble-point pressure, pb (psia)"],
  ["mu_od_measured", "Measured dead-oil viscosity (cp), optional"],
  ["mu_ob_measured", "Measured bubble-point viscosity (cp), optional"],
  ["mu_o_measured", "Measured undersaturated viscosity (cp), optional"],
];

const EXAMPLE = { api: "40.5", t_f: "237", rs: "968", p: "5000", pb: "2884", mu_od_measured: "1.014", mu_ob_measured: "0.377", mu_o_measured: "0.414" };

const f3 = (v) => (v === null || v === undefined ? "n/a" : v.toFixed(3));

function Table({ rows, measuredLabel, showFrom }) {
  if (!rows.length) return <p className="note">Not enough inputs for this step.</p>;
  const hasErr = rows.some((r) => r.error_pct !== undefined);
  return (
    <table>
      <thead>
        <tr>
          <th>Method</th>
          {showFrom && <th>Starting from</th>}
          <th>Viscosity (cp)</th>
          {hasErr && <th>Error vs {measuredLabel}</th>}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td>{r.name}</td>
            {showFrom && <td>{r.from}</td>}
            <td>{f3(r.value)}</td>
            {hasErr && <td>{r.error_pct === undefined ? "" : `${r.error_pct >= 0 ? "+" : ""}${r.error_pct.toFixed(1)}%`}</td>}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function VerifyTable({ title, rows, measured }) {
  return (
    <>
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>
            <th>Method</th>
            {[1, 2, 3, 4, 5, 6].map((n) => (
              <th key={n}>Oil {n}</th>
            ))}
            <th>AAE here</th>
            <th>AAE published</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Measured</td>
            {measured.map((v, i) => (
              <td key={i}>{v}</td>
            ))}
            <td></td>
            <td></td>
          </tr>
          {rows.map((r) => (
            <tr key={r.name}>
              <td>{r.name}</td>
              {r.calc.map((v, i) => (
                <td key={i}>{v.toFixed(3)}</td>
              ))}
              <td>{r.aae.toFixed(1)}%</td>
              <td>{r.book_aae}%</td>
            </tr>
          ))}
          {rows.map((r) => (
            <tr key={r.name + "b"} className="muted">
              <td>{r.name}, as printed</td>
              {r.book.map((v, i) => (
                <td key={i}>{v}</td>
              ))}
              <td></td>
              <td></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function Viscosity({ embedded = false }) {
  const [v, setV] = useState(Object.fromEntries(FIELDS.map(([k]) => [k, ""])));
  const [res, setRes] = useState(null);
  const [ver, setVer] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/viscosity/verification`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`API returned ${r.status}`))))
      .then(setVer)
      .catch((e) => setError(e.message));
  }, []);

  async function run(values = v) {
    setError(null);
    const body = {};
    for (const [k] of FIELDS) if (values[k] !== "") body[k] = Number(values[k]);
    try {
      const r = await fetch(`${API}/viscosity/compute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || `API returned ${r.status}`);
      }
      setRes(await r.json());
    } catch (e) {
      setError(e.message);
    }
  }

  const anyInput = FIELDS.some(([k]) => v[k] !== "");

  return (
    <div>
      {!embedded && <h1>Oil Viscosity</h1>}
      <p className="subtitle">
        Dead-oil, saturated-oil and undersaturated-oil viscosity from published correlations. Fill in what you have and each step
        runs when its inputs are there. Each later step starts from every result of the step before it, plus your measured value if you give one.
      </p>

      <section className="card">
        <h2>Inputs</h2>
        {FIELDS.map(([k, label]) => (
          <label className="field" key={k}>
            <span>{label}</span>
            <input
              type="number"
              value={v[k]}
              onChange={(e) => {
                setV({ ...v, [k]: e.target.value });
                setRes(null);
              }}
            />
          </label>
        ))}
        <p>
          <button className="primary" disabled={!anyInput} onClick={() => run()}>
            Calculate
          </button>{" "}
          <button
            className="seg"
            onClick={() => {
              setV(EXAMPLE);
              run(EXAMPLE);
            }}
          >
            Use oil 4 from Example 2-36
          </button>
        </p>
        {error && <p className="error">Something went wrong: {error}</p>}
      </section>

      {res && (
        <>
          <section className="card">
            <h2>Dead-oil viscosity</h2>
            <Table rows={res.dead} measuredLabel="measured" />
          </section>
          <section className="card">
            <h2>Saturated-oil viscosity at the bubble point</h2>
            <Table rows={res.saturated} measuredLabel="measured" showFrom />
          </section>
          <section className="card">
            <h2>Undersaturated-oil viscosity</h2>
            <Table rows={res.undersaturated} measuredLabel="measured" showFrom />
          </section>
        </>
      )}

      {ver && (
        <details className="card checks">
          <summary>Check against a published example</summary>
          <p>Six oils from a published example. The calculated values are compared with the published results and average absolute errors (AAE).</p>
          <VerifyTable title="Dead oil" rows={ver.dead} measured={ver.measured.dead} />
          <VerifyTable title="Saturated oil (starting from the measured dead-oil viscosity)" rows={ver.saturated} measured={ver.measured.saturated} />
          <VerifyTable title="Undersaturated oil (starting from the measured bubble-point viscosity)" rows={ver.undersaturated} measured={ver.measured.undersaturated} />
          <h3>Where the published example needed a decision</h3>
          {ver.notes.map((n) => (
            <p className="note" key={n}>
              {n}
            </p>
          ))}
        </details>
      )}
    </div>
  );
}

export default Viscosity;
