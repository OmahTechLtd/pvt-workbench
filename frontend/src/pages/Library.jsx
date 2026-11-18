import { useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8000";

const PROPS = [
  ["rs", "Solution gas-oil ratio, Rs", "How much gas is dissolved in the oil at a given pressure."],
  ["pb", "Bubble point pressure, Pb", "The pressure at which the first gas comes out of the oil."],
  ["bo", "Oil formation volume factor, Bo", "How much a barrel of stock tank oil swells at reservoir conditions."],
];

const INPUT_NAMES = {
  p_psia: "Pressure",
  t_f: "Temperature",
  api: "Oil gravity",
  gamma_g: "Gas gravity",
  rs_measured: "Measured Rs",
  psep_psia: "Separator pressure",
  tsep_f: "Separator temperature",
};

const hasRange = (r) => r && !/^none/i.test(r);

export default function Library() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [q, setQ] = useState("");
  const [prop, setProp] = useState("all");

  useEffect(() => {
    fetch(`${API}/methods`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setError("The method list could not be loaded. Check that the API is running."));
  }, []);

  const total = data ? Object.values(data).reduce((a, l) => a + l.length, 0) : 0;
  const needle = q.trim().toLowerCase();

  const shown = useMemo(() => {
    if (!data) return [];
    return PROPS.filter(([k]) => prop === "all" || prop === k).map(([k, title, blurb]) => ({
      k,
      title,
      blurb,
      methods: (data[k] || []).filter((m) => !needle || `${m.name} ${m.source}`.toLowerCase().includes(needle)),
    }));
  }, [data, needle, prop]);

  return (
    <div>
      <h1>Method Library</h1>
      <p className="subtitle">
        {total ? `${total} published correlations` : "The published correlations"} behind the property calculators. Each one is coded from its source and
        reproduces the worked example printed there. Run them side by side on the Rs, Pb and Bo pages, and use the Test on data tab there to see which fits your own data.
      </p>

      <p className="subtitle" style={{ marginTop: -8 }}>
        Most of these correlations were fitted to crudes from the US, the North Sea and the Middle East. Check them against your own lab data before relying on any one of them.
      </p>

      <div className="segmented">
        <button className={"seg" + (prop === "all" ? " active" : "")} onClick={() => setProp("all")}>All properties</button>
        {PROPS.map(([k, title]) => (
          <button key={k} className={"seg" + (prop === k ? " active" : "")} onClick={() => setProp(k)}>{title.split(",")[1].trim()}</button>
        ))}
      </div>
      <label className="field" style={{ maxWidth: 360 }}>
        <span>Search by author or equation</span>
        <input type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="for example Standing or 2-72" />
      </label>

      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading…</p>}

      {shown.map((g) => (
        <section className="card" key={g.k}>
          <h2>{g.title}</h2>
          <p className="muted" style={{ marginTop: -6 }}>{g.blurb}</p>
          {g.methods.length === 0 ? (
            <p className="muted">No method matches “{q}”.</p>
          ) : (
            <div className="tablewrap">
              <table className="libtable">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Needs</th>
                    <th>Source</th>
                    <th>Check</th>
                  </tr>
                </thead>
                <tbody>
                  {g.methods.map((m) => (
                    <tr key={m.key}>
                      <td><strong>{m.name}</strong></td>
                      <td>
                        {m.inputs.map((i) => INPUT_NAMES[i] || i).join(", ")}
                        {m.optional_inputs.length > 0 && <div className="note">Optional: {m.optional_inputs.map((i) => INPUT_NAMES[i] || i).join(", ")}</div>}
                        {hasRange(m.valid_range) && <div className="note">Range: {m.valid_range}</div>}
                      </td>
                      <td>{m.source}</td>
                      <td>{/^verified/i.test(m.status) ? <span className="badge ok">Matches published example</span> : <span className="badge off">Not checked</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ))}

      <p className="note">
        Viscosity, surface tension, lab checks and material balance carry their own source line and checks table on the page itself.
      </p>
    </div>
  );
}
