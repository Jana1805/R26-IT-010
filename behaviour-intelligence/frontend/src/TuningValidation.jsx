import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BASE_URL = 'http://127.0.0.1:8001';
const ROW_LIMIT = 12;      // rows shown before "Show all" ...
const COLLAPSE_ABOVE = 30; // ... but only for tables longer than this

function formatCell(value, column) {
  if (value === null || value === undefined || value === '') return '—';
  if (column === 'best') return String(value).replace('<--', '✓').trim();
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return value.toLocaleString();
    return Math.abs(value) >= 1000 ? value.toLocaleString(undefined, { maximumFractionDigits: 1 }) : String(value);
  }
  return String(value);
}

function EvidenceTable({ table }) {
  const [showAll, setShowAll] = useState(false);
  if (!table.available) {
    return <p className="status-na">Table {table.name} not found.</p>;
  }
  const collapsible = table.rows.length > COLLAPSE_ABOVE;
  const rows = showAll || !collapsible ? table.rows : table.rows.slice(0, ROW_LIMIT);
  return (
    <div className="tuning-table-block">
      <p className="tuning-table-title">
        {table.title} <span className="tuning-file">{table.name}</span>
      </p>
      <div className="table-wrapper">
        <table className="data-table striped tuning-table">
          <thead>
            <tr>
              {table.columns.map((c) => (
                <th key={c} className={typeof table.rows[0]?.[c] === 'string' && c !== 'best' ? 'tuning-text-cell' : ''}>
                  {c.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={row.best ? 'tuning-row-best' : ''}>
                {table.columns.map((c) => (
                  <td key={c} className={typeof row[c] === 'string' && row[c] !== '' ? 'tuning-text-cell' : ''}>
                    {formatCell(row[c], c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {collapsible && (
        <button className="btn-quick tuning-more" onClick={() => setShowAll(!showAll)}>
          {showAll ? 'Show fewer rows' : `Show all ${table.rows.length} rows`}
        </button>
      )}
    </div>
  );
}

function Section({ section }) {
  return (
    <section className="chart-card tuning-section" id={`tuning-${section.id}`}>
      <h3 className="chart-title">{section.title}</h3>
      <div className="tuning-notes">
        <p><span className="tuning-note-label">What we tuned</span>{section.what}</p>
        {section.result && <p><span className="tuning-note-label">Result</span>{section.result}</p>}
        {section.note && <p className="tuning-honest">{section.note}</p>}
        {section.chosen && (
          <p className="tuning-chosen">
            <span className="tuning-note-label">Chosen</span>
            <span className="tuning-chosen-value">{section.chosen}</span>
          </p>
        )}
      </div>
      {section.figures.map((f) => (
        f.available ? (
          <img
            key={f.name}
            className="tuning-figure"
            src={`${BASE_URL}/api/tuning-evidence/figure/${f.name}`}
            alt={`${section.title} – ${f.name}`}
            loading="eager"
          />
        ) : <p key={f.name} className="status-na">Figure {f.name} not found.</p>
      ))}
      {section.tables.map((t) => <EvidenceTable key={t.name} table={t} />)}
    </section>
  );
}

export default function TuningValidation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get(`${BASE_URL}/api/tuning-evidence`)
      .then((res) => {
        if (res.data.success) setData(res.data.data);
        else setError(res.data.message);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.response?.data?.message || 'Failed to load tuning evidence');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading tuning evidence…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>Cannot load tuning evidence</h2>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-header-brand">
            <h1 className="app-header-title">Tuning &amp; Validation</h1>
            <p className="app-header-sub">
              How every parameter was chosen and checked · results of {data.source_notebook}
            </p>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="note-callout">
          <span className="note-callout-icon">ⓘ</span>
          <div>
            <span className="note-callout-label">Principle</span>
            {data.principle}
          </div>
        </div>

        <nav className="tuning-toc">
          {data.sections.map((s) => (
            <a key={s.id} href={`#tuning-${s.id}`} className="tuning-toc-link"
               onClick={(e) => { e.preventDefault(); document.getElementById(`tuning-${s.id}`)?.scrollIntoView({ block: 'start' }); }}>
              {s.title}
            </a>
          ))}
        </nav>

        {data.sections.map((s) => <Section key={s.id} section={s} />)}

        <div className="note-callout">
          <span className="note-callout-icon">⚠</span>
          <div>
            <span className="note-callout-label">Honest limits</span>
            <ul className="tuning-limits">
              {data.honest_limits.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>
        </div>
        <p className="section-meta">
          Highlighted rows are the chosen / best setting. Files are read from {data.tables_dir} and {data.figures_dir}.
        </p>
      </main>
    </div>
  );
}
