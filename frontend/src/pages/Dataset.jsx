import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Label,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = "http://127.0.0.1:8000";

const PROP_UNITS = { rs: "scf/STB", pb: "psia", bo: "bbl/STB" };
const PROP_SYMBOLS = { rs: "Rs", pb: "Pb", bo: "Bo" };
const PROP_NAMES = {
  rs: "Solution gas-oil ratio (Rs)",
  pb: "Bubble-point pressure (Pb)",
  bo: "Oil formation volume factor (Bo)",
};
// The column that holds the measured value for each property
const MEASURED_COLUMN = { rs: "rs_measured", pb: "p_psia", bo: "bo" };

function Dataset({ embedded = false, fixedProp = null }) {
  const [methods, setMethods] = useState(null);
  const [builtin, setBuiltin] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const [source, setSource] = useState(fixedProp && fixedProp !== "bo" ? "upload" : "builtin");
  const [prop, setProp] = useState(fixedProp || "bo");
  const [selected, setSelected] = useState([]);
  const [regions, setRegions] = useState([]);
  const [excludeDuplicates, setExcludeDuplicates] = useState(true);
  const [excludeSuspect, setExcludeSuspect] = useState(false);
  const [csvText, setCsvText] = useState("");
  const [fileName, setFileName] = useState("");

  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/methods`).then((r) => {
        if (!r.ok) throw new Error(`API returned ${r.status}`);
        return r.json();
      }),
      fetch(`${API}/dataset/builtin`).then((r) => {
        if (!r.ok) throw new Error(`API returned ${r.status}`);
        return r.json();
      }),
    ])
      .then(([m, b]) => {
        setMethods(m);
        setBuiltin(b);
        setSelected(m[fixedProp || "bo"].map((x) => x.key));
        setRegions(b.regions.map((x) => x.name));
      })
      .catch((err) => setLoadError(err.message));
  }, []);

  if (loadError) return <p>Could not reach the API: {loadError}</p>;
  if (!methods || !builtin) return <p>Loading...</p>;

  const available = methods[prop];
  const digits = prop === "bo" ? 3 : 1;
  const symbol = PROP_SYMBOLS[prop];
  const unit = PROP_UNITS[prop];

  const requiredColumns = [
    ...new Set([
      MEASURED_COLUMN[prop],
      ...available
        .filter((m) => selected.includes(m.key))
        .flatMap((m) => m.inputs),
    ]),
  ];

  const canRun =
    !running &&
    selected.length > 0 &&
    (source === "builtin" ? regions.length > 0 : csvText !== "");

  function changeSource(next) {
    setSource(next);
    setResult(null);
    setRunError(null);
    if (next === "builtin") {
      setProp("bo");
      setSelected(methods.bo.map((m) => m.key));
    }
  }

  function changeProp(next) {
    setProp(next);
    setSelected(methods[next].map((m) => m.key));
    setResult(null);
  }

  function toggleMethod(key) {
    setSelected(
      selected.includes(key) ? selected.filter((k) => k !== key) : [...selected, key]
    );
    setResult(null);
  }

  function toggleRegion(name) {
    setRegions(
      regions.includes(name) ? regions.filter((r) => r !== name) : [...regions, name]
    );
    setResult(null);
  }

  async function onFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setCsvText(await file.text());
    setResult(null);
  }

  async function run() {
    setRunning(true);
    setRunError(null);
    try {
      const body = { prop, methods: selected, source };
      if (source === "builtin") {
        body.regions = regions;
        body.exclude_duplicates = excludeDuplicates;
        body.max_gas_gravity = excludeSuspect ? builtin.suspect_gas_limit : null;
      } else {
        body.csv_text = csvText;
      }
      const res = await fetch(`${API}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `API returned ${res.status}`);
      setResult(data);
    } catch (err) {
      setResult(null);
      setRunError(err.message);
    } finally {
      setRunning(false);
    }
  }

  function downloadPredictions() {
    const keys = result.summary.map((s) => s.key);
    const header = ["oil", "region", `measured_${prop}`, ...keys.map((k) => `${k}_${prop}`)];
    const lines = result.rows.map((r) =>
      [r.oil, r.region ?? "", r.measured, ...keys.map((k) => r[k] ?? "")]
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(",")
    );
    const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `predictions_${prop}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const fmt = (v, d = digits) => (v === null || v === undefined ? "n/a" : v.toFixed(d));
  const signed = (v, d = digits) =>
    v === null || v === undefined ? "n/a" : `${v >= 0 ? "+" : ""}${v.toFixed(d)}`;

  const ranked = result
    ? [...result.summary].sort((a, b) => (a.aae ?? Infinity) - (b.aae ?? Infinity))
    : [];
  const chartData = ranked
    .filter((s) => s.aae !== null)
    .map((s) => ({ method: s.key, aae: Number(s.aae.toFixed(2)) }));
  const regionNames = result ? Object.keys(result.by_region) : [];
  const resultKeys = result ? result.summary.map((s) => s.key) : [];

  return (
    <div>
      {!embedded && <h1>Dataset Analysis</h1>}
      <p className="subtitle">
        Score the correlations against many measured records and see which ones fit best.
      </p>

      {(!fixedProp || fixedProp === "bo") && (
      <div className="segmented">
        {(!fixedProp || fixedProp === "bo") && (
          <button
            className={source === "builtin" ? "seg active" : "seg"}
            onClick={() => changeSource("builtin")}
          >
            Built-in dataset
          </button>
        )}
        <button
          className={source === "upload" ? "seg active" : "seg"}
          onClick={() => changeSource("upload")}
        >
          Upload a CSV
        </button>
      </div>
      )}

      {source === "upload" && !fixedProp && (
        <div className="segmented">
          {Object.keys(PROP_NAMES).map((p) => (
            <button
              key={p}
              className={prop === p ? "seg active" : "seg"}
              onClick={() => changeProp(p)}
            >
              {PROP_NAMES[p]}
            </button>
          ))}
        </div>
      )}

      <div className="panels">
        <section className="card">
          {source === "builtin" ? (
            <>
              <h2>Built-in data</h2>
              <p className="note">
                {builtin.n_rows} oil samples from {builtin.regions.length} regions. This data has
                no pressure, bubble-point or separator values, so only Bo can be scored.
              </p>
              {builtin.regions.map((r) => (
                <label className="check" key={r.name}>
                  <input
                    type="checkbox"
                    checked={regions.includes(r.name)}
                    onChange={() => toggleRegion(r.name)}
                  />{" "}
                  {r.name} ({r.n})
                </label>
              ))}
              <hr />
              <label className="check">
                <input
                  type="checkbox"
                  checked={excludeDuplicates}
                  onChange={(e) => {
                    setExcludeDuplicates(e.target.checked);
                    setResult(null);
                  }}
                />{" "}
                Leave out {builtin.n_duplicates} repeated rows from {builtin.duplicate_sheet}
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={excludeSuspect}
                  onChange={(e) => {
                    setExcludeSuspect(e.target.checked);
                    setResult(null);
                  }}
                />{" "}
                Leave out {builtin.n_suspect_gas} rows with gas gravity above{" "}
                {builtin.suspect_gas_limit} (all from Pakistan)
              </label>
            </>
          ) : (
            <>
              <h2>Your data</h2>
              <label className="field">
                <span>CSV file</span>
                <input type="file" accept=".csv,text/csv" onChange={onFile} />
              </label>
              {fileName && <p className="note">Loaded {fileName}</p>}
              <p className="note">
                Needed columns for the selected methods: {requiredColumns.join(", ")}.
                Optional columns: oil, region, psep_psia, tsep_f. Pressures are in psia,
                temperatures in °F, Rs in scf/STB.
              </p>
            </>
          )}
        </section>

        <section className="card">
          <h2>Select Methods</h2>
          {available.map((m) => (
            <label className="check" key={m.key}>
              <input
                type="checkbox"
                checked={selected.includes(m.key)}
                onChange={() => toggleMethod(m.key)}
              />{" "}
              {m.name}
            </label>
          ))}
        </section>
      </div>

      <p>
        <button className="primary" onClick={run} disabled={!canRun}>
          {running ? "Running..." : "Run Analysis"}
        </button>
      </p>
      {selected.length === 0 && <p className="hint">Select at least one method.</p>}
      {source === "builtin" && regions.length === 0 && (
        <p className="hint">Select at least one region.</p>
      )}
      {source === "upload" && csvText === "" && (
        <p className="hint">Choose a CSV file to analyse.</p>
      )}
      {runError && <p className="error">Something went wrong: {runError}</p>}

      {result && (
        <section className="card">
          <h2>Results for {symbol}</h2>
          <p className="note">
            {result.rows_used} records scored out of {result.rows_loaded} loaded. Methods are
            listed with the lowest average absolute error first.
          </p>
          <table>
            <thead>
              <tr>
                <th>Method</th>
                <th>N</th>
                <th>AAE (%)</th>
                <th>MAE ({unit})</th>
                <th>RMSE ({unit})</th>
                <th>Bias ({unit})</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((s) => (
                <tr key={s.key}>
                  <td>{s.name}</td>
                  <td>{s.n}</td>
                  <td>{fmt(s.aae, 2)}</td>
                  <td>{fmt(s.mae)}</td>
                  <td>{fmt(s.rmse)}</td>
                  <td>{signed(s.bias)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="chart">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ top: 20, right: 10, left: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="method" tick={{ fontSize: 12 }} interval={0} />
                <YAxis tick={{ fontSize: 12 }} width={70}>
                  <Label
                    value="AAE (%)"
                    angle={-90}
                    position="insideLeft"
                    style={{ textAnchor: "middle", fontSize: 12 }}
                  />
                </YAxis>
                <Tooltip />
                <Bar dataKey="aae" fill="var(--c1)">
                  <LabelList dataKey="aae" position="top" fontSize={12} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {regionNames.length > 1 && (
            <>
              <h2>AAE (%) by region</h2>
              <table>
                <thead>
                  <tr>
                    <th>Region</th>
                    <th>N</th>
                    {resultKeys.map((k) => (
                      <th key={k}>{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {regionNames.map((name) => {
                    const row = result.by_region[name];
                    const values = resultKeys.map((k) => row[k]?.aae ?? null);
                    const best = Math.min(...values.filter((v) => v !== null));
                    return (
                      <tr key={name}>
                        <td>{name}</td>
                        <td>{row[resultKeys[0]]?.n}</td>
                        {values.map((v, i) => (
                          <td key={resultKeys[i]} style={v === best ? { fontWeight: 700 } : undefined}>
                            {fmt(v, 2)}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="note">The lowest error in each region is in bold.</p>
            </>
          )}

          {result.notes.map((n, i) => (
            <p className="hint" key={i}>
              {n}
            </p>
          ))}

          <p>
            <button className="primary" onClick={downloadPredictions}>
              Download predictions (CSV)
            </button>
          </p>

          <p className="note">
            AAE is the mean absolute percent error. MAE and RMSE are in {unit}. Bias is the mean
            of calculated minus measured, so a positive bias means the method overpredicts. A low
            error on this data does not guarantee the same accuracy on your own crude oil.
          </p>
        </section>
      )}

      {source === "builtin" && (
        <p className="note">
          Data: Ramirez-Dolores, C. (2025), PVT Oil Property Data for Oilfields in Africa, Alaska,
          Malaysia, Middle East, North Sea, Pakistan and United Arab Emirates, Mendeley Data,
          DOI 10.17632/6mttycsgbw.1, CC BY 4.0. Labedi, R. M. (1982), PVT Correlations of the
          African Crudes, PhD thesis, Colorado School of Mines. Correlations and verification
          examples: Ahmed, T., Reservoir Engineering Handbook, 5th ed.
        </p>
      )}
    </div>
  );
}

export default Dataset;