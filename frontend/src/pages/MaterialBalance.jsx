import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = "http://127.0.0.1:8000";
const COLOURS = ["#2563eb", "#d97706", "#16a34a", "#9333ea"];

const f = (v, d = 3) => (v === null || v === undefined || Number.isNaN(v) ? "n/a" : Number(v).toFixed(d));
const big = (v, d = 2) => (v === null || v === undefined ? "n/a" : (Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(d) + " million" : Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })));
const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));

// Lines of values separated by spaces, commas or tabs. A dash or n/a marks a blank value. Lines with other text are ignored.
const parse = (text) =>
  text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => l.split(/[\s,;]+/).map((t) => (/^(-|–|n\/a|na)$/i.test(t) ? null : Number(t))))
    .filter((r) => r.length && r.every((v) => v === null || Number.isFinite(v)));

async function post(url, body) {
  const r = await fetch(API + url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await r.json();
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "The input could not be used.");
  return data;
}

function Num({ label, value, onChange, hint }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" step="any" value={value} onChange={(e) => onChange(e.target.value)} />
      {hint && <small className="note">{hint}</small>}
    </label>
  );
}

function Lines({ label, value, onChange, rows = 6 }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ width: "100%", boxSizing: "border-box", fontFamily: "monospace", fontSize: 13, padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}
      />
    </label>
  );
}

function Pick({ label, value, onChange, options }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}

