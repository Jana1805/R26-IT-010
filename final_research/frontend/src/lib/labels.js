// Plain-language names, units and helpers shared by all components.

export const FEATURE_LABEL = {
  'Temperature (°C)': { name: 'Temperature', unit: '°C', plain: 'outdoor temperature' },
  'Humidity (%)': { name: 'Humidity', unit: '%', plain: 'humidity' },
  'Wind Speed (m/s)': { name: 'Wind speed', unit: 'm/s', plain: 'wind speed' },
  'Rainfall (mm)': { name: 'Rainfall', unit: 'mm', plain: 'rainfall' },
  'Solar Irradiance (W/m²)': { name: 'Sunshine', unit: 'W/m²', plain: 'sunshine' },
  'GDP (LKR)': { name: 'Economy (GDP)', unit: '', plain: 'economic activity' },
  'Per Capita Energy Use (kWh)': { name: 'Household appetite', unit: 'kWh', plain: 'energy use per person' },
  'Electricity Price (LKR/kWh)': { name: 'Electricity price', unit: 'LKR/kWh', plain: 'electricity price' },
  'Day of Week': { name: 'Day of week', unit: '', plain: 'day of the week' },
  'Hour of Day': { name: 'Time of day', unit: '', plain: 'time of day' },
  Month: { name: 'Month', unit: '', plain: 'month' },
  'Public Event': { name: 'Public event', unit: '', plain: 'a public event' },
  'Poya Day': { name: 'Poya day', unit: '', plain: 'a Poya holiday' },
};

export const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
export const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
  'September', 'October', 'November', 'December'];

