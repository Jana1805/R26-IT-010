import { Activity, BarChart3, BookOpen, Database, Gauge, Menu, Radio, X } from "lucide-react";
import { createElement, useEffect, useRef, useState } from "react";
import { Status } from "./DashboardUI";
import { formatDate, formatDemand, formatTimestamp } from "../dashboardData";

const NAV=[
  {id:"overview",label:"Overview",icon:Gauge},
  {id:"forecast",label:"Forecast",icon:Activity},
  {id:"compare",label:"Compare Models",icon:BarChart3},
  {id:"library",label:"Model Library",icon:BookOpen},
];

export default function AppShell({ page, health, source, live, children }) {
  const [open,setOpen]=useState(false);
  const menuRef=useRef(null);
  const navRef=useRef(null);
  useEffect(()=>{
    if(!open)return;
    const previousOverflow=document.body.style.overflow;
    document.body.style.overflow="hidden";
    const focusable=()=>[menuRef.current,...(navRef.current?.querySelectorAll("a[href]")??[])].filter(Boolean);
    navRef.current?.querySelector("a[href]")?.focus();
    const handleKey=event=>{
      if(event.key==="Escape"){setOpen(false);requestAnimationFrame(()=>menuRef.current?.focus());return;}
      if(event.key!=="Tab")return;
      const items=focusable(), first=items[0], last=items.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    };
    document.addEventListener("keydown",handleKey);
    return()=>{document.body.style.overflow=previousOverflow;document.removeEventListener("keydown",handleKey)};
  },[open]);
  return <div className="shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <header className="topbar">
      <div className="brand"><div className="brand__mark"><Radio size={22} aria-hidden="true"/></div><div><strong>Electricity Demand Intelligence System</strong><span>Sri Lanka · 15-minute demand forecasting</span></div></div>
      <div className="topbar__status"><Status ok={Boolean(health?.model_loaded&&health?.data_loaded)}>{health?.status==="ok"?"API ready":"API unavailable"}</Status><span className="dataset-chip"><Database size={14} aria-hidden="true"/> Historical dataset</span><div className="latest"><span>Latest observed</span><strong>{formatDemand(live?.demand_kw)}</strong></div></div>
      <button ref={menuRef} className="menu-button" aria-label={open?"Close navigation":"Open navigation"} aria-expanded={open} aria-controls="primary-navigation" onClick={()=>setOpen(value=>!value)}>{open?<X aria-hidden="true"/>:<Menu aria-hidden="true"/>}</button>
    </header>
    <div className="historical-notice" role="note"><Database size={16} aria-hidden="true"/><span>Research mode — forecasts use a bundled historical dataset, not a live grid feed.</span><span className="historical-notice__time">Latest record: {formatTimestamp(source?.latest_timestamp)}</span></div>
    <div className="shell__body">
      <nav ref={navRef} id="primary-navigation" className={`sidebar ${open?"sidebar--open":""}`} aria-label="Primary navigation">
        <div className="sidebar__label">Workspace</div>{NAV.map(item=><a key={item.id} href={`#${item.id}`} className={`nav-item ${page===item.id?"nav-item--active":""}`} aria-current={page===item.id?"page":undefined} onClick={()=>setOpen(false)}>{createElement(item.icon,{size:18,"aria-hidden":"true"})}<span>{item.label}</span></a>)}
        <div className="sidebar__meta"><span>Dataset coverage</span><strong>{formatDate(health?.oldest_timestamp)}</strong><span>to {formatDate(health?.latest_timestamp)}</span></div>
      </nav>
      <main id="main-content" tabIndex="-1" className="main-content" inert={open}>{children}</main>
    </div>
    <footer className="footer" inert={open}>Final-year research demonstration · R26-IT010 · SLIIT 2026</footer>
  </div>;
}
