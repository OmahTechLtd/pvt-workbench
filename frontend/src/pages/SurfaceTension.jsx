import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

const EXAMPLE = {
  rho_o: "46.23",
  rho_g: "18.21",
  m_plus: "215",
  rows: [
    ["C1", "0.45", "0.77"],
    ["C2", "0.05", "0.08"],
    ["C3", "0.05", "0.06"],
    ["nC4", "0.03", "0.04"],
    ["nC5", "0.01", "0.02"],
    ["nC6", "0.01", "0.02"],
    ["C7+", "0.40", "0.01"],
  ],
};

function SurfaceTension({ embedded = false }) {
  const [components, setComponents] = useState([]);
  const [rows, setRows] = useState([["C1", "", ""]]);
  const [rhoO, setRhoO] = useState("");
  const [rhoG, setRhoG] = useState("");
  const [mPlus, setMPlus] = useState("");
  const [res, setRes] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API}/tension/components`)
      .then((r) => r.json())
      .then((d) => setComponents(d.components))
      .catch((e) => setError(e.message));
  }, []);

  const setCell = (i, j, val) => {
    setRows(rows.map((r, k) => (k === i ? r.map((c, m) => (m === j ? val : c)) : r)));
    setRes(null);
  };

  async function run(data = { rows, rhoO, rhoG, mPlus }) {
    setError(null);
    try {
      const r = await fetch(`${API}/tension/compute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          components: data.rows.map((x) => x[0]),
          x: data.rows.map((x) => Number(x[1] || 0)),
          y: data.rows.map((x) => Number(x[2] || 0)),
          rho_o: Number(data.rhoO),
          rho_g: Number(data.rhoG),
          m_plus: data.mPlus === "" ? null : Number(data.mPlus),
        }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(typeof d.detail === "string" ? d.detail : `API returned ${r.status}`);
      }
      setRes(await r.json());
    } catch (e) {
      setError(e.message);
      setRes(null);
    }
  }

  const hasPlus = rows.some((r) => r[0] === "C7+");
  const ready = rhoO !== "" && rhoG !== "" && rows.length > 0 && (!hasPlus || mPlus !== "");

  return (
    <div>
      {!embedded && <h1>Surface Tension</h1>}
      <p className="subtitle">
        Surface tension of a crude oil in equilibrium with its gas, from the oil and gas compositions and densities (Sugden correlation in the form
        of Katz et al., Ahmed, Eq. 2-124).
      </p>

      <section className="card">
        <h2>Compositions</h2>
        <table>
          <thead>
            <tr>
              <th>Component</th>
              <th>Oil, xi</th>
              <th>Gas, yi</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>
                  <select value={r[0]} onChange={(e) => setCell(i, 0, e.target.value)}>
                    {components.map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </td>
                <td>
                  <input type="number" step="any" value={r[1]} onChange={(e) => setCell(i, 1, e.target.value)} />
                </td>
                <td>
                  <input type="number" step="any" value={r[2]} onChange={(e) => setCell(i, 2, e.target.value)} />
                </td>
                <td>
                  <button className="seg" onClick={() => { setRows(rows.filter((_, k) => k !== i)); setRes(null); }}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            <tr>
              <td colSpan="4">
                <button className="seg" onClick={() => setRows([...rows, ["C1", "", ""]])}>
                  Add a component
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <label className="field">
          <span>Oil phase density (lb/ft³)</span>
          <input type="number" value={rhoO} onChange={(e) => { setRhoO(e.target.value); setRes(null); }} />
        </label>
        <label className="field">
          <span>Gas phase density (lb/ft³)</span>
          <input type="number" value={rhoG} onChange={(e) => { setRhoG(e.target.value); setRes(null); }} />
        </label>
        {hasPlus && (
          <label className="field">
            <span>Molecular weight of C7+</span>
            <input type="number" value={mPlus} onChange={(e) => { setMPlus(e.target.value); setRes(null); }} />
          </label>
        )}
        <p>
          <button className="primary" disabled={!ready} onClick={() => run()}>
            Calculate
          </button>{" "}
          <button
            className="seg"
            onClick={() => {
              setRows(EXAMPLE.rows);
              setRhoO(EXAMPLE.rho_o);
              setRhoG(EXAMPLE.rho_g);
              setMPlus(EXAMPLE.m_plus);
              run({ rows: EXAMPLE.rows, rhoO: EXAMPLE.rho_o, rhoG: EXAMPLE.rho_g, mPlus: EXAMPLE.m_plus });
            }}
          >
            Use Example 2-37
          </button>
        </p>
        {error && <p className="error">Something went wrong: {error}</p>}
      </section>

      {res && (
        <section className="card">
          <h2>Result</h2>
          <p>
            Surface tension, σ = <strong>{res.sigma.toFixed(3)} dynes/cm</strong>
          </p>
          <table>
            <thead>
              <tr>
                <th>Component</th>
                <th>Pch(A xi − B yi)</th>
              </tr>
            </thead>
            <tbody>
              {res.components.map((c, i) => (
                <tr key={i}>
                  <td>{c}</td>
                  <td>{res.terms[i].toFixed(4)}</td>
                </tr>
              ))}
              <tr>
                <td>Sum</td>
                <td>{res.sum.toFixed(4)}</td>
              </tr>
            </tbody>
          </table>
          <p className="note">
            Apparent molecular weights: oil {res.mo.toFixed(2)}, gas {res.mg.toFixed(2)}. A = {res.A.toFixed(5)}, B = {res.B.toFixed(5)}. Sum of oil
            fractions {res.sum_x.toFixed(3)}, sum of gas fractions {res.sum_y.toFixed(3)}. σ is the sum raised to the fourth power. The parachor of
            C7+ is 69.9 + 2.3 M. Other parachors come from Table 2-1.
          </p>
          {(Math.abs(res.sum_x - 1) > 0.005 || Math.abs(res.sum_y - 1) > 0.005) && (
            <p className="error">The mole fractions do not add up to 1, so the answer will be off.</p>
          )}
          <p className="note">
            Example 2-37 gives 0.753 dynes/cm. This tool returns 0.752. The published apparent gas molecular weight is 24.99, but the printed gas
            composition gives 25.05, which accounts for the small difference.
          </p>
        </section>
      )}
    </div>
  );
}

export default SurfaceTension;