export const fmtHour = (h) => {
  const hr = ((h % 24) + 24) % 24;
  const suffix = hr < 12 ? 'AM' : 'PM';
  return `${hr % 12 === 0 ? 12 : hr % 12} ${suffix}`;
};
export const fmtKw = (v, d = 0) => `${Number(v).toLocaleString('en-US', { maximumFractionDigits: d })} kW`;
export const fmtSigned = (v, d = 0) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: d })}`;

export const featureValueText = (feature, v) => {
  const l = FEATURE_LABEL[feature];
  if (!l) return String(v);
  if (feature === 'GDP (LKR)') return `${Math.round(v)}`;
  const n = Number(v);
  const digits = Math.abs(n) >= 100 ? 0 : 1;
  return `${n.toFixed(digits)}${l.unit ? ' ' + l.unit : ''}`;
};

// ---- Quick-start scenarios (shortcuts that move the sliders) --------------
export const SCENARIO_PRESETS = [
  { key: 'heat_wave', label: 'Heat wave', emoji: '🔥', blurb: 'Much hotter, a bit drier', apply: (b) => ({ ...b, temp: b.temp + 8, humidity: Math.max(30, b.humidity - 15) }) },
  { key: 'cold_spell', label: 'Cool spell', emoji: '❄️', blurb: 'Cooler and more humid', apply: (b) => ({ ...b, temp: Math.max(15, b.temp - 8), humidity: Math.min(95, b.humidity + 15) }) },
  { key: 'price_shock', label: 'Price shock', emoji: '💸', blurb: 'Tariff doubles', apply: (b) => ({ ...b, price: b.price * 2 }) },
  { key: 'economic_boom', label: 'Economic boom', emoji: '📈', blurb: 'Economy grows 20%', apply: (b) => ({ ...b, gdp: b.gdp * 1.2 }) },
];

// ---- Grid status ----------------------------------------------------------
export function gridStatus(peakKw, capacityKw) {
  const ratio = peakKw / capacityKw;
  if (ratio > 1) return { key: 'overload', label: 'Overload risk', color: '#dc2626', bg: '#fef2f2', ratio };
  if (ratio >= 0.85) return { key: 'watch', label: 'Watch closely', color: '#d97706', bg: '#fffbeb', ratio };
  return { key: 'safe', label: 'Safe', color: '#059669', bg: '#ecfdf5', ratio };
}

// ---- Plain-English headline ----------------------------------------------
export function describeChanges(base, scen) {
  const parts = [];
  const d = (a, b) => b - a;
  if (Math.abs(d(base.temp, scen.temp)) >= 0.5) parts.push(`${Math.abs(d(base.temp, scen.temp)).toFixed(1)} °C ${scen.temp > base.temp ? 'hotter' : 'cooler'} weather`);
  if (Math.abs(d(base.humidity, scen.humidity)) >= 2) parts.push(`${scen.humidity > base.humidity ? 'more' : 'less'} humid air`);
  if (Math.abs(scen.price / base.price - 1) >= 0.02) parts.push(`electricity ${Math.round(Math.abs(scen.price / base.price - 1) * 100)}% ${scen.price > base.price ? 'more expensive' : 'cheaper'}`);
  if (Math.abs(scen.gdp / base.gdp - 1) >= 0.01) parts.push(`an economy ${Math.round(Math.abs(scen.gdp / base.gdp - 1) * 100)}% ${scen.gdp > base.gdp ? 'larger' : 'smaller'}`);
  if (!parts.length) return null;
  return parts.length === 1 ? parts[0] : parts.slice(0, -1).join(', ') + ' and ' + parts[parts.length - 1];
}

export const KW_PER_HOME = 0.5; // assumption used only for the "homes" comparison

export function headline({ base, scen, hour, baseKw, scenKw }) {
  const change = describeChanges(base, scen);
  const diff = scenKw - baseKw;
  const pct = baseKw ? (diff / baseKw) * 100 : 0;
  if (!change || Math.abs(diff) < 1) {
    return { text: `On a normal day, demand at ${fmtHour(hour)} is about ${fmtKw(baseKw)}. Drag a slider or pick a quick scenario to see what changes.`, diff, pct };
  }
  const homes = Math.round(Math.abs(diff) / KW_PER_HOME);
  return {
    text: `With ${change}, demand at ${fmtHour(hour)} would be ${fmtKw(scenKw)}, which is ${fmtKw(Math.abs(diff))} (${Math.abs(pct).toFixed(1)}%) ${diff >= 0 ? 'higher' : 'lower'} than a normal day, roughly the load of ${homes.toLocaleString()} average homes.`,
    diff, pct,
  };
}

// ---- Recommendations ------------------------------------------------------
export function recommendations({ status, peakKw, capacityKw, peakHour, explain, base, scen }) {
  const recs = [];
  const gap = peakKw - capacityKw;
  const window = `${fmtHour(Math.max(0, peakHour - 1))} to ${fmtHour(peakHour + 1)}`;
  if (status.key === 'overload') {
    recs.push({ icon: '🚨', title: 'Cover the shortfall', body: `Demand would exceed supply by about ${fmtKw(gap)} at ${fmtHour(peakHour)}. Line up reserve generation or imports of at least that size.` });
    recs.push({ icon: '🏭', title: 'Ask big users to shift load', body: `Request industrial and commercial customers to move flexible work out of ${window}.` });
    recs.push({ icon: '📣', title: 'Warn the public', body: 'Issue a conservation notice before the peak: avoid heavy appliances and set air-conditioners a degree higher.' });
  } else if (status.key === 'watch') {
    recs.push({ icon: '👀', title: 'Keep reserves ready', body: `Peak is ${Math.round(status.ratio * 100)}% of supply. Keep spinning reserve available around ${window}.` });
    recs.push({ icon: '📱', title: 'Prepare a soft alert', body: 'Have a voluntary saving message ready in case the forecast rises further.' });
  } else {
    recs.push({ icon: '✅', title: 'No action needed', body: `Peak is only ${Math.round(status.ratio * 100)}% of supply, so the grid has room to spare.` });
    recs.push({ icon: '🔧', title: 'Good time for maintenance', body: 'With this much headroom, planned maintenance during off-peak hours is low risk.' });
  }
  const top = explain?.change_drivers?.[0];
  if (top && Math.abs(top.effect_kw) >= 20) {
    const l = FEATURE_LABEL[top.feature];
    const up = top.effect_kw > 0;
    if (top.feature === 'Temperature (°C)') recs.push({ icon: '🌡️', title: up ? 'Cooling is the main driver' : 'Less cooling is needed', body: up ? 'Hotter weather means more air-conditioning. Heat forecasts are the best early warning for demand spikes.' : 'Cooler weather trims air-conditioning demand, which relieves the evening peak.' });
    else if (top.feature === 'Electricity Price (LKR/kWh)') recs.push({ icon: '💰', title: up ? 'Higher prices cut demand' : 'Cheaper power raises demand', body: up ? 'Customers use less when power costs more, which can ease peaks but may hurt affordability.' : 'A lower tariff encourages use, so plan for the extra load.' });
    else if (top.feature === 'GDP (LKR)') recs.push({ icon: '🏗️', title: up ? 'Plan for growth' : 'Slower growth lowers demand', body: up ? 'A stronger economy lifts demand across all hours, so long-term capacity planning matters.' : 'A weaker economy trims demand across the day.' });
    else recs.push({ icon: 'ℹ️', title: `${l?.name || top.feature} matters most here`, body: `This is the biggest single reason demand differs from normal in this scenario.` });
  }
  return recs;
}
