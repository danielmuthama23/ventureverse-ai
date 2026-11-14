import { useCallback, useEffect, useState } from "react";
import { api as client } from "../lib/api";
import type { LedgerEntry, VerifyResult } from "../lib/types";
import type { MissionApi } from "../lib/useMission";

export default function LedgerPanel({ api }: { api: MissionApi }) {
  const id = api.mission?.id, count = api.mission?.ledger_length;
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [res, setRes] = useState<VerifyResult | null>(null);
  const [msg, setMsg] = useState("");
  const load = useCallback(() => { if (id) client.ledger(id).then((l) => setEntries(l.entries)).catch(() => undefined); }, [id]);
  useEffect(load, [load, count]);
  const bySeq = new Map(res?.entries.map((e) => [e.seq, e]));
  return (
    <>
      <p className="note">Simulated Hedera Consensus Service. Each decision is hashed with SHA-256 on the server and chained to the previous entry. Only hashes would be submitted, your documents stay private.</p>
      <div className="card"><h3>Topic</h3><div className="mini">{api.mission ? `HCS topic ${api.mission.topic} (simulated)` : "Launch a mission to open a topic."}</div>
        <div className="row" style={{ marginTop: 8 }}>
          <button className="btn sm" id="vfy" disabled={!id} onClick={() => api.guard(async () => { const r = await client.verify(id!); setRes(r); setMsg(r.ok ? `All ${r.entries.length} entries verified.` : `${r.entries.filter((e) => !(e.payload_ok && e.link_ok)).length} entries fail verification.`); })}>Verify chain</button>
          <button className="btn sm" id="tmp" disabled={!id} onClick={() => api.guard(async () => { await client.tamper(id!); setMsg("Entry #1 was edited. Press Verify chain."); })}>Simulate tampering</button>
          <button className="btn sm" id="rst" disabled={!id} onClick={() => api.guard(async () => { await client.restore(id!); setRes(null); setMsg("Entry #1 restored."); })}>Restore</button>
        </div>
        <div className="mini" style={{ marginTop: 6 }}>{msg}</div>
      </div>
      <div className="agents">{entries.length ? entries.map((e) => {
        const v = bySeq.get(e.seq), ok = v && v.payload_ok && v.link_ok;
        return <div key={e.seq} className={`blk ${v ? (ok ? "ok" : "bad") : ""}`}><b>#{e.seq} {e.type}</b> {e.ts.slice(11, 19)}<br />payload {e.payload_hash.slice(0, 28)}…<br />prev {e.prev.slice(0, 14)}… entry {e.entry_hash.slice(0, 14)}…<br />tx {e.tx}{v && <><br />{ok ? "verified" : `MISMATCH: ${v.payload_ok ? "chain link broken" : "payload no longer matches its hash"}`}</>}</div>;
      }) : <div className="mini">No entries yet.</div>}</div>
    </>
  );
}
