import { Fragment, useState } from "react";
import type { MissionApi } from "../lib/useMission";
import type { Pick } from "./Scene";
import { StatusChip } from "./Chips";
import LocationMap from "./LocationMap";
import Simulator from "./Simulator";

const SAMPLE = "I want to launch an AI-powered agricultural marketplace connecting farmers in Kenya with agricultural suppliers and buyers.";

function Inspector({ api, pick }: { api: MissionApi; pick: Pick }) {
  const { world, mission } = api;
  if (!world) return null;
  let rows: [string, React.ReactNode][] = [];
  if (pick.kind === "agent") {
    const a = world.agents.find((x) => x.id === pick.id)!; const st = mission?.agents.find((x) => x.id === pick.id)?.status;
    rows = [["Agent", a.name], ["MCP server", a.mcp_server], ["Tool", `${a.tool}()`], ["Manual baseline", `${a.manual_minutes} min (assumed)`], ["Status", st ?? "locked"], ["Needs", a.needs.length ? a.needs.join(", ") : "nothing"]];
  } else if (pick.kind === "claim") {
    const c = mission?.claims.find((x) => x.id === pick.id); if (!c) return null;
    rows = [["Claim", c.claim], ["Evidence", c.text], ["Source", c.source], ["Method", c.method], ["URL", c.url], ["Your label", c.label ? <StatusChip s={c.label} /> : <span className="mini">not reviewed yet</span>],
      ["Truth", c.verdict ? <><StatusChip s={c.verdict.truth} /> {c.verdict.why}</> : <span className="mini">revealed after you review it</span>]];
  } else if (pick.kind === "competitor") {
    const c = world.competitors.find((x) => x.id === pick.id)!;
    rows = [["Name", c.name], ["Type", c.kind], ["Pricing", c.price], ["Strength", c.good], ["Weakness", c.bad], ["Overlap", `${Math.round(c.overlap * 100)}%`], ["Note", "Sample competitor, invented for the demo."]];
  } else if (pick.kind === "segment") {
    const s = world.segments.find((x) => x.id === pick.id)!;
    rows = [["Segment", s.name], ["Relative size", `${Math.round(s.size * 100)} of 100`], ["Pain", s.pain], ["Channel", s.channel], ["Status", <><StatusChip s="hypothesis" /> until you interview them</>]];
  } else {
    const claims = mission?.claims.filter((c) => c.city === pick.id) ?? [];
    rows = [["City", pick.id], ["Score now", `${mission?.recommendation?.scores[pick.id] ?? "n/a"} / 100`],
      ["Claims", claims.length ? claims.map((c) => <div key={c.id}>{c.label ? <StatusChip s={c.label} /> : <span className="chip s-unknown">unreviewed</span>} {c.claim}</div>) : "none yet"]];
  }
  return <dl className="kv">{rows.map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v}</dd></Fragment>)}</dl>;
}

