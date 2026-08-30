import { DAYS } from "../utils";
import { EMPTY_VALUE } from "../dashboardData";
import { EmptyState, LoadingState } from "./DashboardUI";

const CIVIDIS = [[0,32,76],[61,76,100],[124,123,120],[190,180,78],[253,231,55]];
const cividis = (value,min,max) => {
  const t=Math.max(0,Math.min(1,(value-min)/(max-min||1)))*(CIVIDIS.length-1);
  const low=Math.floor(t), high=Math.min(CIVIDIS.length-1,low+1), mix=t-low;
  const rgb=CIVIDIS[low].map((channel,index)=>Math.round(channel+(CIVIDIS[high][index]-channel)*mix));
  return `rgb(${rgb.join(",")})`;
};
const hourLabel = hour => `${String(Number.parseInt(hour,10)).padStart(2,"0")}:00`;

export default function DemandHeatmap({data=[],loading}) {
  const values=data.flatMap(row=>DAYS.map(day=>row[day])).filter(value=>Number.isFinite(Number(value)));
  const min=values.length?Math.min(...values):0, max=values.length?Math.max(...values):0;
  const rows=Array.from({length:24},(_,hour)=>data.find(row=>Number.parseInt(row.hour,10)===hour)??{hour});
  return <div className="heatmap">
    <p className="section-copy">Average observed demand in kW. The fixed matrix shows seven weekdays by twenty-four hourly rows.</p>
    {loading?<LoadingState label="Calculating demand pattern…"/>:!data.length?<EmptyState/>:<>
      <div className="heatmap-scroll" tabIndex="0" aria-label="Scrollable 7-column by 24-row demand heatmap">
        <div className="heatmap__grid" role="grid" aria-label="Average electricity demand by weekday and hour">
          <div aria-hidden="true"/>{DAYS.map(day=><div className="heatmap__day" key={day} role="columnheader">{day}</div>)}
          {rows.map(row=><div className="heatmap__row" key={row.hour} role="row">
            <div className="heatmap__hour" role="rowheader">{hourLabel(row.hour)}</div>
            {DAYS.map(day=>{const value=row[day],missing=!Number.isFinite(Number(value));const label=missing?EMPTY_VALUE:`${Math.round(value).toLocaleString("en-US")} kW`;return <div key={day} role="gridcell" className={`heatmap__cell ${missing?"heatmap__cell--missing":""}`} style={missing?undefined:{background:cividis(value,min,max)}} title={`${day}, ${hourLabel(row.hour)}–${hourLabel(Number(row.hour)+1)}, ${label}`} aria-label={`${day}, ${hourLabel(row.hour)} to ${hourLabel(Number(row.hour)+1)}, ${missing?"demand unavailable":`${Math.round(value).toLocaleString("en-US")} kilowatts`}`}/>})}
          </div>)}
        </div>
      </div>
      <div className="heatmap__legend" aria-label={`Cividis scale from ${Math.round(min).toLocaleString()} to ${Math.round(max).toLocaleString()} kilowatts`}><span>Lower average demand</span><div className="heatmap__scale"/><span>Higher average demand</span><span>{Math.round(min).toLocaleString()}–{Math.round(max).toLocaleString()} kW</span></div>
    </>}
  </div>;
}
