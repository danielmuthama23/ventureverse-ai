import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Checkpoint, Health, Mission, Status, TraceLine, World } from "./types";

export interface LogLine extends TraceLine { t: string; id: number }
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** All game state lives on the server. This hook mirrors it and replays agent traces for the console. */
export function useMission() {
  const [world, setWorld] = useState<World | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [mission, setMission] = useState<Mission | null>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [summary, setSummary] = useState<{ title: string; text: string } | null>(null);
  const [log, setLog] = useState<LogLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const seq = useRef(0);

  const push = useCallback((kind: TraceLine["kind"], text: string) => {
    const line: LogLine = { kind, text, id: ++seq.current, t: new Date().toLocaleTimeString([], { hour12: false }) };
    setLog((l) => [...l.slice(-79), line]);
  }, []);

  const guard = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    try { setError(null); return await fn(); }
    catch (e) { const msg = e instanceof Error ? e.message : String(e); setError(msg); push("warn", msg); return undefined; }
  }, [push]);

  useEffect(() => {
    Promise.all([api.world(), api.health()])
      .then(([w, h]) => { setWorld(w); setHealth(h); push("sys", `API connected. LLM: ${h.llm}. Vector store: ${h.vector_store} (${h.passages} passages).`); })
      .catch(() => setError("Cannot reach the API. Start the backend on port 8000."));
  }, [push]);

  const launch = useCallback((idea: string) => guard(async () => {
    const m = await api.createMission(idea);
    setMission(m); setStartedAt(Date.now()); setSummary(null);
    push("sys", `mission ${m.id} created. Ledger topic ${m.topic} (simulated).`);
  }), [guard, push]);

  const dispatch = useCallback((agentId: string) => guard(async () => {
    if (!mission || running) return;
    setRunning(agentId);
    try {
      const res = await api.runAgent(mission.id, agentId);
      const name = mission.agents.find((a) => a.id === agentId)?.name ?? agentId;
      setSummary({ title: `${name} · working`, text: "" });
      for (const line of res.trace) { push(line.kind, line.text); await sleep(170); }
      for (let i = 0; i <= res.summary.length; i += 5) { setSummary({ title: `${name} · working`, text: res.summary.slice(0, i) }); await sleep(14); }
      setSummary({ title: `${name} · done in ${res.duration_ms} ms (${res.llm_backend})`, text: res.summary });
      setMission(res.mission);
    } finally { setRunning(null); }
  }), [guard, mission, running, push]);

  const label = useCallback((claimId: string, status: Status) => guard(async () => {
    if (!mission) return;
    const r = await api.label(mission.id, claimId, status);
    push(r.correct ? "in" : "warn", `triage ${claimId}: you said ${status}, evidence is ${r.truth} (${r.points > 0 ? "+" : ""}${r.points})`);
    setMission(r.mission);
  }), [guard, mission, push]);

  const openCheckpoint = useCallback(async (): Promise<Checkpoint | undefined> => guard(async () => {
    if (!mission) return undefined;
    push("sys", "interrupt(): graph paused at human_checkpoint");
    return api.checkpoint(mission.id);
  }), [guard, mission, push]);

  return { world, health, mission, setMission, running, summary, log, error, setError, startedAt, push, guard, launch, dispatch, label, openCheckpoint };
}
export type MissionApi = ReturnType<typeof useMission>;
