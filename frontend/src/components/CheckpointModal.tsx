import { useEffect, useState } from "react";
import { api as client } from "../lib/api";
import type { Checkpoint } from "../lib/types";
import type { MissionApi } from "../lib/useMission";
import { StatusChip } from "./Chips";

export default function CheckpointModal({ api, onClose, onResearch, onSealed }: { api: MissionApi; onClose: () => void; onResearch: () => void; onSealed: () => void }) {
  const { mission } = api;
  const [cp, setCp] = useState<Checkpoint | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = () => api.openCheckpoint().then((c) => c && setCp(c));
  useEffect(() => { refresh(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);
  if (!mission || !cp) return <div className="modal"><div className="sheet">Loading checkpoint…</div></div>;
  const city = cp.recommendation.city;
  const act = async (action: "approve" | "challenge" | "research") => {
    setBusy(true);
    const r = await api.guard(() => client.act(mission.id, action, [...picked]));
    setBusy(false);
    if (!r) return;
    api.setMission(r.mission);
    if (action === "approve") { api.push("sys", `decision approved: ${city}`); onSealed(); }
    else if (action === "research") { api.push("in", `3 new passages indexed (${r.added?.join(", ")})`); onResearch(); }
    else { await refresh(); setMsg(`You challenged the case. ${r.dropped?.length ?? 0} hypothesis-labelled claims were set aside. ${r.city !== r.previous_city ? `The recommendation moved from ${r.previous_city} to ${r.city}.` : `The recommendation stays at ${r.previous_city}.`}`); }
  };
  return (
    <div className="modal" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label="Human checkpoint">
        <h2>Human checkpoint</h2>
        <p className="note">Nothing is sealed until you decide. The critic listed possible weaknesses. Some are real, some are not.</p>
        <div className="card"><h3>AI recommendation</h3>
          <div style={{ font: "600 18px var(--f-display)" }}>Launch in {city} first</div>
          <div className="cities" style={{ marginTop: 8 }}>{Object.entries(cp.recommendation.scores).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
            <div className="city" key={k}><span>{k}</span><div className="bar"><i style={{ width: `${v}%`, background: k === city ? "var(--violet)" : "var(--blue)" }} /></div><span>{v}</span></div>))}</div>
        </div>
        <div className="card"><h3>Supporting evidence</h3>
          <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 5 }}>
            {cp.supporting_claim_ids.length ? cp.supporting_claim_ids.map((id) => { const c = mission.claims.find((x) => x.id === id); return c && <li key={id}>{c.label ? <StatusChip s={c.label} /> : <span className="chip s-unknown">unreviewed</span>} {c.claim}</li>; }) : <li>No positive evidence for this city.</li>}
          </ul></div>
        <div className="card"><h3>Which weaknesses are real? Tick the ones you believe.</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{cp.weaknesses.map((w, i) => (
            <label className="weak" key={w}><input type="checkbox" id={`w${i}`} checked={picked.has(i)} onChange={(e) => setPicked((p) => { const n = new Set(p); e.target.checked ? n.add(i) : n.delete(i); return n; })} /><span>{w}</span></label>))}</div></div>
        {cp.unreviewed > 0 && <p className="mini" style={{ color: "var(--warn)" }}>{cp.unreviewed} claims are still unreviewed. Their sources' own confidence is counted at face value.</p>}
        <div className="row">
          <button className="btn vio" id="cpApprove" disabled={busy} onClick={() => act("approve")}>Approve</button>
          <button className="btn" id="cpChallenge" disabled={busy} onClick={() => act("challenge")}>Challenge</button>
          <button className="btn" id="cpResearch" disabled={busy || !cp.can_request_research} onClick={() => act("research")}>Request more research</button>
          <button className="btn" id="cpClose" onClick={onClose}>Back to the board</button>
        </div>
        <p className="mini" id="cpMsg">{msg}</p>
      </div>
    </div>
  );
}
