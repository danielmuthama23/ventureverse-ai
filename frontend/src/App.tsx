import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { useMission } from "./lib/useMission";
import type { Mode, Tab } from "./lib/types";
import type { Pick } from "./components/Scene";
import MissionPanel from "./components/MissionPanel";
import EvidencePanel from "./components/EvidencePanel";
import RagPanel from "./components/RagPanel";
import LedgerPanel from "./components/LedgerPanel";
import CheckpointModal from "./components/CheckpointModal";

const Scene = lazy(() => import("./components/Scene"));
const STEPS = ["Brief", "Research", "Triage", "Checkpoint", "Sealed"];
const MODES: [Mode, string][] = [["command", "Command"], ["competitors", "Competitor Galaxy"], ["customers", "Customer Universe"], ["radar", "Opportunity Radar"]];
const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export default function App() {
  const api = useMission();
  const { mission, world, log, error, running } = api;
  const [tab, setTab] = useState<Tab>("mission");
  const [mode, setMode] = useState<Mode>("command");
  const [pick, setPick] = useState<Pick | null>(null);
  const [cpOpen, setCpOpen] = useState(false);
  const [shortlist, setShortlist] = useState<Set<string>>(new Set());
  const [dispatchProgress, setDispatchProgress] = useState<Record<string, number>>({});
  const [now, setNow] = useState(Date.now());
  const consoleRef = useRef<HTMLDivElement>(null);
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 500); return () => clearInterval(t); }, []);
  useEffect(() => { consoleRef.current?.scrollTo({ top: 1e6 }); }, [log.length]);
  useEffect(() => {
    if (!running) return;
    const agentId = running;
    const step = 10;
    const tick = window.setInterval(() => {
      setDispatchProgress((prev) => ({
        ...prev,
        [agentId]: Math.min((prev[agentId] ?? 0) + step, 100)
      }));
    }, 180);
    return () => window.clearInterval(tick);
  }, [running]);

  const done = (id: string) => mission?.agents.find((a) => a.id === id)?.status === "done";
  const sealed = !!mission?.approved;
  const step = sealed ? 4 : done("critic") ? 3 : (mission?.reviewed ?? 0) > 0 ? 2 : mission ? 1 : 0;
  // The checkpoint opens by itself the first time the critic finishes.
  const opened = useRef(false);
  useEffect(() => { if (done("critic") && !sealed && !opened.current) { opened.current = true; setCpOpen(true); } }); // eslint-disable-line react-hooks/exhaustive-deps

  const onPick = (p: Pick) => {
    const ready = mission?.agents.find((a) => a.id === p.id)?.status === "ready";
    if (p.kind === "agent" && ready && !running) {
      setDispatchProgress((prev) => ({ ...prev, [p.id]: 0 }));
      api.dispatch(p.id);
      return;
    }
    setPick(p); setTab("mission");
  };
  const empty =
    !world ? "Connecting to the API…" :
    mode === "command" && !mission ? "Write your idea in the Mission tab and press Launch mission." :
    mode === "command" && mission && !done("founder") && !running ? "Click the glowing Founder Intelligence satellite, or press Dispatch." :
    mode === "competitors" && !done("competitor") ? "Dispatch Competitor Intelligence to populate the galaxy." :
    mode === "customers" && !done("customer") ? "Dispatch Customer Discovery to reveal the segments." :
    mode === "radar" && !mission?.recommendation ? "Dispatch Growth Strategy to raise the city pillars." : "";
  const elapsed = mission ? ((sealed && mission.report ? mission.created + mission.report.session_minutes * 60 : now / 1000) - mission.created) : 0;

  return (
    <div id="app">
      <header className="hud">
        <div className="brand"><b>VENTUREVERSE</b><span>Founder Quest: validate the idea, keep the decision</span></div>
        <div className="steps">{STEPS.map((s, i) => <div key={s} className={`step ${i < step ? "done" : i === step ? "on" : ""}`}>{s}</div>)}</div>
        <div className="stats">
          <div className="stat"><small>Judgment</small><b>{mission?.score ?? 0}</b></div>
          <div className="stat"><small>Combo</small><b>x{(mission?.combo ?? 1).toFixed(2).replace(/\.?0+$/, "")}</b></div>
          <div className="stat"><small>Triaged</small><b>{mission?.reviewed ?? 0}/{mission?.claims.length ?? 0}</b></div>
          <div className="stat"><small>Elapsed</small><b>{fmt(elapsed)}</b></div>
        </div>
        {done("critic") && !sealed && <button className="btn vio sm" onClick={() => setCpOpen(true)}>Open checkpoint</button>}
      </header>

      <main className="stage">
        <section className="viewport" aria-label="3D command center">
          <div style={{ position: "absolute", inset: 0 }}>
            {world && <Suspense fallback={<div className="empty">Loading 3D engine…</div>}><Scene world={world} mission={mission} mode={mode} onPick={onPick} running={running} dispatchProgress={dispatchProgress} /></Suspense>}
          </div>
          <div className="modebar">{MODES.map(([m, label]) => <button key={m} className={mode === m ? "on" : ""} onClick={() => setMode(m)}>{label}</button>)}</div>
          {empty && <div className="empty">{empty}</div>}
          <div className="hint">Drag to rotate. Scroll to zoom. Click a satellite to dispatch an agent, an orb to inspect evidence.</div>
        </section>

        <aside className="side">
          <nav className="tabs" role="tablist">
            {(["mission", "evidence", "rag", "ledger"] as Tab[]).map((t) => (
              <button key={t} className="tab" role="tab" aria-selected={tab === t} data-p={t} onClick={() => setTab(t)}>
                {{ mission: "Mission", evidence: "Evidence", rag: "RAG lab", ledger: "Ledger" }[t]}
                {t === "evidence" && <span className="n">{(mission?.claims.length ?? 0) - (mission?.reviewed ?? 0)}</span>}
                {t === "ledger" && <span className="n">{mission?.ledger_length ?? 0}</span>}
              </button>
            ))}
          </nav>
          <div className={`pane ${tab === "mission" ? "on" : ""}`} id="pane-mission"><MissionPanel api={api} pick={pick} shortlist={shortlist} dispatchProgress={dispatchProgress} startDispatch={(agentId) => { setDispatchProgress((prev) => ({ ...prev, [agentId]: 0 })); api.dispatch(agentId); }} toggleLead={(id) => setShortlist((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; })} /></div>
          <div className={`pane ${tab === "evidence" ? "on" : ""}`} id="pane-evidence"><EvidencePanel api={api} /></div>
          <div className={`pane ${tab === "rag" ? "on" : ""}`} id="pane-rag"><RagPanel api={api} /></div>
          <div className={`pane ${tab === "ledger" ? "on" : ""}`} id="pane-ledger"><LedgerPanel api={api} /></div>
        </aside>
      </main>

      <footer className="console" ref={consoleRef} aria-live="polite">
        {log.map((l) => <div key={l.id} className={`cl ${l.kind}`}><span className="t">{l.t}</span> {l.text}</div>)}
      </footer>

      {cpOpen && mission && !sealed && (
        <CheckpointModal api={api} onClose={() => setCpOpen(false)} onResearch={() => { setCpOpen(false); setTab("evidence"); }} onSealed={() => { setCpOpen(false); setTab("mission"); }} />
      )}
      {error && <div className="toast" role="alert">{error} <button className="btn sm" onClick={() => api.setError(null)}>Dismiss</button></div>}
    </div>
  );
}
