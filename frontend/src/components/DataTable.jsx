import { useEffect, useRef, useState } from "react";

// A table for typing or pasting a block of numbers. One column per quantity, units in the header.
//
// The value it holds is still plain text, one row per line and cells separated by spaces, so each page keeps its own
// parser. A blank cell between two filled ones is written as a dash. Blank cells at the end of a row are dropped.
//
// columns: [{ label: "Pressure", unit: "psia", optional: true, text: true }]

const SPLIT = /[\t,;]+|\s{2,}|\s+/;

function toRows(value, ncols) {
  const lines = String(value || "")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  return lines.map((l) => {
    const cells = l.split(SPLIT).map((c) => (/^(-|–|n\/a|na)$/i.test(c) ? "" : c));
    while (cells.length < ncols) cells.push("");
    return cells.slice(0, Math.max(ncols, cells.length));
  });
}

function toText(rows, columns) {
  return rows
    .map((r) => {
      const cells = r.map((c, i) => {
        const t = String(c ?? "").trim();
        return columns[i]?.text ? t.replace(/\s+/g, "_") : t;
      });
      while (cells.length && cells[cells.length - 1] === "") cells.pop();
      return cells.map((c) => (c === "" ? "-" : c)).join(" ");
    })
    .filter((l) => l.replace(/[-\s]/g, "") !== "")
    .join("\n");
}

const bad = (v, col) => v !== "" && !col?.text && !Number.isFinite(Number(v));

export default function DataTable({ label, columns, value, onChange, minRows = 4, hint }) {
  const ncols = columns.length;
  const last = useRef(value);
  const [rows, setRows] = useState(() => {
    const r = toRows(value, ncols);
    while (r.length < minRows) r.push(Array(ncols).fill(""));
    return r;
  });
  const refs = useRef({});

  // When the page replaces the value (an example was loaded, or the table was cleared), rebuild the rows.
  useEffect(() => {
    if (value !== last.current) {
      const r = toRows(value, ncols);
      while (r.length < minRows) r.push(Array(ncols).fill(""));
      setRows(r);
      last.current = value;
    }
  }, [value, ncols, minRows]);

  const commit = (next) => {
    setRows(next);
    const text = toText(next, columns);
    last.current = text;
    onChange(text);
  };

  const setCell = (ri, ci, v) => commit(rows.map((r, i) => (i === ri ? r.map((c, j) => (j === ci ? v : c)) : r)));

  const focusCell = (ri, ci) => {
    const el = refs.current[`${ri}-${ci}`];
    if (el) el.focus();
  };

  const addRow = () => commit([...rows, Array(ncols).fill("")]);
  const delRow = (ri) => {
    const next = rows.filter((_, i) => i !== ri);
    while (next.length < minRows) next.push(Array(ncols).fill(""));
    commit(next);
  };
  const clearAll = () => commit(Array.from({ length: minRows }, () => Array(ncols).fill("")));

  const onPaste = (e, ri, ci) => {
    const text = e.clipboardData.getData("text");
    if (!/[\n\t]/.test(text) && text.trim().split(SPLIT).length < 2) return;
    e.preventDefault();
    const block = text
      .replace(/\r/g, "")
      .split("\n")
      .filter((l) => l.trim() !== "")
      .map((l) => l.split(/\t|[,;]|\s+/).map((c) => (/^(-|–|n\/a|na)$/i.test(c.trim()) ? "" : c.trim())));
    const next = rows.map((r) => [...r]);
    block.forEach((cells, bi) => {
      const r = ri + bi;
      while (next.length <= r) next.push(Array(ncols).fill(""));
      cells.forEach((c, bj) => {
        if (ci + bj < ncols) next[r][ci + bj] = c;
      });
    });
    commit(next);
  };

  const onKey = (e, ri, ci) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (ri === rows.length - 1) addRow();
      setTimeout(() => focusCell(ri + 1, ci), 0);
    } else if (e.key === "ArrowDown") {
      focusCell(ri + 1, ci);
    } else if (e.key === "ArrowUp") {
      focusCell(ri - 1, ci);
    }
  };

  return (
    <div className="dt">
      {label && <span className="dtlabel">{label}</span>}
      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              <th className="rowno">#</th>
              {columns.map((c, i) => (
                <th key={i}>
                  {c.label}
                  {c.optional ? <small>optional</small> : null}
                  {c.unit ? <small>{c.unit}</small> : !c.optional ? <small>&nbsp;</small> : null}
                </th>
              ))}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, ri) => (
              <tr key={ri}>
                <td className="rowno">{ri + 1}</td>
                {columns.map((c, ci) => (
                  <td key={ci}>
                    <input
                      ref={(el) => (refs.current[`${ri}-${ci}`] = el)}
                      type="text"
                      inputMode={c.text ? "text" : "decimal"}
                      className={bad(r[ci], c) ? "bad" : ""}
                      value={r[ci] ?? ""}
                      aria-label={`${c.label} row ${ri + 1}`}
                      onChange={(e) => setCell(ri, ci, e.target.value)}
                      onPaste={(e) => onPaste(e, ri, ci)}
                      onKeyDown={(e) => onKey(e, ri, ci)}
                    />
                  </td>
                ))}
                <td>
                  <button className="del" type="button" title="Remove row" aria-label={`Remove row ${ri + 1}`} onClick={() => delRow(ri)}>
                    ×
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="dtbar">
        <button type="button" className="seg" onClick={addRow}>
          + Add row
        </button>
        <button type="button" className="seg" onClick={clearAll}>
          Clear
        </button>
        <small className="note">{hint || "You can paste a block straight from Excel."}</small>
      </div>
    </div>
  );
}
