import { Activity, ArrowRight, Database, Trophy } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import DemandHeatmap from "../components/DemandHeatmap";
import { ChartDescription, CsvDownload, DemandTooltip } from "../components/ChartUI";
import { LoadingState, MetricCard, Panel } from "../components/DashboardUI";
import { ACTUAL_SERIES, compactDemandTick, formatDemand, formatInteger, formatMetric, formatTimestamp, shortTime } from "../dashboardData";

export default function OverviewPage({ data }) {
  const best=[...(data.comparison?.models??[])].filter(model=>model.metrics).sort((a,b)=>a.metrics.MAE-b.metrics.MAE)[0];
  const history=(data.history??[]).map(row=>({...row,demand_kw:row.actual_kw,label:shortTime(row.timestamp)}));
  return <div className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">System overview</p><h1>Grid demand at a glance</h1><p>Observed load, temporal patterns, and production model readiness from the bundled Sri Lankan electricity dataset.</p></div></header>
    <section className="metric-grid" aria-label="System summary">
      <MetricCard label="Latest demand" value={formatDemand(data.live?.demand_kw)} detail={formatTimestamp(data.live?.timestamp)}/>
      <MetricCard label="Dataset rows" value={formatInteger(data.source?.rows??data.health?.rows)} detail="15-minute observations"/>
      <MetricCard label="Active model" value={data.registry?.models?.find(model=>model.model_id===data.selectedModel)?.display_name??"Loading"} detail="User-selectable for forecasts"/>
      <MetricCard label="Best aligned MAE" value={formatMetric("MAE",best?.metrics.MAE)} detail={best?`${best.display_name} · common test period`:"Comparison evidence unavailable"}/>
    </section>
    <div className="overview-grid">
      <Panel title="Recent observed demand" eyebrow="Last 48 hours" className="panel--chart">
        {data.loading.history?<LoadingState/>:<><ChartDescription id="history-chart-description">Observed electricity demand over the latest forty-eight hours available in the bundled historical dataset, measured in kilowatts.</ChartDescription><div className="chart-frame" role="img" aria-describedby="history-chart-description"><ResponsiveContainer><LineChart data={history} margin={{top:16,right:24,bottom:44,left:64}}><CartesianGrid vertical={false}/><XAxis dataKey="label" minTickGap={42}/><YAxis tickFormatter={compactDemandTick} label={{value:"Demand (kW)",angle:-90,position:"insideLeft",className:"axis-label"}}/><Tooltip content={<DemandTooltip/>}/><Line type="monotone" dataKey="demand_kw" name="Actual" stroke={ACTUAL_SERIES.color} strokeWidth={2.75} dot={false} connectNulls={false} isAnimationActive={false}/></LineChart></ResponsiveContainer></div><div className="chart-footer"><p className="chart-caption">Actual observations · 15-minute cadence · Sri Lanka time</p><CsvDownload rows={data.history} columns={["timestamp","actual_kw"]} filename="recent-observed-demand.csv"/></div></>}
      </Panel>
      <Panel title="Operational summary" eyebrow="Research deployment">
        <div className="summary-list"><div><Activity aria-hidden="true"/><span><strong>{data.registry?.models?.filter(model=>model.enabled).length??0} of 7 models ready</strong><small>Artifacts validated by the backend registry</small></span></div><div><Database aria-hidden="true"/><span><strong>Historical-data mode</strong><small>No claim of live utility-grid connectivity</small></span></div><div><Trophy aria-hidden="true"/><span><strong>{best?.display_name??"Comparison loading"}</strong><small>{best?"Lowest MAE on the common aligned test period":"Awaiting comparison evidence"}</small></span></div></div>
        <a className="button button--secondary button--full" href="#compare">Open model comparison <ArrowRight size={16} aria-hidden="true"/></a>
      </Panel>
    </div>
    <Panel title="Demand intensity by weekday and hour" eyebrow="Temporal profile"><DemandHeatmap data={data.heatmap} loading={data.loading.heatmap}/></Panel>
  </div>;
}
