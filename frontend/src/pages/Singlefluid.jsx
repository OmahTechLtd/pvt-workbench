import { useEffect, useState } from "react";
import Recommend from "../components/Recommend.jsx";
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
  ReferenceLine,
} from "recharts";

const API = "http://127.0.0.1:8000";

const INPUT_INFO = {
  p_psia: { label: "Pressure", unit: "psia" },
  t_f: { label: "Temperature", unit: "°F" },
  api: { label: "Oil API gravity", unit: "°API" },
  gamma_g: { label: "Gas specific gravity", unit: "air = 1" },
  rs_measured: { label: "Solution gas-oil ratio, Rs", unit: "scf/STB" },
  psep_psia: { label: "Separator pressure", unit: "psia" },
  tsep_f: { label: "Separator temperature", unit: "°F" },
};

const PROP_UNITS = { rs: "scf/STB", pb: "psia", bo: "bbl/STB" };
const PROP_SYMBOLS = { rs: "Rs", pb: "Pb", bo: "Bo" };
const PROP_NAMES = {
  rs: "Solution gas-oil ratio (Rs)",
  pb: "Bubble-point pressure (Pb)",
  bo: "Oil formation volume factor (Bo)",
};

function SingleFluid({ embedded = false, fixedProp = null }) {
  const [methods, setMethods] = useState(null);
  const [error, setError] = useState(null);
  const [prop, setProp] = useState(fixedProp || "rs");
  const [selected, setSelected] = useState([]);
  const [values, setValues] = useState({});
  const [measured, setMeasured] = useState({});
  const [results, setResults] = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);

  useEffect(() => {
    fetch(`${API}/methods`)
      .then((res) => {
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setMethods(data);
        setSelected(data[fixedProp || "rs"].map((m) => m.key));
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p>Could not reach the API: {error}</p>;
  if (!methods) return <p>Loading methods...</p>;

  const available = methods[prop];

  // Inputs every selected method must have
  const needed = [
    ...new Set(
      available.filter((m) => selected.includes(m.key)).flatMap((m) => m.inputs)
    ),
  ];

  // Extra inputs some selected methods can use (for example separator data)
  const optional = [
    ...new Set(
      available
        .filter((m) => selected.includes(m.key))
        .flatMap((m) => m.optional_inputs ?? [])
    ),
  ].filter((name) => !needed.includes(name));

  const missingFields = needed.filter(
    (name) => values[name] === undefined || values[name] === ""
  );
  const optionalFilled = optional.filter(
    (name) => values[name] !== undefined && values[name] !== ""
  );
  const optionalIncomplete =
    optionalFilled.length > 0 && optionalFilled.length < optional.length;

  const canRun = selected.length > 0 && missingFields.length === 0 && !running;
  const measuredRaw = measured[prop];
  const measuredNum =
    measuredRaw === undefined || measuredRaw === "" ? null : Number(measuredRaw);
  const hasMeasured = measuredNum !== null && measuredNum > 0;
  const digits = prop === "bo" ? 3 : 1;
  const okValues = results
    ? results.filter((r) => r.error === null).map((r) => r.value)
    : [];
  const mean = okValues.reduce((a, b) => a + b, 0) / (okValues.length || 1);

  const chartData = results
    ? results
        .filter((r) => r.error === null)
        .map((r) => ({ method: r.key, value: Number(r.value.toFixed(digits)) }))
    : [];

  function nameOf(key) {
    return available.find((m) => m.key === key)?.name ?? key;
  }

  function changeProp(newProp) {
    setProp(newProp);
    setSelected(methods[newProp].map((m) => m.key));
    setResults(null);
  }

  function toggleMethod(key) {
    setSelected(
      selected.includes(key)
        ? selected.filter((k) => k !== key)
        : [...selected, key]
    );
    setResults(null);
  }

  async function runAnalysis() {
    setRunning(true);
    setRunError(null);
    try {
      const inputs = {};
      for (const name of needed) inputs[name] = Number(values[name]);
      // Send optional inputs only when the person filled them in
      for (const name of optionalFilled) inputs[name] = Number(values[name]);
      const res = await fetch(`${API}/calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prop, methods: selected, inputs }),
      });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      setResults(data.results);
    } catch (err) {
      setRunError(err.message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      {!embedded && <h1>Single Fluid Analysis</h1>}
      <p className="subtitle">
        Enter fluid properties, select methods and compare predictions.
      </p>

      {!fixedProp && (
      <div className="segmented">
        {Object.keys(methods).map((p) => (
          <button
            key={p}
            className={prop === p ? "seg active" : "seg"}
            onClick={() => changeProp(p)}
          >
            {PROP_NAMES[p] ?? p.toUpperCase()}
          </button>
        ))}
      </div>
      )}

      <div className="panels">
        <section className="card">
          <h2>Fluid Properties</h2>

          {needed.map((name) => {
            const info = INPUT_INFO[name] ?? { label: name, unit: "" };
            return (
              <label className="field" key={name}>
                <span>
                  {info.label} ({info.unit})
                </span>
                <input
                  type="number"
                  value={values[name] ?? ""}
                  onChange={(e) => {
                    setValues({ ...values, [name]: e.target.value });
                    setResults(null);
                  }}
                />
              </label>
            );
          })}

          {optional.map((name) => {
            const info = INPUT_INFO[name] ?? { label: name, unit: "" };
            return (
              <label className="field" key={name}>
                <span>
                  {info.label} ({info.unit}), optional
                </span>
                <input
                  type="number"
                  value={values[name] ?? ""}
                  onChange={(e) => {
                    setValues({ ...values, [name]: e.target.value });
                    setResults(null);
                  }}
                />
              </label>
            );
          })}

          <label className="field">
            <span>
              Measured {PROP_SYMBOLS[prop] ?? prop.toUpperCase()} ({PROP_UNITS[prop]}), optional
            </span>
            <input
              type="number"
              value={measured[prop] ?? ""}
              onChange={(e) => {
                setMeasured({ ...measured, [prop]: e.target.value });
                setResults(null);
              }}
            />
          </label>
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
        <button className="primary" onClick={runAnalysis} disabled={!canRun}>
          {running ? "Running..." : "Run Analysis"}
        </button>
      </p>
      {selected.length === 0 && <p className="hint">Select at least one method.</p>}
      {selected.length > 0 && missingFields.length > 0 && (
        <p className="hint">
          Enter a value for:{" "}
          {missingFields.map((n) => INPUT_INFO[n]?.label ?? n).join(", ")}
        </p>
      )}
      {optionalIncomplete && (
        <p className="hint">
          Enter both separator values, or leave both blank. One value alone is ignored.
        </p>
      )}
      {runError && <p className="error">Something went wrong: {runError}</p>}

      <Recommend prop={prop} api={values.api} />

      {results && (
        <section className="card">
          <h2>Results</h2>
          <table>
            <thead>
              <tr>
                <th>Method</th>
                <th>
                  {PROP_SYMBOLS[prop] ?? prop.toUpperCase()} ({PROP_UNITS[prop]})
                </th>
                <th>Deviation from mean</th>
                {hasMeasured && <th>Error vs measured</th>}
              </tr>
            </thead>
            <tbody>
              {results.map((r) => {
                const dev = ((r.value - mean) / mean) * 100;
                const err = hasMeasured
                  ? ((r.value - measuredNum) / measuredNum) * 100
                  : null;
                return (
                  <tr key={r.key}>
                    <td>{nameOf(r.key)}</td>
                    {r.error ? (
                      <td colSpan={hasMeasured ? 3 : 2} className="error">
                        {r.error}
                      </td>
                    ) : (
                      <>
                        <td>{r.value.toFixed(digits)}</td>
                        <td>
                          {dev >= 0 ? "+" : ""}
                          {dev.toFixed(1)}%
                        </td>
                        {hasMeasured && (
                          <td>
                            {err >= 0 ? "+" : ""}
                            {err.toFixed(1)}%
                          </td>
                        )}
                      </>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="chart">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 10, left: 10, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="method" tick={{ fontSize: 12 }} interval={0} />
                <YAxis tick={{ fontSize: 12 }} width={70}>
                  <Label
                    value={`${PROP_SYMBOLS[prop] ?? prop.toUpperCase()} (${PROP_UNITS[prop]})`}
                    angle={-90}
                    position="insideLeft"
                    style={{ textAnchor: "middle", fontSize: 12 }}
                  />
                </YAxis>
                {hasMeasured && (
                  <ReferenceLine
                    y={measuredNum}
                    stroke="var(--c3)"
                    strokeDasharray="5 5"
                    ifOverflow="extendDomain"
                    label={{ value: "Measured", position: "insideTopRight", fill: "var(--c3)", fontSize: 12 }}
                  />
                )}
                <Tooltip />
                <Bar dataKey="value" fill="var(--c1)">
                  <LabelList dataKey="value" position="top" fontSize={12} formatter={(v) => v.toFixed(digits)} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="note">
            {hasMeasured
              ? "Error compares each estimate with the single measured value you entered. A positive error means the method overpredicts. One sample is not enough to say which method is more accurate overall."
              : "Differences between methods show how far the estimates spread. They do not show which method is more accurate."}
          </p>
        </section>
      )}
    </div>
  );
}

export default SingleFluid;