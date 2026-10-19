import React, { useEffect } from 'react';

export const TOUR_STEPS = [
  { target: 'step1', title: 'Step 1: pick a normal day', body: 'Choose the kind of day, the weather and the hour you care about. This sets the baseline we compare against.' },
  { target: 'step2', title: 'Step 2: ask "what if…?"', body: 'Drag the sliders or tap a quick scenario like Heat wave. Nothing is saved or broken, so experiment freely.' },
  { target: 'chart-card', title: 'Watch the day redraw', body: 'The blue area is your what-if, the dashed line is a normal day, and the red line is the most power we can supply.' },
  { target: 'impact-card', title: 'Read it in plain English', body: 'This card turns the chart into one sentence: how much more or less power is needed, and what that equals.' },
  { target: 'status-card', title: 'Step 3: can the grid cope?', body: 'Green is safe, amber means watch closely, red means demand could pass supply. Move the supply limit to test it.' },
  { target: 'drivers-card', title: 'Understand the reason', body: 'The bars show which factor pushes demand up (red) or down (green), so the result is never a black box.' },
  { target: 'export-btn', title: 'Take it with you', body: 'Export a one-page PDF of your scenario, the chart, the reasons and the suggested actions.' },
];

export default function Tour({ step, onStep, onClose }) {
  const s = TOUR_STEPS[step];
  useEffect(() => {
    const el = document.getElementById(s.target);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('tour-highlight');
      return () => el.classList.remove('tour-highlight');
    }
  }, [step, s.target]);
  return (
    <div className="fixed inset-x-0 bottom-4 z-50 mx-auto w-[min(92vw,30rem)] rounded-2xl bg-slate-900 p-5 text-white shadow-2xl" role="dialog" aria-label="Guided tour">
      <p className="text-xs uppercase tracking-wide text-indigo-300">Guided tour {step + 1} / {TOUR_STEPS.length}</p>
      <h3 className="mt-1 text-lg font-semibold">{s.title}</h3>
      <p className="mt-1 text-sm text-slate-300">{s.body}</p>
      <div className="mt-4 flex items-center justify-between">
        <button onClick={onClose} className="text-sm text-slate-400 hover:text-white">Skip tour</button>
        <div className="flex gap-2">
          <button disabled={step === 0} onClick={() => onStep(step - 1)} className="rounded-lg bg-slate-700 px-3 py-1.5 text-sm disabled:opacity-40">Back</button>
          {step < TOUR_STEPS.length - 1
            ? <button onClick={() => onStep(step + 1)} className="rounded-lg bg-indigo-500 px-3 py-1.5 text-sm font-semibold">Next</button>
            : <button onClick={onClose} className="rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-semibold">Done</button>}
        </div>
      </div>
    </div>
  );
}
