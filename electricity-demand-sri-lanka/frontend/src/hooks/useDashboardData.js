import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { toInputTimestamp } from "../dashboardData";

export function useDashboardData() {
  const initialized = useRef(false);
  const [data, setData] = useState({ health:null, source:null, range:null, live:null, history:[], heatmap:[], registry:null, comparison:null, metrics:null, forecast:[], forecastMeta:null });
  const [loading, setLoading] = useState({ initial:true });
  const [errors, setErrors] = useState({});
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedTimestamp, setSelectedTimestamp] = useState("");
  const [forecastSteps, setForecastSteps] = useState(24);

  const request = useCallback(async (key, fn, apply) => {
    setLoading(current => ({ ...current, [key]:true })); setErrors(current => ({ ...current, [key]:null }));
    try { const result=await fn(); apply(result); return result; }
    catch (error) { setErrors(current => ({ ...current, [key]:error.message })); return null; }
    finally { setLoading(current => ({ ...current, [key]:false })); }
  }, []);

  useEffect(() => {
    if (initialized.current) return; initialized.current=true;
    Promise.all([
      request("health",api.health,value=>setData(current=>({...current,health:value}))),
      request("source",api.dataSource,value=>setData(current=>({...current,source:value}))),
      request("range",api.dataRange,value=>{setData(current=>({...current,range:value}));setSelectedTimestamp(toInputTimestamp(value.valid_forecast_from));}),
      request("live",api.liveDemand,value=>setData(current=>({...current,live:value}))),
      request("history",()=>api.historical(48),value=>setData(current=>({...current,history:value.data??[]}))),
      request("heatmap",api.heatmap,value=>setData(current=>({...current,heatmap:value.data??[]}))),
      request("registry",api.registry,value=>{setData(current=>({...current,registry:value}));setSelectedModel(current=>current||value.default_model_id);}),
      request("comparison",api.comparison,value=>setData(current=>({...current,comparison:value}))),
    ]).finally(()=>setLoading(current=>({...current,initial:false})));
  }, [request]);

  useEffect(() => {
    if (!selectedModel) return;
    request("metrics",()=>api.metrics(selectedModel),value=>setData(current=>({...current,metrics:value})));
  }, [selectedModel,request]);

  const runForecast = useCallback(() => request("forecast",()=>api.forecast({steps:forecastSteps,startTimestamp:selectedTimestamp,includeActuals:true,model:selectedModel}),value=>setData(current=>({...current,forecast:value.forecasts??[],forecastMeta:value}))), [request,forecastSteps,selectedTimestamp,selectedModel]);

  return { ...data, loading, errors, selectedModel, setSelectedModel, selectedTimestamp, setSelectedTimestamp, forecastSteps, setForecastSteps, runForecast };
}
