import { useEffect, useState } from "react";
import { api } from "../lib/api";

/** Growth scenario. The numbers come from the scenario_simulate MCP tool on the server. */
export default function Simulator() {
  const [b, setB] = useState(1500), [c, setC] = useState(22), [r, setR] = useState(8);
  const [res, setRes] = useState<{ series: number[]; steady_state: number } | null>(null);
  useEffect(() => {
    const t = setTimeout(() => { api.scenario(b, c, r / 100).then(setRes).catch(() => setRes(null)); }, 150);
    return () => clearTimeout(t);
  }, [b, c, r]);
  const pts = res?.series ?? [], mx = Math.max(...pts, 1);
  const X = (m: number) => 10 + m * (300 / 12), Y = (v: number) => 100 - (v / mx) * 86;
  const d = pts.length ? "M" + pts.map((v, m) => `${X(m).toFixed(1)} ${Y(v).toFixed(1)}`).join(" L") : "";
  const end = pts[pts.length - 1] ?? 0;
  return (
    <div className="card">
      <h3>Growth simulator (scenario, not a forecast)</h3>
      <div className="sl"><label htmlFor="slB">Budget / month</label><input id="slB" type="range" min={200} max={5000} step={100} value={b} onChange={(e) => setB(+e.target.value)} /><span>${b}</span></div>
      <div className="sl"><label htmlFor="slC">Cost per customer</label><input id="slC" type="range" min={5} max={60} value={c} onChange={(e) => setC(+e.target.value)} /><span>${c}</span></div>
      <div className="sl"><label htmlFor="slR">Monthly churn</label><input id="slR" type="range" min={2} max={20} value={r} onChange={(e) => setR(+e.target.value)} /><span>{r}%</span></div>
      <svg viewBox="0 0 320 110" width="100%" height="110" role="img" aria-label="Projected active customers over 12 months">
        {d && <><path d={`${d} L${X(12)} 100 L10 100Z`} fill="rgba(154,107,255,.2)" /><path d={d} fill="none" stroke="#9a6bff" strokeWidth="2" />
          <circle cx={X(12)} cy={Y(end)} r="3.5" fill="#4a86ff" />
          <text x={X(12) - 6} y={Math.max(10, Y(end) - 7)} textAnchor="end" fontSize="10" fill="#e8ecfb">{Math.round(end)} customers</text></>}
        <line x1="10" y1="100" x2="310" y2="100" stroke="#1f2a4d" />
        <text x="10" y="109" fontSize="9" fill="#8e99c2">month 0</text><text x="310" y="109" textAnchor="end" fontSize="9" fill="#8e99c2">month 12</text>
      </svg>
      <p className="mini">{res ? `Steady state is about ${Math.round(res.steady_state)} customers. ` : ""}Cost per customer is a guess until you measure it.</p>
    </div>
  );
}
