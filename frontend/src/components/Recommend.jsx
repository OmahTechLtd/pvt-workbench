import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

const EVIDENCE = {
  strong: "Many similar oils support this.",
  moderate: "A fair number of similar oils. Treat it as a good starting point.",
  weak: "Few similar oils. Treat it as a lean, not a rule.",
};

const join = (list) => (list.length <= 1 ? list.join("") : list.slice(0, -1).join(", ") + " and " + list[list.length - 1]);

// Ranks the methods on measured oils of similar gravity and says which ones to use, with the evidence behind it.
export default function Recommend({ prop, api }) {
  const [region, setRegion] = useState("Africa");
  const [window, setWindow] = useState("5");
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [regions, setRegions] = useState([]);

  const apiNum = api === "" || api === undefined ? NaN : Number(api);
  const valid = Number.isFinite(apiNum) && apiNum > 0 && apiNum < 80;

  useEffect(() => {
    if (!valid) {
      setData(null);
      return undefined;
    }
    const t = setTimeout(() => {
      fetch(`${API}/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prop, api: apiNum, api_window: Number(window), regions: region === "all" ? null : [region] }),
      })
        .then(async (r) => {
          const d = await r.json();
          if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : "The request could not be used.");
          return d;
        })
        .then((d) => {
          setError(null);
          setData(d);
          if (d.regions) setRegions(d.regions);
        })
        .catch((e) => setError(e.message));
    }, 400);
    return () => clearTimeout(t);
  }, [prop, apiNum, valid, window, region]);

  if (prop !== "bo") {
    return (
      <section className="card">
        <h2>Which method suits oils like this one?</h2>
        <p className="muted">
          The workbench holds no measured Rs or bubble point data to rank these methods on yet. Upload your own measurements on the Test on data tab to rank them on your oils.
        </p>
      </section>
    );
  }

  const v = data && data.verdict;
  const where = region === "all" ? "all regions" : region;

  return (
    <section className="card">
      <h2>Which method suits oils like this one?</h2>

      {!valid && <p className="muted">Enter the oil gravity above to see which methods have fitted measured oils of similar gravity best.</p>}
      {error && <p className="error">{error}</p>}

      {valid && (
        <>
          <div className="btnrow" style={{ display: "flex", gap: 24, flexWrap: "wrap", marginBottom: 6 }}>
            <label className="field" style={{ marginBottom: 0 }}>
              <span>Oils from</span>
              <select value={region} onChange={(e) => setRegion(e.target.value)}>
                <option value="all">All regions</option>
                {(regions.length ? regions : [{ name: "Africa", n: 0 }]).map((r) => (
                  <option key={r.name} value={r.name}>{r.name}{r.n ? ` (${r.n})` : ""}</option>
                ))}
              </select>
            </label>
            <label className="field" style={{ marginBottom: 0 }}>
              <span>Gravity range around yours</span>
              <select value={window} onChange={(e) => setWindow(e.target.value)}>
                <option value="3">plus or minus 3 °API</option>
                <option value="5">plus or minus 5 °API</option>
                <option value="10">plus or minus 10 °API</option>
              </select>
            </label>
          </div>

          {data && data.available === false && <p className="muted">{data.reason}</p>}

          {data && data.available && !v && <p className="hint">{data.message}</p>}

          {data && v && (
            <>
              <div className="verdict">
                <div className="big">
                  Best fit <em>{join(v.leaders)}</em>
                </div>
                <div>
                  Average error {v.aae.toFixed(1)} percent on {data.n} measured oils between {data.window[0]} and {data.window[1]} °API ({where}).
                  {v.leaders.length > 1 && " These methods are within half a point of each other, so any of them is a fair choice."}
                  {v.behind.length > 0 && ` Less suited here are ${join(v.behind)}.`}
                </div>
                <div className="note" style={{ marginTop: 6 }}>
                  Evidence is {data.evidence}. {EVIDENCE[data.evidence]}
                </div>
              </div>

              <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>Method</th>
                      <th>Average error (%)</th>
                      <th>Bias (bbl/STB)</th>
                      <th>Oils</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.ranking.map((r) => (
                      <tr key={r.key}>
                        <td>{r.name}</td>
                        <td>{r.aae.toFixed(2)}</td>
                        <td>{(r.bias >= 0 ? "+" : "") + r.bias.toFixed(4)}</td>
                        <td>{r.n}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {data.notes.map((n) => (
                <p className="note" key={n}>{n}</p>
              ))}
            </>
          )}

          <p className="note">
            Based on measured oils compiled from published studies, not from your reservoir. A positive bias means the method tends to overpredict.
            Confirm the choice on your own lab data before you rely on it.
          </p>
        </>
      )}
    </section>
  );
}
