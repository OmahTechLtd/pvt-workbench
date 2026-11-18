import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

const TABS = [
  {
    key: "gravity",
    label: "Gravity",
    url: "/props/gravity",
    intro: "Oil gravity from the stock-tank density, and the solution gas gravity from separator data (Eq. 2-66 to 2-68).",
    fields: [
      ["rho_o_sc", "Stock-tank oil density (lb/ft³)"],
      ["api", "Or oil gravity (°API) to get specific gravity"],
    ],
    lists: true,
    example: { rho_o_sc: "53", sep: "724,0.743\n202,0.956\n58,1.296" },
    exampleLabel: "Use Examples 2-16 and 2-17",
  },
  {
    key: "co",
    label: "Compressibility",
    url: "/props/compressibility",
    intro: "Isothermal compressibility of undersaturated oil (Eq. 2-97 to 2-101), and below the bubble point (Eq. 2-104).",
    fields: [
      ["rsb", "Rs at the bubble point (scf/STB)"],
      ["t_f", "Temperature (°F)"],
      ["api", "Oil gravity (°API)"],
      ["gamma_g", "Gas gravity"],
      ["gamma_gs", "Gas gravity at 100 psig, optional"],
      ["psep_psia", "Separator pressure (psia), optional"],
      ["tsep_f", "Separator temperature (°F), optional"],
      ["p", "Pressure (psia)"],
      ["pb", "Bubble-point pressure (psia), optional"],
      ["rs", "Rs at p (scf/STB), only for Eq. 2-104"],
      ["bo", "Bo at p (bbl/STB), only for Eq. 2-104"],
      ["bg", "Bg at p (bbl/scf), only for Eq. 2-104"],
      ["measured", "Measured compressibility (10⁻⁶ psi⁻¹), optional"],
    ],
    example: { rsb: "751", t_f: "250", api: "47.1", gamma_g: "0.851", gamma_gs: "0.873", p: "1665", pb: "2392", rs: "515", bo: "1.393", bg: "0.001936" },
    exampleLabel: "Use Example 2-32",
  },
  {
    key: "bo",
    label: "Bo above pb",
    url: "/props/bo_under",
    intro: "Oil formation volume factor above the bubble point (Eq. 2-107 to 2-109).",
    fields: [
      ["bob", "Bo at the bubble point (bbl/STB)"],
      ["p", "Pressure (psia)"],
      ["pb", "Bubble-point pressure (psia)"],
      ["rsb", "Rs at the bubble point (scf/STB)"],
      ["t_f", "Temperature (°F)"],
      ["api", "Oil gravity (°API)"],
      ["gamma_g", "Gas gravity"],
      ["gamma_gs", "Gas gravity at 100 psig, optional"],
      ["co", "Known compressibility (10⁻⁶ psi⁻¹), optional"],
      ["measured", "Measured Bo (bbl/STB), optional"],
    ],
    example: { bob: "1.528", p: "5015", pb: "2392", rsb: "751", t_f: "250", api: "47.1", gamma_g: "0.851", gamma_gs: "0.873", measured: "1.457" },
    exampleLabel: "Use Example 2-33",
  },
  {
    key: "rho",
    label: "Density",
    url: "/props/density",
    intro: "Oil density at and above the bubble point (Eq. 2-111 to 2-115).",
    fields: [
      ["api", "Oil gravity (°API)"],
      ["rs", "Rs (scf/STB)"],
      ["gamma_g", "Gas gravity"],
      ["t_f", "Temperature (°F)"],
      ["bo", "Bo (bbl/STB), optional"],
      ["rho_ob", "Density at the bubble point (lb/ft³), for pressures above pb"],
      ["p", "Pressure (psia), above pb only"],
      ["pb", "Bubble-point pressure (psia), above pb only"],
      ["rsb", "Rs at the bubble point, above pb only"],
      ["co", "Compressibility (10⁻⁶ psi⁻¹), optional"],
      ["measured", "Measured density (lb/ft³), optional"],
    ],
    example: { api: "47.1", rs: "751", gamma_g: "0.851", t_f: "250", bo: "1.528", measured: "38.13" },
    exampleLabel: "Use oil 1 from Example 2-34",
  },
  {
    key: "bt",
    label: "Total FVF",
    url: "/props/bt",
    intro: "Total (two-phase) formation volume factor below the bubble point (Standing, Glaso, Marhoun, and the definition).",
    fields: [
      ["rs", "Rs at p (scf/STB)"],
      ["rsb", "Rs at the bubble point (scf/STB), for the definition"],
      ["t_f", "Temperature (°F)"],
      ["api", "Oil gravity (°API), or"],
      ["gamma_o", "Oil specific gravity"],
      ["gamma_g", "Gas gravity"],
      ["p", "Pressure (psia)"],
      ["bo", "Bo at p (bbl/STB), for the definition"],
      ["bg", "Bg (bbl/scf), or"],
      ["z", "Gas z-factor, to get Bg"],
      ["measured", "Measured Bt (bbl/STB), optional"],
    ],
    example: { rs: "444", rsb: "603", t_f: "140", gamma_o: "0.843", gamma_g: "0.6744", p: "2000", bo: "1.1752", z: "0.81" },
    exampleLabel: "Use Example 2-35",
  },
];

