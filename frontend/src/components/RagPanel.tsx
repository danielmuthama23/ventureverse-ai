import { useState } from "react";
import { api as client } from "../lib/api";
import type { MissionApi } from "../lib/useMission";
import type { RagHit } from "../lib/types";

const STAGES = ["Ingest", "Extract", "Chunk", "Embed", "Qdrant", "Retrieve", "Generate", "Cite"];

export default function RagPanel({ api }: { api: MissionApi }) {
  const [q, setQ] = useState("Which city has the fewest competitors?");
  const [note, setNote] = useState("Co-op chairs in Kisumu said they pay suppliers late because buyers pay late.");
  const [hits, setHits] = useState<RagHit[]>([]);
  const [stat, setStat] = useState(`Index: ${api.health?.passages ?? "…"} passages. Press Retrieve.`);
  const [stage, setStage] = useState(-1);
  const [added, setAdded] = useState("");
  const id = api.mission?.id;

  const search = () => api.guard(async () => {
    for (let i = 0; i < STAGES.length; i++) { setStage(i); await new Promise((r) => setTimeout(r, 80)); }
    const t0 = performance.now();
    const res = await client.ragSearch(q, id);
    setHits(res.hits);
    setStat(`Searched ${res.passages} passages in Qdrant. Round trip ${(performance.now() - t0).toFixed(0)} ms (cosine over dense vectors).`);
    api.push("out", `rag.retrieve q="${q}" top_k=5`);
  });
  const ingest = () => api.guard(async () => {
    if (!id) { setAdded("Launch a mission first. Notes are private to a mission."); return; }
    const r = await client.ragIngest(id, note);
    setAdded(`Indexed. ${r.passages} passages visible to this mission. Ask about it.`);
    api.push("sys", `rag.ingest 1 document, mission index now ${r.passages}`);
  });
  return (
    <>
      <p className="note">Retrieval runs on the backend: passages are embedded and searched in Qdrant with payload filters. The default embedder is a hashing embedder so it works offline; set EMBED_MODE=ollama for a real embedding model.</p>
      <div className="pipe">{STAGES.map((s, i) => <span key={s} className={`chip ${i === stage ? "on" : ""}`}>{s}</span>)}</div>
      <div className="card"><h3>Ask the corpus</h3>
        <div className="row"><input id="ragQ" type="text" aria-label="Retrieval query" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()} style={{ flex: "1 1 200px" }} /><button className="btn pri sm" id="ragGo" onClick={search}>Retrieve</button></div>
        <div className="mini" style={{ marginTop: 6 }}>{stat}</div>
      </div>
      <div className="agents">{hits.map((h) => (
        <div className="card hit" key={h.id}><div className="row"><b className="mini" style={{ color: "var(--fg)" }}>{h.title}</b><span className="chip s-unknown">{h.collection}</span><span className="mini">score {h.score.toFixed(3)}</span></div><div>{h.text}</div></div>
      ))}</div>
      <div className="card"><h3>Ingest a founder note</h3>
        <textarea id="ragNote" rows={2} aria-label="Founder note" value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="row" style={{ marginTop: 8 }}><button className="btn sm" onClick={ingest}>Add to index</button><span className="mini">{added}</span></div>
      </div>
    </>
  );
}
