import type { ActResult, Checkpoint, Health, LabelResult, LedgerEntry, Mission, RagHit, RunResult, Status, VerifyResult, World } from "./types";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, { ...init, headers: { "content-type": "application/json" } });
  if (!r.ok) {
    let detail: unknown = r.statusText;
    try { detail = (await r.json()).detail ?? detail; } catch { /* body was not JSON */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return r.json() as Promise<T>;
}
const post = <T,>(path: string, body?: unknown) => http<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => http<Health>("/health"),
  world: () => http<World>("/world"),
  createMission: (idea: string) => post<Mission>("/missions", { idea }),
  runAgent: (id: string, agent: string) => post<RunResult>(`/missions/${id}/agents/${agent}/run`),
  label: (id: string, claim: string, label: Status) => post<LabelResult>(`/missions/${id}/claims/${claim}/label`, { label }),
  checkpoint: (id: string) => http<Checkpoint>(`/missions/${id}/checkpoint`),
  act: (id: string, action: "approve" | "challenge" | "research", weaknesses: number[]) => post<ActResult>(`/missions/${id}/checkpoint`, { action, weaknesses }),
  ledger: (id: string) => http<{ topic: string; entries: LedgerEntry[] }>(`/missions/${id}/ledger`),
  verify: (id: string) => post<VerifyResult>(`/missions/${id}/ledger/verify`),
  tamper: (id: string) => post<{ tampered: boolean }>(`/missions/${id}/ledger/tamper`),
  restore: (id: string) => post<{ restored: boolean }>(`/missions/${id}/ledger/restore`),
  ragSearch: (query: string, mission_id?: string) => post<{ passages: number; hits: RagHit[] }>("/rag/search", { query, k: 5, mission_id }),
  ragIngest: (mission_id: string, text: string) => post<{ passages: number }>("/rag/ingest", { mission_id, text }),
  scenario: (budget: number, cost_per_customer: number, churn: number) => post<{ series: number[]; steady_state: number }>("/scenario", { budget, cost_per_customer, churn }),
};
