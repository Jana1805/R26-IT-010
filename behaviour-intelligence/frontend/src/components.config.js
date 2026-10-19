// Config for teammate components embedded via iframe in the sidebar shell.
// Edit URLs/labels/commands here only -- keep them out of the JSX.
//
// `url` is both the iframe src AND the address health-checked before the
// iframe is rendered (see TeammateComponentView.jsx).
// `startCommands` are shown in the fallback panel when that health check
// fails, so someone can bring the component up without leaving the app.

const OTHER_COMPONENTS = [
  {
    key: 'forecast',
    name: 'Demand Forecasting',
    owner: 'Dewmini',
    url: 'http://localhost:5175',
    startCommands: [
      'python start-all.py --only forecast   (from the repo root)',
      '— or manually —',
      'final_research\\venv\\Scripts\\python.exe -m uvicorn app:app --port 8002   (from final_research/backend)',
      'npm run dev   (from final_research/frontend)',
    ],
  },
  {
    key: 'xai',
    name: 'Explainable AI',
    owner: 'Madushani',
    url: 'http://localhost:5173',
    startCommands: [
      'python start-all.py --only xai   (from the repo root)',
      '— or manually —',
      'madushani_xai\\venv\\Scripts\\python.exe -m uvicorn app:app --port 8000   (from madushani_xai/backend)',
      'npm run dev   (from madushani_xai/frontend)',
    ],
  },
  {
    key: 'nn',
    name: 'Adaptive Forecasting',
    owner: 'Janahan',
    url: 'http://localhost:5176',
    startCommands: [
      'python start-all.py --only nn   (from the repo root)',
      '— or manually —',
      'electricity-demand-sri-lanka\\.venv\\Scripts\\python.exe -m uvicorn api.main:app --port 8003   (from electricity-demand-sri-lanka)',
      'npm run dev   (from electricity-demand-sri-lanka/frontend)',
    ],
  },
];

export default OTHER_COMPONENTS;
