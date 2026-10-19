import { Activity, BarChart3, BookOpen, Gauge } from "lucide-react";
import { createElement } from "react";

const NAV=[
  {id:"overview",label:"Overview",icon:Gauge},
  {id:"forecast",label:"Forecast",icon:Activity},
  {id:"compare",label:"Compare Models",icon:BarChart3},
  {id:"library",label:"Model Library",icon:BookOpen},
];

export default function AppShell({ page, children }) {
  return <div className="shell">
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <div className="shell__body">
      <nav id="primary-navigation" className="sidebar" aria-label="Primary navigation">
        <div className="sidebar__label">Workspace</div>{NAV.map(item=><a key={item.id} href={`#${item.id}`} className={`nav-item ${page===item.id?"nav-item--active":""}`} aria-current={page===item.id?"page":undefined}>{createElement(item.icon,{size:18,"aria-hidden":"true"})}<span>{item.label}</span></a>)}
      </nav>
      <main id="main-content" tabIndex="-1" className="main-content">{children}</main>
    </div>
  </div>;
}
