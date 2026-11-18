import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

const PRESETS = [
  { label: "Example 1-1 (M 150, gravity 0.78)", m: "150", gamma: "0.78" },
  { label: "Problem 3 (M 190, gravity 0.8762)", m: "190", gamma: "0.8762" },
];

const DIGITS = { tb: 1, tc: 1, pc: 1, vc: 5 };

function PlusFraction() {
  const [m, setM] = useState("");
  const [gamma, setGamma] = useState("");
  const [result, setResult] = useState(null);
  const [verification, setVerification] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch(`${API}/fraction/verification`)
      .then((r) => {
        if (!r.ok) throw new Error(`API returned ${r.status}`);
        return r.json();
      })
      .then(setVerification)
      .catch((e) => setError(e.message));
  }, []);

  const canRun = m !== "" && gamma !== "" && Number(m) > 0 && Number(gamma) > 0 && !running;

  async function run(mValue = m, gValue = gamma) {
    setRunning(true);
    setError(null);
    try {
      const res = await fetch(`${API}/fraction/characterize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ m: Number(mValue), gamma: Number(gValue) }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `API returned ${res.status}`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  function usePreset(p) {
    setM(p.m);
    setGamma(p.gamma);
    run(p.m, p.gamma);
  }

  return (
    <div>
      <h1>Plus Fraction Characterization</h1>
      <p className="subtitle">
        Estimate the critical properties and acentric factor of a heptanes-plus fraction from its molecular weight and
        specific gravity (Ahmed, Chapter 1).
      </p>

      <section className="card">
        <h2>Fraction properties</h2>
        <label className="field">
          <span>Molecular weight, M</span>
          <input
            type="number"
            value={m}
            onChange={(e) => {
              setM(e.target.value);
              setResult(null);
            }}
          />
        </label>
        <label className="field">
          <span>Specific gravity (water = 1)</span>
          <input
            type="number"
            value={gamma}
            onChange={(e) => {
              setGamma(e.target.value);
              setResult(null);
            }}
          />
        </label>
        <p>
          <button className="primary" onClick={() => run()} disabled={!canRun}>
            {running ? "Working..." : "Characterize"}
          </button>{" "}
          {PRESETS.map((p) => (
            <button key={p.label} className="seg" onClick={() => usePreset(p)}>
              {p.label}
            </button>
          ))}
        </p>
        {error && <p className="error">Something went wrong: {error}</p>}
      </section>

      {result && (
        <section className="card">
          <h2>Results</h2>
          <table>
            <thead>
              <tr>
                <th>Property</th>
                <th>Value</th>
                <th>Unit</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.properties).map(([key, p]) => (
                <tr key={key}>
                  <td>{p.label}</td>
                  <td>{p.value.toFixed(DIGITS[key])}</td>
                  <td>{p.unit}</td>
                </tr>
              ))}
              <tr>
                <td>Acentric factor, ω (Edmister)</td>
                <td>{result.omega.toFixed(4)}</td>
                <td></td>
              </tr>
            </tbody>
          </table>
          <h2 style={{ marginTop: 24 }}>Critical compressibility factor, Zc</h2>
          <table>
            <thead>
              <tr>
                <th>Method</th>
                <th>Zc</th>
              </tr>
            </thead>
            <tbody>
              {result.zc.map((z) => (
                <tr key={z.key}>
                  <td>{z.name}</td>
                  <td>{z.value.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="note">
            Tb, Tc, pc and Vc come from the Riazi and Daubert equation (Eq. 1-2, Table 1-4). The acentric factor comes
            from Edmister's equation (Eq. 1-3). The book prints the Nath equation without an acentric factor term. It
            is calculated here as 0.2918 − 0.0928ω, in the same form as the other methods.
          </p>
        </section>
      )}

      {verification && (
        <section className="card">
          <h2>Check against Example 1-1</h2>
          <p>{verification.summary}</p>
          <table>
            <thead>
              <tr>
                <th>Quantity</th>
                <th>Book</th>
                <th>This tool</th>
                <th>Difference</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {verification.rows.map((r) => (
                <tr key={r.label}>
                  <td>{r.label}</td>
                  <td>{r.book}</td>
                  <td>{r.calculated.toFixed((String(r.book).split(".")[1] || "").length + 1)}</td>
                  <td>
                    {r.diff_pct >= 0 ? "+" : ""}
                    {r.diff_pct.toFixed(3)}%
                  </td>
                  <td>{r.match ? "Matches" : "Does not match"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {verification.rows
            .filter((r) => r.note)
            .map((r) => (
              <p className="note" key={r.label + "n"}>
                <strong>{r.label}.</strong> {r.note}
              </p>
            ))}
          <p className="note">
            A row matches when it is within one unit of the last digit the book prints.
          </p>
        </section>
      )}
    </div>
  );
}

export default PlusFraction;
