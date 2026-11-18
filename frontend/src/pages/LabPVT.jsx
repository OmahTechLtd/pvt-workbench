import { useEffect, useState } from "react";
import DataTable from "../components/DataTable.jsx";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = "http://127.0.0.1:8000";
const COLOURS = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)"];

const f = (v, d = 3) => (v === null || v === undefined || Number.isNaN(v) ? "n/a" : Number(v).toFixed(d));

// Rows of numbers from the data tables. A dash marks a blank cell. The first `need` values in a row must be numbers
// (all of them when `need` is left out); rows that do not meet that are ignored.
const parse = (text, need) =>
  text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => l.split(/[\s,;]+/).map((t) => (/^(-|–|n\/a|na)$/i.test(t) ? null : Number(t))))
    .filter((r) => r.length && r.every((v) => v === null || Number.isFinite(v)) && r.slice(0, need ?? r.length).every((v) => v !== null && Number.isFinite(v)));

const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));

async function post(url, body) {
  const r = await fetch(API + url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await r.json();
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "The input could not be used.");
  return data;
}

function slopeAbove(points, psat) {
  const pts = points.filter(([p]) => p > psat * 1.02);
  if (pts.length < 2) return null;
  const n = pts.length;
  const sx = pts.reduce((a, [p]) => a + p, 0);
  const sy = pts.reduce((a, [, v]) => a + v, 0);
  const sxy = pts.reduce((a, [p, v]) => a + p * v, 0);
  const sxx = pts.reduce((a, [p]) => a + p * p, 0);
  return (n * sxy - sx * sy) / (n * sxx - sx * sx);
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

function Chart({ data, lines, xLabel, yLabel, height = 280, reverseX = false }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="p" type="number" domain={["dataMin", "dataMax"]} tick={{ fontSize: 12 }} reversed={reverseX}
                 label={{ value: xLabel, position: "insideBottom", offset: -12, fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={64} domain={["auto", "auto"]}
                 label={{ value: yLabel, angle: -90, position: "insideLeft", style: { textAnchor: "middle", fontSize: 12 } }} />
          <Tooltip formatter={(v) => (typeof v === "number" ? v.toFixed(4) : v)} />
          <Legend verticalAlign="top" height={28} />
          {lines.map((l, i) => (
            <Line key={l.key} type="monotone" dataKey={l.key} name={l.name} stroke={l.colour || COLOURS[i % COLOURS.length]}
                  strokeWidth={l.dots ? 0 : 2} dot={l.dots ? { r: 3 } : false} connectNulls isAnimationActive={false}
                  strokeDasharray={l.dash} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
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

const TABS = [
  ["cce", "Constant composition"],
  ["dl", "Differential liberation"],
  ["sep", "Separator tests"],
  ["adj", "Adjust to separator"],
  ["newpb", "New bubble point"],
  ["gas", "Gas condensate"],
];

const SOURCE = "Source: Ahmed, Reservoir Engineering Handbook, pp. 123 to 166.";

export default function LabPVT() {
  const [tab, setTab] = useState("cce");
  const [ex, setEx] = useState(null);
  const [checks, setChecks] = useState(null);
  const [error, setError] = useState(null);
  const [out, setOut] = useState({});

  // oil inputs, shared across the oil tabs
  const [t, setT] = useState({
    psat: "", rhoSat: "", tF: "", rsdb: "", bodb: "", rsfb: "", bofb: "",
    cce: "", dl: "", sep: "",
    psatNew: "", slope: "", pNew: "6500\n6000\n5000\n4000\n3000\n2000\n1911\n1808",
    rsdbNew: "", bodbNew: "", stGor: "0",
  });
  // gas condensate inputs
  const [g, setG] = useState({ gpm: "", pd: "", zd: "", cce: "", cvd: "", ldo: "", swi: "0" });
  const set = (k) => (v) => { setT((s) => ({ ...s, [k]: v })); };
  const setg = (k) => (v) => { setG((s) => ({ ...s, [k]: v })); };

  useEffect(() => {
    fetch(`${API}/lab/examples`).then((r) => r.json()).then(setEx).catch(() => {});
    fetch(`${API}/lab/verification`).then((r) => r.json()).then(setChecks).catch(() => {});
  }, []);

  const lines = (arr, keys) => arr.map((o) => keys.map((k) => o[k]).join(" ")).join("\n");

  const loadOil = (which) => {
    if (!ex) return;
    const e = ex[which];
    const first = which === "oil";
    setT((s) => ({
      ...s,
      psat: String(e.cce.psat), rhoSat: String(e.cce.rho_sat), tF: String(e.dl.t_f), rsdb: String(e.dl.rsdb), bodb: String(e.dl.bodb),
      cce: lines(e.cce.points, ["p", "vrel"]), dl: lines(e.dl.rows, ["p", "rsd", "bod", "z"]),
      sep: lines(e.separator.tests, ["pressure", "temperature", "gor_separator", "gor_stock_tank", "api", "bofb"]),
      rsfb: first ? String(e.adjust.rsfb) : "693", bofb: first ? String(e.adjust.bofb) : "1.529",
      psatNew: first ? String(e.new_pb.psat_new) : "2500", slope: first ? String(e.new_pb.slope) : "",
      rsdbNew: first ? String(e.new_pb.rsdb_new) : "", bodbNew: first ? String(e.new_pb.bodb_new) : "",
      stGor: first ? "13" : "0",
    }));
    setOut({});
    setError(null);
  };

  const loadGas = () => {
    if (!ex) return;
    const e = ex.gas;
    setG({
      gpm: e.gpm.components.map((c) => `${c.name.replace(/\s/g, "_")} ${c.y} ${c.m} ${c.gamma_oi}`).join("\n"),
      pd: String(e.cond.pd), zd: String(e.cond.zd),
      cce: lines(e.cond.cce, ["p", "vrel"]), cvd: lines(e.cond.cvd, ["p", "value"]), ldo: lines(e.cond.ldo, ["p", "value"]), swi: "0.25",
    });
    setOut({});
    setError(null);
  };

  const guard = async (fn) => {
    setError(null);
    try { await fn(); } catch (e) { setError(e.message); }
  };

  const cceBody = () => ({ psat: Number(t.psat), rho_sat: num(t.rhoSat), points: parse(t.cce).map(([p, vrel]) => ({ p, vrel })) });
  const dlRows = () => parse(t.dl, 3).map(([p, rsd, bod, z]) => ({ p, rsd, bod, z: z ?? null }));
  const dlBody = () => ({ t_f: Number(t.tF), rsdb: Number(t.rsdb), bodb: Number(t.bodb), rows: dlRows() });

  const runCce = () => guard(async () => { const r = await post("/lab/cce", cceBody()); setOut((o) => ({ ...o, cce: r })); });
  const runDl = () => guard(async () => { const r = await post("/lab/dl", dlBody()); setOut((o) => ({ ...o, dl: r })); });
  const runSep = () => guard(async () => {
    const tests = parse(t.sep, 4).map(([pressure, temperature, a, b, api, bofb]) => ({ pressure, temperature, gor_separator: a, gor_stock_tank: b, api: api ?? null, bofb: bofb ?? null }));
    const r = await post("/lab/separator", { tests });
    setOut((o) => ({ ...o, sep: r }));
  });
  const runAdj = () => guard(async () => {
    const dl = await post("/lab/dl", dlBody());
    const body = {
      pb: Number(t.psat), rsdb: Number(t.rsdb), bodb: Number(t.bodb), rsfb: Number(t.rsfb), bofb: Number(t.bofb),
      dl: dlRows(), cce: parse(t.cce).map(([p, vrel]) => ({ p, vrel })),
      btd: dl.rows.filter((r) => r.btd !== undefined).map((r) => ({ p: r.p, vrel: r.btd })),
    };
    const r = await post("/lab/adjust", body);
    setOut((o) => ({ ...o, adj: { ...r, dl: dl.rows } }));
  });
  const runNew = () => guard(async () => {
    const cce = await post("/lab/cce", cceBody());
    const pts = parse(t.cce);
    const slope = num(t.slope) ?? slopeAbove(pts, Number(t.psat));
    if (slope === null) throw new Error("Give the slope above the old saturation pressure or enough points above it.");
    const body = {
      psat_old: Number(t.psat), psat_new: Number(t.psatNew), a: cce.a, b: cce.b, slope,
      pressures: parse(t.pNew).map((r) => r[0]),
      rsfb_old: num(t.rsfb), rsdb_old: num(t.rsdb), rsdb_new: num(t.rsdbNew),
      bofb_old: num(t.bofb), bodb_old: num(t.bodb), bodb_new: num(t.bodbNew), stock_tank_gor: Number(t.stGor || 0),
    };
    const r = await post("/lab/new_pb", body);
    setOut((o) => ({ ...o, newpb: { ...r, a: cce.a, b: cce.b, slope, old: pts } }));
  });
  const estimate = () => guard(async () => {
    const rows = dlRows();
    const mk = (key, atOld) => ({ psat_old: Number(t.psat), psat_new: Number(t.psatNew), value_at_old: atOld, points: rows.map((r) => ({ p: r.p, value: r[key] })) });
    const [b, r] = await Promise.all([post("/lab/new_pb/estimate", mk("bod", Number(t.bodb))), post("/lab/new_pb/estimate", mk("rsd", Number(t.rsdb)))]);
    setT((s) => ({ ...s, bodbNew: b.value_at_new.toFixed(3), rsdbNew: r.value_at_new.toFixed(0) }));
  });
  const runGas = () => guard(async () => {
    const comps = g.gpm.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => l.split(/\s+/)).filter((p) => p.length >= 4)
      .map((p) => ({ name: p[0].replace(/_/g, " "), y: Number(p[1]), m: Number(p[2]), gamma_oi: Number(p[3]) }));
    const gpm = comps.length ? await post("/lab/gpm", { components: comps }) : null;
    const cond = await post("/lab/gas_condensate", {
      pd: Number(g.pd), zd: Number(g.zd), swi: Number(g.swi || 0),
      cce: parse(g.cce).map(([p, vrel]) => ({ p, vrel })),
      cvd: parse(g.cvd).map(([p, value]) => ({ p, value })),
      ldo: parse(g.ldo).map(([p, value]) => ({ p, value })),
    });
    setOut((o) => ({ ...o, gas: { gpm, cond } }));
  });

  const asc = (rows) => [...rows].sort((a, b) => a.p - b.p);

  return (
    <div>
      <h1>Laboratory PVT Analysis</h1>
      <p className="subtitle">
        Turn laboratory reports into the properties used in reservoir calculations. Constant composition expansion, differential
        liberation and separator tests for oil, adjustment of differential data to separator conditions, correction to a new bubble
        point, and gas condensate tests. Each calculation is checked against published worked examples at the bottom of the page.
      </p>

      <div className="segmented">
        {TABS.map(([k, label]) => (
          <button key={k} className={k === tab ? "seg active" : "seg"} onClick={() => { setTab(k); setError(null); }}>{label}</button>
        ))}
      </div>

      {tab !== "gas" && (
        <section className="card">
          <h2>Laboratory data</h2>
          <p className="note">
            Pressures are gauge (psig). Paste one row per line, values separated by spaces or commas. The same data feeds the oil tabs.
          </p>
          <p>
            <button className="seg" onClick={() => loadOil("oil")}>Load published example</button>{" "}
            <button className="seg" onClick={() => loadOil("oil_problem")}>Load practice data set (no published solution)</button>
          </p>
          <div className="panels">
            <div>
              <Num label="Saturation pressure, pb (psig)" value={t.psat} onChange={set("psat")} />
              <Num label="Density at pb (gm/cc)" value={t.rhoSat} onChange={set("rhoSat")} />
              <Num label="Temperature (°F)" value={t.tF} onChange={set("tF")} />
              <Num label="Differential Rs at pb, Rsdb (scf/STB)" value={t.rsdb} onChange={set("rsdb")} />
              <Num label="Differential Bo at pb, Bodb (bbl/STB)" value={t.bodb} onChange={set("bodb")} />
            </div>
            <div>
              <DataTable label="Constant composition" columns={[{ label: "Pressure", unit: "psig" }, { label: "Relative volume", unit: "V / Vsat" }]} value={t.cce} onChange={set("cce")} minRows={6} />
              <DataTable label="Differential liberation" columns={[{ label: "Pressure", unit: "psig" }, { label: "Rsd", unit: "scf/STB" }, { label: "Bod", unit: "bbl/STB" }, { label: "z", unit: "gas", optional: true }]} value={t.dl} onChange={set("dl")} minRows={6} />
            </div>
          </div>
        </section>
      )}

      {error && <p className="error">Something went wrong: {error}</p>}

      {tab === "cce" && (
        <section className="card">
          <h2>Constant composition expansion</h2>
          <p>Density above the bubble point, the Y-function, smoothed relative volume and compressibility above the bubble point.</p>
          <button className="primary" onClick={runCce}>Calculate</button>
          {out.cce && (
            <>
              <p className="note">Y = a + b p with a = {f(out.cce.a, 4)} and b = {f(out.cce.b, 6)}. {out.cce.fit_note}</p>
              {(() => {
                const ps = Number(t.psat);
                const rows = asc(out.cce.rows).map((r) => {
                  const below = r.p < ps;
                  const y = below ? (ps - r.p) / ((r.p + 14.7) * (r.vrel - 1)) : undefined;
                  const smooth = below ? 1 + (ps - r.p) / ((r.p + 14.7) * (out.cce.a + out.cce.b * r.p)) : undefined;
                  return { ...r, y, smooth, fit: below ? out.cce.a + out.cce.b * r.p : undefined };
                });
                out.cce.view = rows;
                return (
                  <>
                    <Chart data={rows} xLabel="Pressure (psig)" yLabel="Relative volume"
                           lines={[{ key: "vrel", name: "Measured", dots: true }, { key: "smooth", name: "Smoothed below the bubble point", dash: "5 3" }]} />
                    <Chart data={rows.filter((r) => r.y !== undefined)} xLabel="Pressure (psig)" yLabel="Y-function"
                           lines={[{ key: "y", name: "Y-function", dots: true }, { key: "fit", name: "Straight line fit", dash: "5 3" }]} />
                    <Table head={["Pressure (psig)", "Relative volume", "Density (gm/cc)", "Y-function", "Smoothed relative volume"]}
                           rows={[...rows].reverse().map((r) => [r.p, f(r.vrel, 4), r.p >= ps ? f(r.density, 4) : "", r.y === undefined ? "" : f(r.y), r.smooth === undefined ? "" : f(r.smooth, 4)])} />
                  </>
                );
              })()}
              {out.cce.compressibility.length > 0 && (
                <>
                  <h3>Average compressibility between pressures</h3>
                  <Table head={["From (psig)", "To (psig)", "co (1/psi)"]}
                         rows={out.cce.compressibility.map((c) => [c.p_high, c.p_low, (c.co * 1e6).toFixed(2) + " × 10⁻⁶"])} />
                </>
              )}
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "dl" && (
        <section className="card">
          <h2>Differential liberation</h2>
          <p>Shrinkage factor, gas formation volume factor and relative total volume at each pressure. Add z to each row to get the last two.</p>
          <button className="primary" onClick={runDl}>Calculate</button>
          {out.dl && (
            <>
              <Chart data={asc(out.dl.rows)} xLabel="Pressure (psig)" yLabel="Differential Bo (bbl/STB)" lines={[{ key: "bod", name: "Bod" }]} />
              <Table head={["Pressure (psig)", "Rsd (scf/STB)", "Bod (bbl/STB)", "Shrinkage factor", "Bg (ft³/scf)", "Btd (bbl/STB)"]}
                     rows={out.dl.rows.map((r) => [r.p, r.rsd, f(r.bod), f(r.sod, 4), r.bg === undefined ? "" : f(r.bg, 5), r.btd === undefined ? "" : f(r.btd)])} />
              <p className="note">Differential values describe the reservoir process, not the surface. They are not the Bo and Rs used in material balance until they are adjusted to separator conditions.</p>
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "sep" && (
        <section className="card">
          <h2>Separator tests</h2>
          <p>Total solution gas-oil ratio for each separator pressure and the separator pressure that gives the lowest oil formation volume factor.</p>
          <DataTable label="Separator tests, one row per test" columns={[{ label: "Separator pressure", unit: "psig" }, { label: "Temperature", unit: "°F" }, { label: "Separator GOR", unit: "scf/STB" }, { label: "Stock tank GOR", unit: "scf/STB" }, { label: "Stock tank gravity", unit: "°API", optional: true }, { label: "Bofb", unit: "bbl/STB", optional: true }]} value={t.sep} onChange={set("sep")} minRows={4} />
          <button className="primary" onClick={runSep}>Calculate</button>
          {out.sep && (
            <>
              <Table head={["Separator (psig)", "Temperature (°F)", "Total GOR, Rsfb (scf/STB)", "Stock tank °API", "Bofb (bbl/STB)"]}
                     rows={out.sep.rows.map((r) => [r.pressure, r.temperature, f(r.rsfb, 0), r.api ?? "", r.bofb ?? ""])} />
              {out.sep.optimum && (
                <p>Lowest Bofb is {out.sep.optimum.bofb} bbl/STB at a separator pressure of {out.sep.optimum.pressure} psig, which is usually taken as the optimum. At the optimum the stock tank gravity is normally highest and the total gas lowest, so check those columns too.</p>
              )}
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "adj" && (
        <section className="card">
          <h2>Adjust differential data to separator conditions</h2>
          <p>Bo and Rs for material balance, from the differential liberation, the constant composition expansion and the separator test at the chosen separator conditions.</p>
          <div className="panels">
            <Num label="Bofb from the separator test (bbl/STB)" value={t.bofb} onChange={set("bofb")} />
            <Num label="Rsfb from the separator test (scf/STB)" value={t.rsfb} onChange={set("rsfb")} />
          </div>
          <button className="primary" onClick={runAdj}>Calculate</button>
          {out.adj && (() => {
            const bo = [...out.adj.above, ...out.adj.below].map((r) => ({ p: r.p, bo: r.bo, rs: r.rs }));
            const bod = out.adj.dl.map((r) => ({ p: r.p, bod: r.bod, rsd: r.rsd }));
            const merged = asc([...bo, ...bod]);
            return (
              <>
                <Chart data={merged.filter((r) => r.p <= Number(t.psat) * 1.3)} xLabel="Pressure (psig)" yLabel="Bo (bbl/STB)"
                       lines={[{ key: "bo", name: "Adjusted Bo" }, { key: "bod", name: "Differential Bod", dash: "5 3" }]} />
                <Chart data={merged.filter((r) => r.p <= Number(t.psat) * 1.3)} xLabel="Pressure (psig)" yLabel="Rs (scf/STB)"
                       lines={[{ key: "rs", name: "Adjusted Rs" }, { key: "rsd", name: "Differential Rsd", dash: "5 3" }]} />
                <Table head={["Pressure (psig)", "Adjusted Rs (scf/STB)", "Adjusted Bo (bbl/STB)"]}
                       rows={[...out.adj.above, ...out.adj.below].map((r) => [r.p, f(r.rs, 1), f(r.bo)])} />
                {out.adj.bt_from_dl.length > 0 && (
                  <>
                    <h3>Two-phase formation volume factor below the bubble point</h3>
                    <Table head={["Pressure (psig)", "Bt from the differential relative total volume"]} rows={out.adj.bt_from_dl.map((r) => [r.p, f(r.bt)])} />
                  </>
                )}
                <p className="note">The adjustment normally gives lower Bo and Rs than the differential data. Calculated Bo reaches 1.0 and Rs reaches 0 only at atmospheric pressure, so the curves are drawn to those points by hand. This table stops at the last laboratory pressure.</p>
              </>
            );
          })()}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "newpb" && (
        <section className="card">
          <h2>Correct to a new bubble point</h2>
          <p>
            Use when field data show a bubble point that differs from the laboratory value. The relative volume curve is rebuilt for the new
            bubble point. Rs and Bo at the bubble point are scaled by the change in the differential values.
          </p>
          <div className="panels">
            <div>
              <Num label="New bubble point (psig)" value={t.psatNew} onChange={set("psatNew")} />
              <Num label="Slope of relative volume above the old bubble point" value={t.slope} onChange={set("slope")}
                   hint="Leave blank to fit a straight line to the constant composition points above the old bubble point." />
              <DataTable label="Pressures to calculate" columns={[{ label: "Pressure", unit: "psig" }]} value={t.pNew} onChange={set("pNew")} minRows={5} />
            </div>
            <div>
              <Num label="New differential Rsdb (scf/STB)" value={t.rsdbNew} onChange={set("rsdbNew")} />
              <Num label="New differential Bodb (bbl/STB)" value={t.bodbNew} onChange={set("bodbNew")} />
              <Num label="Stock tank gas-oil ratio (scf/STB)" value={t.stGor} onChange={set("stGor")} />
              <button className="seg" onClick={estimate}>Estimate the new values from the data</button>
              <p className="note">
                The estimate extends a straight line through the 30 to 90 percent pressure range to the new bubble point and carries the
                curvature over. It is a numerical version of a graphical method. It reproduced the published Rsdb closely and did not reproduce
                the published Bodb, so treat it as a first guess and check it against your own plot.
              </p>
            </div>
          </div>
          <button className="primary" onClick={runNew}>Calculate</button>
          {out.newpb && (
            <>
              <p className="note">Y-function fit a = {f(out.newpb.a, 4)}, b = {f(out.newpb.b, 6)}. Slope above the old bubble point {Number(out.newpb.slope).toExponential(3)} per psi.</p>
              <Chart data={asc([...out.newpb.rows.map((r) => ({ p: r.p, new: r.vrel })), ...out.newpb.old.map(([p, v]) => ({ p, old: v }))]).filter((r) => r.p >= Number(t.psatNew) * 0.5 && r.p <= Number(t.psatNew) * 2.6)}
                     xLabel="Pressure (psig)" yLabel="Relative volume" lines={[{ key: "old", name: "Laboratory", dots: true }, { key: "new", name: "At the new bubble point" }]} />
              <Table head={["Pressure (psig)", "Relative volume at the new bubble point", "Equation"]} rows={out.newpb.rows.map((r) => [r.p, f(r.vrel, 4), r.eq])} />
              {out.newpb.rsfb_new !== undefined && (
                <p>New separator-basis Rsfb {f(out.newpb.rsfb_new, 0)} scf/STB, separator gas-oil ratio {f(out.newpb.separator_gor_new, 0)} scf/STB
                  {out.newpb.bofb_new !== undefined && <>, Bofb {f(out.newpb.bofb_new)} bbl/STB</>}.</p>
              )}
            </>
          )}
          <p className="note">{SOURCE}</p>
        </section>
      )}

      {tab === "gas" && (
        <section className="card">
          <h2>Gas condensate</h2>
          <p>Gas plant products, z-factor from the constant composition expansion, two-phase z-factor and liquid dropout from the constant volume depletion test.</p>
          <p><button className="seg" onClick={loadGas}>Load published example</button></p>
          <div className="panels">
            <div>
              <Num label="Dew-point pressure (psig)" value={g.pd} onChange={setg("pd")} />
              <Num label="z-factor at the dew point" value={g.zd} onChange={setg("zd")} />
              <Num label="Initial water saturation (fraction)" value={g.swi} onChange={setg("swi")} />
              <DataTable label="Plant products" columns={[{ label: "Component", text: true }, { label: "Mole fraction", unit: "in the gas" }, { label: "Molecular weight", unit: "lb/lb-mol" }, { label: "Liquid specific gravity", unit: "water = 1" }]} value={g.gpm} onChange={setg("gpm")} minRows={6} />
            </div>
            <div>
              <DataTable label="Constant composition" columns={[{ label: "Pressure", unit: "psig" }, { label: "Relative volume", unit: "V / Vdew" }]} value={g.cce} onChange={setg("cce")} minRows={5} />
              <DataTable label="Depletion" columns={[{ label: "Pressure", unit: "psig" }, { label: "Cumulative gas produced", unit: "% of initial" }]} value={g.cvd} onChange={setg("cvd")} minRows={4} />
              <DataTable label="Liquid dropout" columns={[{ label: "Pressure", unit: "psig" }, { label: "Liquid dropout", unit: "% of HC pore space" }]} value={g.ldo} onChange={setg("ldo")} minRows={4} />
            </div>
          </div>
          <p className="note">Pressure in the z-factor equations is gauge plus 15.025 psi, the base pressure of the laboratory report.</p>
          <button className="primary" onClick={runGas}>Calculate</button>
          {out.gas && (
            <>
              {out.gas.gpm && (
                <>
                  <h3>Gas plant products</h3>
                  <Table head={["Component", "Mole fraction", "GPM (gal/Mscf)"]} rows={[...out.gas.gpm.rows.map((r) => [r.name, r.y, r.gpm === null ? "" : f(r.gpm)]), ["Total at 100% recovery", "", f(out.gas.gpm.total, 2)]]} />
                  <p className="note">Complete recovery is not realistic. A plant usually recovers 5 to 25 percent of the ethane, 80 to 90 percent of the propane, 95 percent or more of the butanes and all heavier components.</p>
                </>
              )}
              {out.gas.cond.cce.length > 0 && (
                <>
                  <h3>z-factor from constant composition expansion</h3>
                  <Table head={["Pressure (psig)", "Relative volume", "z-factor"]} rows={out.gas.cond.cce.map((r) => [r.p, f(r.vrel, 4), f(r.z)])} />
                </>
              )}
              {out.gas.cond.cvd.length > 0 && (
                <>
                  <h3>Two-phase z-factor during depletion</h3>
                  <Table head={["Pressure (psig)", "Cumulative produced (%)", "Two-phase z-factor"]} rows={out.gas.cond.cvd.map((r) => [r.p, f(r.gp_pct), f(r.z_two_phase)])} />
                  <p className="note">Use the two-phase z-factor, not the equilibrium gas z-factor, for a p/z versus cumulative gas plot of a gas condensate.</p>
                </>
              )}
              {out.gas.cond.ldo.length > 0 && (
                <>
                  <h3>Retrograde liquid</h3>
                  <Chart data={asc(out.gas.cond.ldo)} xLabel="Pressure (psig)" yLabel="Liquid dropout (% of pore space)" lines={[{ key: "ldo", name: "Liquid dropout", dots: true }, { key: "so", name: "Oil saturation (% of pore volume)", dash: "5 3" }]} />
                  {out.gas.cond.max_ldo && <p>Maximum liquid dropout is {f(out.gas.cond.max_ldo.ldo, 1)} percent at {out.gas.cond.max_ldo.p} psig.</p>}
                </>
              )}
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
          {checks.map((s) => {
            const rows = s.rows.filter((r) => r.ok !== null);
            const bad = rows.filter((r) => r.ok === false).length;
            return (
              <details key={s.title} open={bad > 0} style={{ marginBottom: 14 }}>
                <summary style={{ cursor: "pointer", fontWeight: 600 }}>
                  {s.title} <span className="note">({rows.length - bad} of {rows.length} match)</span>
                </summary>
                <Table head={["Quantity", "Published", "This tool", "Difference", ""]}
                       rows={s.rows.map((r) => [r.label, r.published === null ? "" : f(r.published, r.digits), r.tool === null ? "" : f(r.tool, Math.max(r.digits, 3)),
                         r.diff === null ? "" : (r.diff >= 0 ? "+" : "") + r.diff.toPrecision(2), r.ok === null ? "" : r.ok ? "matches" : "differs"])} />
                {s.notes.map((n) => <p className="note" key={n}>{n}</p>)}
              </details>
            );
          })}
        </section>
      )}
    </div>
  );
}
