import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = "http://127.0.0.1:8000";

const OIL_INPUTS = [
  { name: "gor", label: "Gas-oil ratio", unit: "scf/STB" },
  { name: "bo", label: "Oil formation volume factor, Bo", unit: "bbl/STB" },
  { name: "api", label: "Oil gravity", unit: "°API" },
  { name: "c7plus", label: "Heptanes-plus content", unit: "mol%" },
];
const RESERVOIR_INPUTS = [
  { name: "pi", label: "Initial reservoir pressure", unit: "psia" },
  { name: "pb", label: "Bubble-point pressure", unit: "psia" },
  { name: "t", label: "Reservoir temperature", unit: "°F" },
  { name: "tc", label: "Critical temperature of the fluid", unit: "°F" },
];

// Distinct colours that also differ in lightness, with a legend as the main cue
const METHOD_COLOURS = ["#2563eb", "#d97706", "#16a34a", "#9333ea", "#0f766e"];

const fmt = (v, d = 2) => (v === null || v === undefined ? "–" : Number(v).toFixed(d));
const range = (r, d = 0) => (r ? `${Number(r[0]).toFixed(d)} to ${Number(r[1]).toFixed(d)}` : "–");

function ClassifyFluid() {
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [criteria, setCriteria] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch(`${API}/classify/criteria`)
      .then((r) => {
        if (!r.ok) throw new Error(`API returned ${r.status}`);
        return r.json();
      })
      .then(setCriteria)
      .catch((e) => setError(e.message));
  }, []);

  const filled = (name) => values[name] !== undefined && values[name] !== "";
  const anyOil = OIL_INPUTS.some((f) => filled(f.name));
  const pressurePair = filled("pi") && filled("pb");
  const temperaturePair = filled("t") && filled("tc");
  const canRun = (anyOil || pressurePair || temperaturePair) && !running;
  const halfPair =
    (filled("pi") !== filled("pb")) || (filled("t") !== filled("tc"));

  function setValue(name, v) {
    setValues({ ...values, [name]: v });
    setResult(null);
  }

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const body = {};
      for (const f of [...OIL_INPUTS, ...RESERVOIR_INPUTS]) {
        if (filled(f.name)) body[f.name] = Number(values[f.name]);
      }
      const res = await fetch(`${API}/classify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
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

  function field(f) {
    return (
      <label className="field" key={f.name}>
        <span>
          {f.label} ({f.unit}), optional
        </span>
        <input
          type="number"
          value={values[f.name] ?? ""}
          onChange={(e) => setValue(f.name, e.target.value)}
        />
      </label>
    );
  }

  return (
    <div>
      <div className="panels">
        <section className="card">
          <h2>Oil properties</h2>
          {OIL_INPUTS.map(field)}
        </section>
        <section className="card">
          <h2>Reservoir conditions</h2>
          {RESERVOIR_INPUTS.map(field)}
        </section>
      </div>

      <p>
        <button className="primary" onClick={run} disabled={!canRun}>
          {running ? "Working..." : "Classify"}
        </button>
      </p>
      {halfPair && (
        <p className="hint">
          Pressure and temperature checks each need both values. A single value is ignored.
        </p>
      )}
      {error && <p className="error">Something went wrong: {error}</p>}

      {result && (
        <>
          {result.oil && (
            <section className="card">
              <h2>Oil type</h2>
              <p>
                <strong>{result.oil.verdict}</strong>
              </p>
              <table>
                <thead>
                  <tr>
                    <th>Class</th>
                    <th>Property</th>
                    <th>Your value</th>
                    <th>Published limit</th>
                    <th>Within limit</th>
                  </tr>
                </thead>
                <tbody>
                  {result.oil.classes.map((c) =>
                    c.checks.length === 0 ? (
                      <tr key={c.key}>
                        <td>{c.name}</td>
                        <td colSpan={4}>No matching property entered</td>
                      </tr>
                    ) : (
                      c.checks.map((k, i) => (
                        <tr key={c.key + k.param}>
                          {i === 0 && <td rowSpan={c.checks.length}>{c.name}</td>}
                          <td>{k.label}</td>
                          <td>
                            {k.value} {k.unit}
                          </td>
                          <td>{k.rule}</td>
                          <td>{k.passed ? "Yes" : "No"}</td>
                        </tr>
                      ))
                    )
                  )}
                </tbody>
              </table>
              {result.oil.notes.map((n) => (
                <p className="note" key={n}>
                  {n}
                </p>
              ))}
              {result.oil.matches.length === 1 && (
                <p>
                  <Link to={`/phase?type=${result.oil.matches[0]}`}>See the phase diagram for this oil type</Link>
                </p>
              )}
            </section>
          )}

          {(result.pressure_state || result.reservoir_kind) && (
            <section className="card">
              <h2>Reservoir type</h2>
              {result.reservoir_kind && (
                <p>
                  <strong>{result.reservoir_kind.name}.</strong> {result.reservoir_kind.text}
                </p>
              )}
              {result.pressure_state && (
                <p>
                  <strong>{result.pressure_state.name}.</strong> {result.pressure_state.text}
                  {result.pressure_state.key === "saturated" &&
                    ` Pressures within ${result.pressure_state.tolerance_psi} psi are treated as equal.`}
                </p>
              )}
              <p className="note">Source: Ahmed, Reservoir Engineering Handbook, p. 3.</p>
            </section>
          )}
        </>
      )}

      {criteria && (
        <section className="card">
          <h2>Limits used</h2>
          <table>
            <thead>
              <tr>
                <th>Class</th>
                <th>Property</th>
                <th>Limit</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {criteria.map((c) =>
                c.criteria.map((k, i) => (
                  <tr key={c.key + k.param}>
                    {i === 0 && <td rowSpan={c.criteria.length}>{c.name}</td>}
                    <td>
                      {k.label} ({k.unit})
                    </td>
                    <td>{k.rule}</td>
                    {i === 0 && <td rowSpan={c.criteria.length}>Ahmed, {c.page}</td>}
                  </tr>
                ))
              )}
            </tbody>
          </table>
          <p className="note">
            These are typical values quoted in the source, not sharp cut-offs, and the ranges leave gaps. Ranges
            written as "between" are treated as including both ends. Ordinary black oil has no Bo limit in the
            source, and near-critical oil has no gravity limit.
          </p>
        </section>
      )}
    </div>
  );
}

function ClassifyDataset() {
  const [data, setData] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const res = await fetch(`${API}/classify/dataset`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      setData(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    run();
  }, []);

  if (error) return <p className="error">Could not reach the API: {error}</p>;
  if (!data) return <p>{running ? "Classifying the dataset..." : ""}</p>;

  const groups = [...data.classes.filter((c) => c.n > 0), data.outside];
  const methodList = data.outside.methods;
  const chartData = groups.map((g) => {
    const row = { group: `${g.name} (n=${g.n})` };
    g.methods.forEach((m) => {
      row[m.name] = m.aae === null ? null : Number(m.aae.toFixed(2));
    });
    return row;
  });

  function aaeTable(blocks, title) {
    return (
      <table>
        <thead>
          <tr>
            <th>{title}</th>
            <th>N</th>
            {methodList.map((m) => (
              <th key={m.key}>{m.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {blocks.map((b) => {
            const best = Math.min(...b.methods.filter((m) => m.aae !== null).map((m) => m.aae));
            return (
              <tr key={b.key}>
                <td>{b.name}</td>
                <td>{b.n}</td>
                {b.methods.map((m) => (
                  <td key={m.key} style={m.aae === best ? { fontWeight: 700 } : undefined}>
                    {fmt(m.aae)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  const outsideShare = (data.outside.share * 100).toFixed(1);

  return (
    <div>
      <section className="card">
        <h2>Where the {data.rows_used} oils fall</h2>
        <p>
          <strong>
            {data.outside.n} of {data.rows_used} oils ({outsideShare}%) fit none of the four classes
          </strong>{" "}
          when the limits in the source are applied as written. {data.n_in_gor_gap} oils have a gas-oil ratio between
          700 and 2,000 scf/STB, where the source gives no class.
        </p>
        <table>
          <thead>
            <tr>
              <th>Class</th>
              <th>N</th>
              <th>Share</th>
              <th>Gas-oil ratio (scf/STB)</th>
              <th>Gravity (°API)</th>
              <th>Bo (bbl/STB)</th>
            </tr>
          </thead>
          <tbody>
            {groups.concat(data.classes.filter((c) => c.n === 0)).map((g) => (
              <tr key={g.key}>
                <td>{g.name}</td>
                <td>{g.n}</td>
                <td>{(g.share * 100).toFixed(1)}%</td>
                <td>{range(g.gor_range)}</td>
                <td>{range(g.api_range, 1)}</td>
                <td>{range(g.bo_range, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="note">
          {data.n_gor_2000_plus} oils have a gas-oil ratio of 2,000 scf/STB or more, and {data.n_gor_2000_plus_bo_below_2}{" "}
          of them have Bo below 2.0. The published volatile oil needs both, so no oil in this dataset meets the printed
          limits for volatile oil.
        </p>
      </section>

      <section className="card">
        <h2>Bo accuracy by class, average absolute error (%)</h2>
        {aaeTable(groups, "Class")}
        <div className="chart">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} margin={{ top: 20, right: 10, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="group" tick={{ fontSize: 11 }} interval={0} />
              <YAxis tick={{ fontSize: 12 }} width={50} />
              <Tooltip />
              <Legend />
              {methodList.map((m, i) => (
                <Bar key={m.key} dataKey={m.name} isAnimationActive={false} fill={METHOD_COLOURS[i % METHOD_COLOURS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="note">
          The best method in each row is in bold. Groups with few oils say little. Near-critical oil has only{" "}
          {data.classes.find((c) => c.key === "near_critical")?.n} oils here.
        </p>
      </section>

      <section className="card">
        <h2>Bo accuracy by gas-oil ratio band, average absolute error (%)</h2>
        {aaeTable(data.gor_bands, "Gas-oil ratio band")}
        <p className="note">
          These bands are not a classification from the source. They show how the error changes as the oil carries
          more gas.
        </p>
      </section>

      {data.notes.map((n) => (
        <p className="note" key={n}>
          {n}
        </p>
      ))}
    </div>
  );
}

function Classification() {
  const [tab, setTab] = useState("fluid");
  return (
    <div>
      <h1>Oil Classification</h1>
      <p className="subtitle">
        Classify a crude oil and its reservoir with published limits for each oil type.
      </p>
      <div className="segmented">
        <button className={tab === "fluid" ? "seg active" : "seg"} onClick={() => setTab("fluid")}>
          Classify a fluid
        </button>
        <button className={tab === "dataset" ? "seg active" : "seg"} onClick={() => setTab("dataset")}>
          Classify the dataset
        </button>
      </div>
      {tab === "fluid" ? <ClassifyFluid /> : <ClassifyDataset />}
    </div>
  );
}

export default Classification;
