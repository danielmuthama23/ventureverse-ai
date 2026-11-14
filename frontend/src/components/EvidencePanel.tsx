import type { MissionApi } from "../lib/useMission";
import type { Claim, Status } from "../lib/types";
import { StatusChip, cap } from "./Chips";

function ClaimCard({ c, api, sealed }: { c: Claim; api: MissionApi; sealed: boolean }) {
  return (
    <div className="card ev" data-id={c.id}>
      <div className="cl">{c.claim}</div>
      <div className="meta">{c.source} · {c.method}</div>
      <div className="meta">url: {c.url} · by {api.world?.agents.find((a) => a.id === c.agent)?.name}</div>
      <div><div className="mini">Confidence projected by the source: {Math.round(c.source_confidence * 100)}%</div><div className="bar"><i style={{ width: `${Math.round(c.source_confidence * 100)}%` }} /></div></div>
      {!c.label ? (
        <div className="tri">{(["verified", "estimate", "hypothesis"] as Status[]).map((k) => <button key={k} className="btn sm" data-lab={k} disabled={sealed} onClick={() => api.label(c.id, k)}>{cap(k)}</button>)}</div>
      ) : c.verdict && (
        <div className={`verdict ${c.verdict.correct ? "good" : "bad"}`}>
          {c.verdict.correct ? `Correct (+${c.verdict.points}). ` : `Not quite (${c.verdict.points}). You said ${c.label}. `}This is <StatusChip s={c.verdict.truth} /> {c.verdict.why}
        </div>
      )}
    </div>
  );
}

export default function EvidencePanel({ api }: { api: MissionApi }) {
  const claims = [...(api.mission?.claims ?? [])].reverse();
  const queue = claims.filter((c) => !c.label), reviewed = claims.filter((c) => c.label), sealed = !!api.mission?.approved;
  return (
    <>
      <p className="note">Every claim an agent returns arrives unlabelled. Decide whether it is verified, an estimate or a hypothesis. The server reveals the truth only after you commit, and your labels change the recommendation.</p>
      <div className="agents" id="queue">{queue.length ? queue.map((c) => <ClaimCard key={c.id} c={c} api={api} sealed={sealed} />) : <div className="mini">{claims.length ? "Every claim is reviewed." : "No claims yet. Dispatch an agent and its findings arrive here."}</div>}</div>
      <h3 className="mini" style={{ textTransform: "uppercase", letterSpacing: ".08em" }}>Reviewed</h3>
      <div className="agents" id="reviewed">{reviewed.length ? reviewed.map((c) => <ClaimCard key={c.id} c={c} api={api} sealed={sealed} />) : <div className="mini">Nothing reviewed yet.</div>}</div>
    </>
  );
}
