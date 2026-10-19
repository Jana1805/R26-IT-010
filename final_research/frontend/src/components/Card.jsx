import React from 'react';

export function Card({ id, step, title, subtitle, children, className = '' }) {
  return (
    <section id={id} className={`rounded-2xl bg-white p-5 shadow-panel ring-1 ring-slate-200 sm:p-6 ${className}`}>
      {(title || step) && (
        <header className="mb-4 flex items-start gap-3">
          {step && (
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">{step}</span>
          )}
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
          </div>
        </header>
      )}
      {children}
    </section>
  );
}

export function Chip({ active, onClick, children, title }) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`rounded-full border px-3 py-1.5 text-sm transition ${
        active ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-indigo-400'
      }`}
    >
      {children}
    </button>
  );
}