function Table({ head, rows }) {
  return (
    <table>
      <thead>
        <tr>{head.map((h) => <th key={h}>{h}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}

// Scatter chart with optional straight line and optional log y axis.
function XY({ series, xLabel, yLabel, height = 300, logY = false }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 10, right: 20, left: 10, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="x" type="number" domain={["auto", "auto"]} tick={{ fontSize: 12 }} tickFormatter={(v) => (Math.abs(v) >= 1e5 ? v.toExponential(1) : v)}
                 label={{ value: xLabel, position: "insideBottom", offset: -12, fontSize: 12 }} />
          <YAxis dataKey="y" type="number" scale={logY ? "log" : "auto"} domain={logY ? [0.01, 1] : ["auto", "auto"]} allowDataOverflow={logY}
                 tick={{ fontSize: 12 }} width={72} tickFormatter={(v) => (Math.abs(v) >= 1e5 ? v.toExponential(1) : v)}
                 label={{ value: yLabel, angle: -90, position: "insideLeft", style: { textAnchor: "middle", fontSize: 12 } }} />
          <Tooltip formatter={(v) => (typeof v === "number" ? Number(v.toPrecision(5)) : v)} />
          <Legend verticalAlign="top" height={28} />
          {series.map((s, i) => (
            <Scatter key={s.name} name={s.name} data={s.data} fill={COLOURS[i % COLOURS.length]} stroke={COLOURS[i % COLOURS.length]}
                     line={s.line ? { strokeWidth: 2 } : false} shape={s.line ? () => null : undefined} isAnimationActive={false} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

const TABS = [
  ["series", "Straight-line analysis"],
  ["point", "Oil in place and drive indexes"],
  ["sat", "Saturations and kr ratio"],
  ["tracy", "Tracy form"],
  ["avg", "Average pressure"],
];

const NP_UNITS = [["1", "STB"], ["1000", "MSTB"], ["1000000", "MMSTB"]];
const GP_UNITS = [["1", "scf"], ["1000", "Mscf"], ["1000000", "MMscf"], ["1000000000", "Bscf"]];
const SOURCE = "Source: Ahmed, Reservoir Engineering Handbook, pp. 751 to 818.";

const CASES = [
  ["volumetric_undersaturated", "Volumetric undersaturated (F against Eo + Ef,w)"],
  ["saturated", "Volumetric saturated (F against Eo)"],
  ["gas_cap", "Gas cap (F/Eo against Eg/Eo)"],
  ["water_drive_pot", "Water drive, pot aquifer (F/Eo against Δp/Eo)"],
];

const lines = (rows, keys) => rows.map((r) => keys.map((k) => (r[k] === undefined || r[k] === null ? "-" : r[k])).join(" ")).join("\n");

export default function MaterialBalance() {
  const [tab, setTab] = useState("series");
  const [ex, setEx] = useState(null);
  const [checks, setChecks] = useState(null);
  const [error, setError] = useState(null);
  const [out, setOut] = useState({});

  // Fluid and rock properties shared by the tabs
  const [fl, setFl] = useState({ pi: "", boi: "", rsi: "", bgi: "", bti: "", swi: "0", cw: "0", cf: "0", bw: "1" });
  const setF = (k) => (v) => setFl((s) => ({ ...s, [k]: v }));
  const fluid = () => ({
    pi: Number(fl.pi), boi: Number(fl.boi), rsi: num(fl.rsi), bgi: num(fl.bgi), bti: num(fl.bti),
    swi: Number(fl.swi || 0), cw: Number(fl.cw || 0), cf: Number(fl.cf || 0), bw: Number(fl.bw || 1),
  });
  const [units, setUnits] = useState({ np: "1", gp: "1", wp: "1" });
  const setU = (k) => (v) => setUnits((s) => ({ ...s, [k]: v }));
  const scales = () => ({ np_scale: Number(units.np), gp_scale: Number(units.gp), wp_scale: Number(units.wp) });

  // series tab
  const [s, setS] = useState({ kase: "volumetric_undersaturated", mode: "pvt", basis: "gp", m: "", efw: false, rows: "" });
  // point tab
  const [pt, setPt] = useState({ solve: "we", p: "", bo: "", rs: "", bg: "", bt: "", np: "", gp: "", wp: "0", basis: "gp", n: "", we: "", m: "", efw: true });
  // saturation tab
  const [st, setSt] = useState({ boi: "", swi: "", n: "", re: "", h: "", phi: "", npScale: "1000000", rows: "" });
  // Tracy tab
  const [tr, setTr] = useState({ boi: "", rsi: "", bgi: "", m: "0", bw: "1", rows: "" });
  // average pressure tab
  const [av, setAv] = useState({ n: "", m: "0", np: "", gp: "", wp: "0", pvt: "" });

  useEffect(() => {
    fetch(`${API}/mb/examples`).then((r) => r.json()).then(setEx).catch(() => {});
    fetch(`${API}/mb/verification`).then((r) => r.json()).then(setChecks).catch(() => {});
  }, []);

  const guard = async (fn) => {
    setError(null);
    try { await fn(); } catch (e) { setError(e.message); }
  };

  const loadFluid = (x, extra = {}) =>
    setFl({ pi: String(x.pi), boi: String(x.boi), rsi: x.rsi == null ? "" : String(x.rsi), bgi: x.bgi == null ? "" : String(x.bgi),
            bti: x.bti == null ? "" : String(x.bti), swi: String(x.swi ?? 0), cw: String(x.cw ?? 0), cf: String(x.cf ?? 0), bw: String(x.bw ?? 1), ...extra });

  // ---- series ----
  const loadSeries = (key, kase, extra = {}) => {
    if (!ex) return;
    const e = ex.series[key];
    loadFluid(e.fluid);
    const direct = e.rows[0].f !== undefined;
    setUnits({ np: String(e.np_scale || 1), gp: String(e.gp_scale || 1), wp: String(e.wp_scale || 1) });
    setS((o) => ({
      ...o, kase, mode: direct ? "direct" : "pvt", basis: key === "practice" ? "rp" : "gp", m: "", efw: false,
      rows: direct ? lines(e.rows, ["p", "f", "eo", "eg"]) : lines(e.rows, ["p", "bo", "rs", "bg", "bt", "n_p", "g_p", "w_p"]),
      ...extra,
    }));
    setOut({});
    setError(null);
  };

  const runSeries = () => guard(async () => {
    const rows = parse(s.rows).map((r) =>
      s.mode === "direct" ? { p: r[0], f: r[1], eo: r[2], eg: r[3] ?? null }
        : { p: r[0], bo: r[1], rs: r[2], bg: r[3], bt: r[4], n_p: r[5] ?? 0, g_p: r[6], w_p: r[7] ?? 0 });
    const r = await post("/mb/series", { case: s.kase, fluid: fluid(), rows, m: num(s.m), include_efw: s.efw, gas_basis: s.basis, ...scales() });
    setOut((o) => ({ ...o, series: r }));
  });

  // ---- point ----
  const loadPoint = (key, solve) => {
    if (!ex) return;
    const e = ex.point[key];
    loadFluid(e.fluid);
    setUnits({ np: "1", gp: "1", wp: "1" });
    setPt({
      solve, p: String(e.p), bo: e.bo == null ? "" : String(e.bo), rs: e.rs == null ? "" : String(e.rs), bg: e.bg == null ? "" : String(e.bg),
      bt: e.bt == null ? "" : String(e.bt), np: String(e.n_p), gp: String(e.g_p), wp: String(e.w_p), basis: "gp",
      n: e.n == null ? "" : String(e.n), we: e.we == null ? "" : String(e.we), m: e.m == null ? "" : String(e.m), efw: true,
    });
    setOut({});
    setError(null);
  };

  const runPoint = () => guard(async () => {
    const r = await post("/mb/point", {
      solve: pt.solve, fluid: fluid(), p: Number(pt.p), bo: num(pt.bo), rs: num(pt.rs), bg: num(pt.bg), bt: num(pt.bt),
      n_p: Number(pt.np), g_p: num(pt.gp), w_p: Number(pt.wp || 0), gas_basis: pt.basis, ...scales(),
      n: num(pt.n), we: num(pt.we), m: num(pt.m), include_efw: pt.efw,
    });
    setOut((o) => ({ ...o, point: r }));
  });

  // ---- saturation ----
  const loadSat = () => {
    if (!ex) return;
    const e = ex.saturation;
    setSt({ boi: String(e.boi), swi: String(e.swi), n: "", re: String(e.re_ft), h: String(e.h_ft), phi: String(e.phi), npScale: "1000000",
            rows: lines(e.rows, ["p", "bo", "rs", "bg", "n_p", "qo", "qg", "mu_ratio"]) });
    setOut({});
    setError(null);
  };

  const runSat = () => guard(async () => {
    const rows = parse(st.rows).map((r) => ({ p: r[0], bo: r[1], rs: r[2], bg: r[3], n_p: r[4] ?? 0, qo: r[5], qg: r[6], mu_ratio: r[7] }));
    const r = await post("/mb/saturation", {
      boi: Number(st.boi), swi: Number(st.swi), n: num(st.n), re_ft: num(st.re), h_ft: num(st.h), phi: num(st.phi),
      np_scale: Number(st.npScale), rows,
    });
    setOut((o) => ({ ...o, sat: r }));
  });

  // ---- Tracy ----
  const runTracy = () => guard(async () => {
    const rows = parse(tr.rows).map((r) => ({ p: r[0], bo: r[1], rs: r[2], bg: r[3], n_p: r[4], g_p: r[5], w_p: r[6] ?? 0, we: r[7] ?? 0 }));
    const r = await post("/mb/tracy", { boi: Number(tr.boi), rsi: Number(tr.rsi), bgi: Number(tr.bgi), m: Number(tr.m || 0), bw: Number(tr.bw || 1), rows, ...scales() });
    setOut((o) => ({ ...o, tracy: r }));
  });

  // ---- average pressure ----
  const loadAvg = () => {
    if (!ex) return;
    const e = ex.average_pressure;
    loadFluid(e.fluid);
    setUnits({ np: "1", gp: "1", wp: "1" });
    setAv({ n: String(Math.round(e.n)), m: String(e.m), np: String(Math.round(e.n_p)), gp: String(Math.round(e.g_p)), wp: "0", pvt: lines(e.pvt, ["p", "bo", "rs", "bg"]) });
    setOut({});
    setError(null);
  };

  const runAvg = () => guard(async () => {
    const pvt = parse(av.pvt).map((r) => ({ p: r[0], bo: r[1], rs: r[2], bg: r[3] }));
    const r = await post("/mb/average_pressure", {
      fluid: fluid(), n: Number(av.n), m: Number(av.m || 0), n_p: Number(av.np), g_p: Number(av.gp), w_p: Number(av.wp || 0), pvt, ...scales(),
    });
    setOut((o) => ({ ...o, avg: r }));
  });

  const fluidPanel = ({ withGas = true, withRock = true } = {}) => (
    <div className="panels">
      <div>
        <Num label="Initial pressure (psi)" value={fl.pi} onChange={setF("pi")} />
        <Num label="Initial oil formation volume factor Boi (bbl/STB)" value={fl.boi} onChange={setF("boi")} />
        {withGas && <Num label="Initial solution gas-oil ratio Rsi (scf/STB)" value={fl.rsi} onChange={setF("rsi")} />}
        {withGas && <Num label="Initial gas formation volume factor Bgi (bbl/scf)" value={fl.bgi} onChange={setF("bgi")} />}
      </div>
      {withRock && (
        <div>
          <Num label="Initial two-phase factor Bti (bbl/STB), blank to use Boi" value={fl.bti} onChange={setF("bti")} />
          <Num label="Initial water saturation (fraction)" value={fl.swi} onChange={setF("swi")} />
          <Num label="Water compressibility cw (1/psi)" value={fl.cw} onChange={setF("cw")} />
          <Num label="Rock compressibility cf (1/psi)" value={fl.cf} onChange={setF("cf")} />
          <Num label="Water formation volume factor Bw (bbl/STB)" value={fl.bw} onChange={setF("bw")} />
        </div>
      )}
    </div>
  );

  const unitPanel = ({ gas = true, water = true } = {}) => (
    <div className="panels">
      <Pick label="Cumulative oil is entered in" value={units.np} onChange={setU("np")} options={NP_UNITS} />
      {gas && <Pick label="Cumulative gas is entered in" value={units.gp} onChange={setU("gp")} options={GP_UNITS} />}
      {water && <Pick label="Cumulative water is entered in" value={units.wp} onChange={setU("wp")} options={NP_UNITS} />}
    </div>
  );

  const fit = out.series && out.series.fit;
  const seriesRows = out.series ? out.series.rows : [];

  return (
    <div>
      <h1>Material Balance</h1>
      <p className="subtitle">
        Find the initial oil in place, the water influx and the size of the gas cap from production history and fluid properties, see how much
        each drive contributes, and work out saturations and the field relative permeability ratio. Each calculation is checked against
        published worked examples at the bottom of the page.
      </p>

      <section className="card">
        <details>
          <summary style={{ cursor: "pointer", fontWeight: 600 }}>Drive mechanisms and typical recovery</summary>
          {ex && (
            <Table head={["Drive", "Recovery (% of initial oil in place)", "Note"]} rows={ex.drives.map((d) => [d.drive, d.recovery, d.note])} />
          )}
          <p className="note">
            The equation assumes a constant temperature, one average pressure across the reservoir, constant reservoir volume apart from
            the rock and water expansion and influx that are included, and reliable production data. It is least reliable early in the
            depletion, when pressure changes are small.
          </p>
        </details>
      </section>

      <div className="segmented">
        {TABS.map(([k, label]) => (
          <button key={k} className={k === tab ? "seg active" : "seg"} onClick={() => { setTab(k); setError(null); }}>{label}</button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}

      {tab === "series" && (
        <section className="card">
          <h2>Straight-line analysis</h2>
          <p className="note">
            Havlena and Odeh. Production and PVT data at several pressures go in. The terms F, Eo, Eg and Ef,w are worked out at each row and
            plotted in the form that gives a straight line for the case chosen. Rows at or above the initial pressure are left out.
          </p>
          <p>
            <button className="seg" onClick={() => loadSeries("volumetric", "volumetric_undersaturated")}>Load volumetric undersaturated example</button>{" "}
            <button className="seg" onClick={() => loadSeries("gas_cap", "gas_cap")}>Load gas cap example (production data)</button>{" "}
            <button className="seg" onClick={() => loadSeries("gas_cap_printed", "gas_cap")}>Load gas cap example (printed F, Eo, Eg)</button>{" "}
            <button className="seg" onClick={() => loadSeries("water_drive", "water_drive_pot")}>Load pot aquifer example</button>{" "}
            <button className="seg" onClick={() => loadSeries("practice", "gas_cap")}>Load practice data set (no published solution)</button>
          </p>
          <Pick label="Case" value={s.kase} onChange={(v) => setS((o) => ({ ...o, kase: v }))} options={CASES} />
          {fluidPanel()}
          {unitPanel()}
          <div className="panels">
            <Pick label="Table columns" value={s.mode} onChange={(v) => setS((o) => ({ ...o, mode: v }))}
                  options={[["pvt", "Pressure, Bo, Rs, Bg, Bt, Np, Gp, Wp"], ["direct", "Pressure, F, Eo, Eg"]]} />
            {s.mode === "pvt" && <Pick label="Gas column holds" value={s.basis} onChange={(v) => setS((o) => ({ ...o, basis: v }))}
                  options={[["gp", "Cumulative gas produced"], ["rp", "Cumulative gas-oil ratio (scf/STB)"]]} />}
          </div>
          <div className="panels">
            <Num label="Known gas cap ratio m (optional, gas cap and saturated cases)" value={s.m} onChange={(v) => setS((o) => ({ ...o, m: v }))} />
            <label className="field">
              <span>Include rock and water expansion (saturated and gas cap cases)</span>
              <input type="checkbox" checked={s.efw} onChange={(e) => setS((o) => ({ ...o, efw: e.target.checked }))} />
            </label>
          </div>
          <Lines label={s.mode === "pvt" ? "Pressure, Bo, Rs, Bg, Bt, Np, Gp, Wp. Use a dash for a blank. Use Bt or Bo, not both needed." : "Pressure, F (bbl), Eo (bbl/STB), Eg (bbl/STB)"}
                 value={s.rows} onChange={(v) => setS((o) => ({ ...o, rows: v }))} rows={9} />
          <button className="primary" onClick={runSeries}>Calculate</button>

          {out.series && (
            <>
              <h3>Result</h3>
              <p>
                Initial oil in place N is <strong>{big(fit.n)} STB</strong>.
                {fit.m !== undefined && fit.m !== null && <> The gas cap ratio m is <strong>{f(fit.m, 2)}</strong>.</>}
                {fit.k !== undefined && <> The aquifer constant K is <strong>{f(fit.k, 0)}</strong> bbl/psi.</>}
              </p>
              {fit.m !== undefined && fit.m !== null && !s.m && (
                <p className="note">m is the slope divided by the intercept, so it changes a lot when the points scatter or when there are only a few of them.</p>
              )}
              {fit.m !== undefined && fit.m !== null && fit.m < 0 && (
                <p className="note">A negative m is not physical. It means these points do not show a gas cap, so treat N here with care and check the input data.</p>
              )}
              {out.series.notes.map((n) => <p className="note" key={n}>{n}</p>)}
              <XY xLabel={fit.x_label} yLabel={fit.y_label}
                  series={[{ name: "Data", data: seriesRows.filter((r) => r.x !== null && r.y !== null).map((r) => ({ x: r.x, y: r.y })) },
                           { name: "Fitted line", data: (fit.line || []).map((l) => ({ x: l.x, y: l.y })), line: true }]} />
              <Table head={["Pressure (psi)", "Δp (psi)", "F (bbl)", "Eo (bbl/STB)", "Eg (bbl/STB)", "Ef,w (bbl/STB)", "N from this point (STB)"]}
                     rows={seriesRows.map((r) => [r.p, f(r.dp, 0), big(r.f), f(r.eo, 4), f(r.eg, 4), r.efw ? f(r.efw, 6) : "", r.n_point === null || r.n_point === undefined ? "" : big(r.n_point)])} />
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "point" && (
        <section className="card">
          <h2>Oil in place, water influx and drive indexes</h2>
          <p className="note">
            One pressure at a time. Choose the unknown and give the other two of N, We and m. When all three are known the four drive indexes
            (depletion, segregation, water and expansion) are shown and add to one.
          </p>
          <p>
            <button className="seg" onClick={() => loadPoint("ex111", "we")}>Load published example (water influx)</button>{" "}
            <button className="seg" onClick={() => loadPoint("ex112", "n")}>Load published example (oil in place)</button>
          </p>
          <Pick label="Solve for" value={pt.solve} onChange={(v) => setPt((o) => ({ ...o, solve: v }))}
                options={[["n", "Initial oil in place N"], ["we", "Cumulative water influx We"], ["m", "Gas cap ratio m"]]} />
          {fluidPanel()}
          {unitPanel()}
          <div className="panels">
            <div>
              <Num label="Current pressure (psi)" value={pt.p} onChange={(v) => setPt((o) => ({ ...o, p: v }))} />
              <Num label="Bo (bbl/STB)" value={pt.bo} onChange={(v) => setPt((o) => ({ ...o, bo: v }))} />
              <Num label="Rs (scf/STB)" value={pt.rs} onChange={(v) => setPt((o) => ({ ...o, rs: v }))} />
              <Num label="Bg (bbl/scf)" value={pt.bg} onChange={(v) => setPt((o) => ({ ...o, bg: v }))} />
              <Num label="Bt (bbl/STB), optional" value={pt.bt} onChange={(v) => setPt((o) => ({ ...o, bt: v }))} />
            </div>
            <div>
              <Num label="Cumulative oil Np" value={pt.np} onChange={(v) => setPt((o) => ({ ...o, np: v }))} />
              <Num label="Cumulative gas Gp (or Rp)" value={pt.gp} onChange={(v) => setPt((o) => ({ ...o, gp: v }))} />
              <Pick label="Gas value is" value={pt.basis} onChange={(v) => setPt((o) => ({ ...o, basis: v }))}
                    options={[["gp", "Cumulative gas produced"], ["rp", "Cumulative gas-oil ratio (scf/STB)"]]} />
              <Num label="Cumulative water Wp" value={pt.wp} onChange={(v) => setPt((o) => ({ ...o, wp: v }))} />
            </div>
            <div>
              {pt.solve !== "n" && <Num label="Initial oil in place N (STB)" value={pt.n} onChange={(v) => setPt((o) => ({ ...o, n: v }))} />}
              {pt.solve !== "we" && <Num label="Cumulative water influx We (bbl)" value={pt.we} onChange={(v) => setPt((o) => ({ ...o, we: v }))} />}
              {pt.solve !== "m" && <Num label="Gas cap ratio m" value={pt.m} onChange={(v) => setPt((o) => ({ ...o, m: v }))} />}
              <label className="field">
                <span>Include rock and water expansion</span>
                <input type="checkbox" checked={pt.efw} onChange={(e) => setPt((o) => ({ ...o, efw: e.target.checked }))} />
              </label>
            </div>
          </div>
          <button className="primary" onClick={runPoint}>Calculate</button>
          {out.point && (
            <>
              <h3>Result</h3>
              <p>
                {out.point.n !== undefined && <>Initial oil in place is <strong>{big(out.point.n)} STB</strong>. </>}
                {out.point.we !== undefined && <>Cumulative water influx is <strong>{big(out.point.we, 3)} bbl</strong>
                  {out.point.net_influx !== undefined && <> and the net influx is <strong>{big(out.point.net_influx, 3)} bbl</strong></>}. </>}
                {out.point.m !== undefined && <>The gas cap ratio is <strong>{f(out.point.m, 3)}</strong>. </>}
              </p>
              <Table head={["F (bbl)", "Eo (bbl/STB)", "Eg (bbl/STB)", "Ef,w (bbl/STB)"]} rows={[[big(out.point.f), f(out.point.eo, 4), f(out.point.eg, 4), f(out.point.efw, 6)]]} />
              {out.point.indexes && (
                <>
                  <h3>Drive indexes</h3>
                  <Table head={["Depletion", "Segregation (gas cap)", "Water", "Expansion", "Sum"]}
                         rows={[[f(out.point.indexes.ddi, 4), f(out.point.indexes.sdi, 4), f(out.point.indexes.wdi, 4), f(out.point.indexes.edi, 4), f(out.point.indexes.sum, 4)]]} />
                  <p className="note">
                    A larger depletion index means the field is being produced mainly by pressure decline. A larger water or gas cap index means
                    the pressure is being supported. The rock and fluid expansion index is usually small when there is a gas cap or when the
                    pressure is below the bubble point.
                  </p>
                </>
              )}
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "sat" && (
        <section className="card">
          <h2>Saturations and field relative permeability ratio</h2>
          <p className="note">
            For a volumetric oil reservoir with no water influx. The oil in the drainage area comes from the drainage radius, thickness and
            porosity, or is given directly. Rates and the viscosity ratio give the ratio krg/kro against gas saturation.
          </p>
          <p><button className="seg" onClick={loadSat}>Load published example</button></p>
          <div className="panels">
            <div>
              <Num label="Initial oil formation volume factor Boi (bbl/STB)" value={st.boi} onChange={(v) => setSt((o) => ({ ...o, boi: v }))} />
              <Num label="Initial water saturation (fraction)" value={st.swi} onChange={(v) => setSt((o) => ({ ...o, swi: v }))} />
              <Pick label="Cumulative oil is entered in" value={st.npScale} onChange={(v) => setSt((o) => ({ ...o, npScale: v }))} options={NP_UNITS} />
            </div>
            <div>
              <Num label="Drainage radius (ft)" value={st.re} onChange={(v) => setSt((o) => ({ ...o, re: v }))} />
              <Num label="Net thickness (ft)" value={st.h} onChange={(v) => setSt((o) => ({ ...o, h: v }))} />
              <Num label="Porosity (fraction)" value={st.phi} onChange={(v) => setSt((o) => ({ ...o, phi: v }))} />
              <Num label="Or give the oil in the drainage area N (STB)" value={st.n} onChange={(v) => setSt((o) => ({ ...o, n: v }))} />
            </div>
          </div>
          <Lines label="Pressure, Bo, Rs, Bg, Np, Qo (STB/day), Qg (MMscf/day), μo/μg. Use a dash for a blank." value={st.rows} onChange={(v) => setSt((o) => ({ ...o, rows: v }))} rows={9} />
          <button className="primary" onClick={runSat}>Calculate</button>
          {out.sat && (
            <>
              <p>The oil in the drainage area is <strong>{big(out.sat.n, 3)} STB</strong>.</p>
              <XY logY xLabel="Gas saturation" yLabel="krg/kro"
                  series={[{ name: "krg/kro", data: out.sat.rows.filter((r) => r.krg_kro && r.sg > 0).map((r) => ({ x: r.sg, y: r.krg_kro })) }]} />
              <Table head={["Pressure (psi)", "So", "Sg", "GOR (scf/STB)", "krg/kro"]}
                     rows={out.sat.rows.map((r) => [r.p, f(r.so, 4), f(r.sg, 4), r.gor === null ? "" : f(r.gor, 1), r.krg_kro === null ? "" : f(r.krg_kro, 4)])} />
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "tracy" && (
        <section className="card">
          <h2>Tracy form</h2>
          <p className="note">
            Tracy's rearrangement of the equation, N = Np Φo + Gp Φg + (Wp Bw − We) Φw, for a reservoir at its bubble point at the start. It is
            not valid above the bubble point. The functions go to infinity at the bubble point, so points just below it can give a poor N.
          </p>
          <div className="panels">
            <div>
              <Num label="Initial Bo (bbl/STB), taken at the bubble point" value={tr.boi} onChange={(v) => setTr((o) => ({ ...o, boi: v }))} />
              <Num label="Initial Rs (scf/STB)" value={tr.rsi} onChange={(v) => setTr((o) => ({ ...o, rsi: v }))} />
              <Num label="Initial Bg (bbl/scf)" value={tr.bgi} onChange={(v) => setTr((o) => ({ ...o, bgi: v }))} />
            </div>
            <div>
              <Num label="Gas cap ratio m" value={tr.m} onChange={(v) => setTr((o) => ({ ...o, m: v }))} />
              <Num label="Bw (bbl/STB)" value={tr.bw} onChange={(v) => setTr((o) => ({ ...o, bw: v }))} />
            </div>
          </div>
          {unitPanel()}
          <Lines label="Pressure, Bo, Rs, Bg, Np, Gp, Wp, We (bbl). Wp and We can be left off." value={tr.rows} onChange={(v) => setTr((o) => ({ ...o, rows: v }))} rows={7} />
          <button className="primary" onClick={runTracy}>Calculate</button>
          {out.tracy && (
            <>
              <Table head={["Pressure (psi)", "Φo", "Φg", "Φw", "N (STB)"]}
                     rows={out.tracy.rows.map((r) => [r.p, f(r.phi_o, 3), f(r.phi_g, 4), f(r.phi_w, 3), big(r.n)])} />
              {out.tracy.notes.map((n) => <p className="note" key={n}>{n}</p>)}
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "avg" && (
        <section className="card">
          <h2>Average reservoir pressure</h2>
          <p className="note">
            When the oil in place and the gas cap ratio are known from other work, the equation can estimate the average pressure at a given
            production. The pressure is where the production side and the expansion side of the equation are equal.
          </p>
          <p><button className="seg" onClick={loadAvg}>Load check data (answer 2,880 psi)</button></p>
          <p className="note">The check data uses the oil properties of the saturation example, with the cumulative gas worked out from the equation at 2,880 psi. It is a round trip test, not a published case.</p>
          {fluidPanel({ withRock: false })}
          {unitPanel()}
          <div className="panels">
            <div>
              <Num label="Initial oil in place N (STB)" value={av.n} onChange={(v) => setAv((o) => ({ ...o, n: v }))} />
              <Num label="Gas cap ratio m" value={av.m} onChange={(v) => setAv((o) => ({ ...o, m: v }))} />
            </div>
            <div>
              <Num label="Cumulative oil Np" value={av.np} onChange={(v) => setAv((o) => ({ ...o, np: v }))} />
              <Num label="Cumulative gas Gp" value={av.gp} onChange={(v) => setAv((o) => ({ ...o, gp: v }))} />
              <Num label="Cumulative water Wp" value={av.wp} onChange={(v) => setAv((o) => ({ ...o, wp: v }))} />
            </div>
          </div>
          <Lines label="PVT table. Pressure, Bo, Rs, Bg" value={av.pvt} onChange={(v) => setAv((o) => ({ ...o, pvt: v }))} rows={7} />
          <button className="primary" onClick={runAvg}>Calculate</button>
          {out.avg && (
            <>
              <p>
                {out.avg.pressure === null ? "The two sides do not cross inside the pressure range of the table."
                  : <>The average reservoir pressure is <strong>{f(out.avg.pressure, 0)} psi</strong>.</>}
              </p>
              <XY xLabel="Assumed pressure (psi)" yLabel="Underground withdrawal and expansion (bbl)"
                  series={[{ name: "Production side (F)", data: out.avg.rows.map((r) => ({ x: r.p, y: r.lhs })), line: true },
                           { name: "Expansion side, N (Eo + m Eg)", data: out.avg.rows.map((r) => ({ x: r.p, y: r.rhs })), line: true }]} />
              {out.avg.notes.map((n) => <p className="note" key={n}>{n}</p>)}
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {checks && (
        <section className="card">
          <h2>Checks against published examples</h2>
          <p className="note">
            Each table compares this tool with the printed values. A row matches when the difference is within one unit of the last printed
            digit or within 0.1 percent. Where a published example disagrees with itself, the notes say what was used.
          </p>
          {checks.map((c) => {
            const rows = c.rows.filter((r) => r.ok !== null);
            const bad = rows.filter((r) => r.ok === false).length;
            return (
              <details key={c.title} open={bad > 0} style={{ marginBottom: 14 }}>
                <summary style={{ cursor: "pointer", fontWeight: 600 }}>
                  {c.title} <span className="note">({rows.length - bad} of {rows.length} match)</span>
                </summary>
                <Table head={["Quantity", "Published", "This tool", "Difference", ""]}
                       rows={c.rows.map((r) => [r.label, r.published === null ? "" : (Math.abs(r.published) >= 1e4 ? Number(r.published).toLocaleString() : f(r.published, r.digits)),
                         r.tool === null ? "" : (Math.abs(r.tool) >= 1e4 ? Number(r.tool).toLocaleString(undefined, { maximumFractionDigits: 0 }) : f(r.tool, Math.max(r.digits, 3))),
                         r.diff === null ? "" : (r.diff >= 0 ? "+" : "") + r.diff.toPrecision(2), r.ok === null ? "" : r.ok ? "matches" : "differs"])} />
                {c.notes.map((n) => <p className="note" key={n}>{n}</p>)}
              </details>
            );
          })}
        </section>
      )}
    </div>
  );
}
