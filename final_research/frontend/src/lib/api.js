import axios from 'axios';

export const getReference = () => axios.get('/api/reference').then((r) => r.data);
export const getCurve = (baseline, scenario) =>
  axios.post('/api/curve', { baseline, scenario }).then((r) => r.data);
export const getExplain = (baseline, scenario, hour) =>
  axios.post('/api/explain', { baseline, scenario, hour }).then((r) => r.data);
export const getSensitivity = (inputs, hour) =>
  axios.post('/api/sensitivity', { inputs, hour }).then((r) => r.data);