export default function MissionPanel({ api, pick, shortlist, dispatchProgress, startDispatch, toggleLead }: { api: MissionApi; pick: Pick | null; shortlist: Set<string>; dispatchProgress: Record<string, number>; startDispatch: (agentId: string) => void; toggleLead: (id: string) => void }) {
  const { mission, world, running, summary } = api;
  const [idea, setIdea] = useState(SAMPLE);
  const [hoveredDispatch, setHoveredDispatch] = useState<string | null>(null);
  const done = (id: string) => mission?.agents.find((a) => a.id === id)?.status === "done";
  const rep = mission?.report;
  return (
    <>
      <p className="note">Demo build. Retrieval (Qdrant), MCP tool calls, scoring and hashing run on the backend. The LLM falls back to an offline template if no local Ollama model is reachable, and the Hedera network is simulated. All market data is invented sample data.</p>
      <div className="card">
        <h3>Founder brief</h3>
        <textarea id="idea" rows={3} aria-label="Business idea" value={mission ? mission.idea : idea} disabled={!!mission} onChange={(e) => setIdea(e.target.value)} />
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn pri" disabled={!!mission || idea.trim().length < 12 || !world} onClick={() => api.launch(idea.trim())}>Launch mission</button>
          <span className="mini">{mission ? `Mission ${mission.id} running.` : "Seven agents wait for your orders."}</span>
        </div>
      </div>
      <div className="card">
        <h3>Agent squad</h3>
        <div className="agents">
          {(mission?.agents ?? world?.agents.map((a) => ({ ...a, status: "locked" as const })) ?? []).map((a) => {
            const st = running === a.id ? "running" : a.status;
            const waits = st === "locked" && mission && !mission.approved ? ` · waits for ${a.needs.filter((n) => !done(n)).join(", ")}` : "";
            const progress = Math.round(st === "done" ? 100 : dispatchProgress[a.id] ?? 0);
            const dispatchLabel = running === a.id ? `${progress}%` : "Dispatch";
            return (
              <div key={a.id} className={`agent ${st === "ready" ? "ready" : st === "running" ? "run" : ""}`}>
                <span className="dot" style={{ background: a.color }} />
                <div style={{ minWidth: 0 }}><div className="nm">{a.name}</div><div className="mt">{a.tool} · manual {a.manual_minutes} min{waits}</div></div>
                <div className="dispatch-status" onMouseEnter={() => setHoveredDispatch(a.id)} onMouseLeave={() => setHoveredDispatch(null)}>
                  <span className={`chip ${st === "done" ? "s-verified" : "s-unknown"}`}>{{ locked: "Locked", ready: "Ready", running: "Working", done: "Done" }[st]}</span>
                  {progress > 0 && <span className="dispatch-value">{progress}%</span>}
                  {hoveredDispatch === a.id && (
                    <div className="dispatch-tooltip">{st === "done" ? `${a.name} has completed the dispatch.` : `${a.name} is validating evidence and updating the mission map.`}</div>
                  )}
                </div>
                <button className="btn sm" data-dispatch={a.id} disabled={!(st === "ready" && !running)} onClick={() => {
                  setHoveredDispatch(a.id);
                  startDispatch(a.id);
                }}>{dispatchLabel}</button>
              </div>
            );
          })}
        </div>
      </div>
      {summary && <div className="card"><h3>{summary.title}</h3><div className="stream">{summary.text}</div></div>}
      {pick && <div className="card"><h3>Inspector</h3><Inspector api={api} pick={pick} /></div>}
      {world && mission && (
        <div className="card">
          <h3>Launch map</h3>
          <LocationMap world={world} mission={mission} />
        </div>
      )}
      {done("leads") && world && (
        <div className="card"><h3>Lead shortlist (sample leads)</h3>
          {world.leads.map((l) => (
            <div className="lead" key={l.id}>
              <div style={{ minWidth: 0 }}><div>{l.name}</div><div className="mini">{l.city} · fit {l.fit}</div></div>
              <span className="chip s-hypothesis">unverified</span>
              <button className="btn sm" onClick={() => toggleLead(l.id)}>{shortlist.has(l.id) ? "Shortlisted" : "Shortlist"}</button>
            </div>
          ))}
          <p className="mini">Leads come from the agent. You choose who to contact.</p>
        </div>
      )}
      {done("growth") && <Simulator />}
      {rep && (
        <div className="card"><h3>Mission report</h3>
          <p style={{ marginBottom: 8 }}>{rep.matches_evidence ? "Your recommendation matches what the evidence supports." : `Your approved city was ${rep.approved_city}. Weighing every claim by its true status, the best-supported city was ${rep.best_supported_city} (${rep.best_score} vs ${rep.approved_score}).`}</p>
          <div className="cmp"><span>Manual baseline (assumed)</span><span /><b>{rep.manual_minutes_assumed} min</b><span>Agent compute time</span><span /><b>{rep.agent_seconds.toFixed(1)} s</b><span>Your session, incl. review</span><span /><b>{rep.session_minutes.toFixed(1)} min</b></div>
          <p className="mini" style={{ marginTop: 8 }}>Baselines are assumed task times. Measure your own real runs before you claim savings.</p>
          <p style={{ marginTop: 8 }}>Final judgment score <b>{mission?.score}</b>. Weakness review {rep.weakness_points >= 0 ? "+" : ""}{rep.weakness_points}, claims reviewed {rep.reviewed}/{rep.total_claims}{rep.full_review_bonus ? ", full review bonus +100" : ""}.</p>
          <p className="mini">Report hash {rep.report_hash.slice(0, 24)}… is on the Ledger tab.</p>
        </div>
      )}
    </>
  );
}
