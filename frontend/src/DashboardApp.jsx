import { lazy, Suspense, useEffect, useState } from "react";
import AppShell from "./components/AppShell";
import { ErrorState, LoadingState } from "./components/DashboardUI";
import { useDashboardData } from "./hooks/useDashboardData";
import OverviewPage from "./pages/OverviewPage";
import ForecastPage from "./pages/ForecastPage";
import ModelLibraryPage from "./pages/ModelLibraryPage";
import "./dashboard.css";
import "./design-system.css";
const CompareModelsPage=lazy(()=>import("./pages/CompareModelsPage"));
const VALID=new Set(["overview","forecast","compare","library"]);
const initialPage=()=>VALID.has(location.hash.slice(1))?location.hash.slice(1):"overview";
export default function DashboardApp(){const data=useDashboardData();const [page,setPage]=useState(initialPage);useEffect(()=>{const sync=()=>{setPage(initialPage());requestAnimationFrame(()=>document.querySelector("main")?.focus())};addEventListener("hashchange",sync);return()=>removeEventListener("hashchange",sync)},[]);const content=page==="forecast"?<ForecastPage data={data}/>:page==="compare"?<Suspense fallback={<LoadingState/>}><CompareModelsPage comparison={data.comparison} loading={data.loading.comparison}/></Suspense>:page==="library"?<ModelLibraryPage registry={data.registry} comparison={data.comparison}/>:<OverviewPage data={data}/>;return <AppShell page={page} health={data.health} source={data.source} live={data.live}>{data.errors.health&&<ErrorState message="The forecasting API is unavailable. Start the backend on port 8000, then refresh." onRetry={()=>location.reload()}/>} {data.loading.initial?<LoadingState label="Loading operational data…"/>:content}</AppShell>}