const fmt = (v) => (Math.abs(v) >= 100 ? v.toFixed(1) : Math.abs(v) >= 1 ? v.toFixed(3) : v.toFixed(4));

function Verification({ sections }) {
  return sections.map((s) => (
    <section className="card" key={s.title}>
      <h2>{s.title}</h2>
      <div style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              {s.columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {s.rows.map((r, i) => (
              <tr key={i}>
                {r.map((c, j) => (
                  <td key={j}>{c}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {s.notes.map((n) => (
        <p className="note" key={n}>
          {n}
        </p>
      ))}
    </section>
  ));
}

function OilProperties() {
  const [tab, setTab] = useState(TABS[0]);
  const [vals, setVals] = useState({});
  const [sepText, setSepText] = useState("");
  const [res, setRes] = useState(null);
  const [error, setError] = useState(null);
  const [ver, setVer] = useState(null);

  useEffect(() => {
    fetch(`${API}/props/verification`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`API returned ${r.status}`))))
      .then((d) => setVer(d.sections))
      .catch((e) => setError(e.message));
  }, []);

  function pick(t) {
    setTab(t);
    setVals({});
    setSepText("");
    setRes(null);
    setError(null);
  }

  async function run(values = vals, sep = sepText) {
    setError(null);
    const body = {};
    for (const [k] of tab.fields) {
      if (values[k] !== undefined && values[k] !== "") body[k] = Number(values[k]);
    }
    if (body.co !== undefined) body.co = Number(body.co);
    if (body.measured !== undefined && tab.key === "co") body.measured = body.measured;
    if (tab.lists && sep.trim()) {
      const lines = sep.trim().split("\n").map((l) => l.split(",").map(Number));
      body.sep_rates = lines.map((l) => l[0]);
      body.sep_gravities = lines.map((l) => l[1]);
    }
    try {
      const r = await fetch(`${API}${tab.url}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
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

  const hasErr = res && res.results.some((r) => r.error_pct !== undefined);

  return (
    <div>
      <h1>Oil Properties</h1>
      <p className="subtitle">Gravity, compressibility, formation volume factor, density and total formation volume factor, each checked against published worked examples further down the page.</p>

      <div className="segmented">
        {TABS.map((t) => (
          <button key={t.key} className={t.key === tab.key ? "seg active" : "seg"} onClick={() => pick(t)}>
            {t.label}
          </button>
        ))}
      </div>

      <section className="card">
        <h2>{tab.label}</h2>
        <p>{tab.intro}</p>
        {tab.fields.map(([k, label]) => (
          <label className="field" key={k}>
            <span>{label}</span>
            <input type="number" step="any" value={vals[k] ?? ""} onChange={(e) => { setVals({ ...vals, [k]: e.target.value }); setRes(null); }} />
          </label>
        ))}
        {tab.lists && (
          <label className="field">
            <span>Separators, one per line as gas-oil ratio (scf/STB), gas gravity. Stock tank last.</span>
            <textarea rows="4" value={sepText} onChange={(e) => { setSepText(e.target.value); setRes(null); }} />
          </label>
        )}
        <p>
          <button className="primary" onClick={() => run()}>
            Calculate
          </button>{" "}
          <button
            className="seg"
            onClick={() => {
              const { sep, ...rest } = tab.example;
              setVals(rest);
              setSepText(sep || "");
              run(rest, sep || "");
            }}
          >
            {tab.exampleLabel}
          </button>
        </p>
        {error && <p className="error">Something went wrong: {error}</p>}
      </section>

      {res && (
        <section className="card">
          <h2>Results</h2>
          <table>
            <thead>
              <tr>
                <th>Method</th>
                <th>Value</th>
                <th>Unit</th>
                {hasErr && <th>Error vs measured</th>}
              </tr>
            </thead>
            <tbody>
              {res.results.map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  <td>{r.value === null ? "n/a" : fmt(r.value)}</td>
                  <td>{r.unit}</td>
                  {hasErr && <td>{r.error_pct === undefined ? "" : `${r.error_pct >= 0 ? "+" : ""}${r.error_pct.toFixed(1)}%`}</td>}
                </tr>
              ))}
            </tbody>
          </table>
          {res.results.filter((r) => r.note).map((r) => (
            <p className="note" key={r.name + "n"}>
              {r.note}
            </p>
          ))}
          {res.notes.map((n) => (
            <p className="note" key={n}>
              {n}
            </p>
          ))}
        </section>
      )}

      {ver && (
        <>
          <h2 style={{ marginTop: 32 }}>Checks against published examples</h2>
          <p className="note">Each table compares this tool with the printed result. Where a published example disagrees with itself, the note says what was used.</p>
          <Verification sections={ver} />
        </>
      )}
    </div>
  );
}

export default OilProperties;
