export type Status = "verified" | "estimate" | "hypothesis";
export type AgentStatus = "locked" | "ready" | "running" | "done";
export type Mode = "command" | "competitors" | "customers" | "radar";
export type Tab = "mission" | "evidence" | "rag" | "ledger";

export interface AgentInfo {
  id: string; name: string; color: string; mcp_server: string; tool: string;
  manual_minutes: number; needs: string[]; focus: string;
}
export interface Competitor { id: string; name: string; kind: string; price: string; strength: number; overlap: number; pos: [number, number, number]; good: string; bad: string }
export interface Segment { id: string; name: string; size: number; pain: string; channel: string; pos: [number, number, number]; col: string }
export interface Lead { id: string; name: string; city: string; fit: number }
export interface World {
  agents: AgentInfo[];
  cities: Record<string, { lat: number; lon: number }>;
  competitors: Competitor[]; competitor_edges: [string, string][];
  segments: Segment[]; leads: Lead[];
}
export interface Verdict { correct: boolean; points: number; truth: Status; why: string }
export interface Claim {
  id: string; agent: string; city: string | null; claim: string; text: string; source: string; method: string;
  collection: string; url: string; source_confidence: number; label: Status | null; verdict: Verdict | null;
}
export interface Report {
  matches_evidence: boolean; approved_city: string; best_supported_city: string; approved_score: number; best_score: number;
  weakness_points: number; reviewed: number; total_claims: number; full_review_bonus: boolean;
  manual_minutes_assumed: number; agent_seconds: number; session_minutes: number; report_hash: string;
}
export interface Mission {
  id: string; idea: string; topic: string; phase: "research" | "checkpoint" | "sealed";
  agents: (AgentInfo & { status: AgentStatus })[]; claims: Claim[]; score: number; combo: number; reviewed: number;
  recommendation: { city: string; scores: Record<string, number> } | null;
  approved: boolean; ledger_length: number; report: Report | null; agent_seconds: number; manual_minutes_assumed: number; created: number;
}
export interface TraceLine { kind: "sys" | "out" | "in" | "warn"; text: string }
export interface RunResult { agent: string; summary: string; llm_backend: string; trace: TraceLine[]; claim_ids: string[]; duration_ms: number; mission: Mission }
export interface LabelResult extends Verdict { mission: Mission }
export interface Checkpoint {
  recommendation: { city: string; scores: Record<string, number> };
  supporting_claim_ids: string[]; weaknesses: string[]; unreviewed: number; can_request_research: boolean;
}
export interface ActResult { action: string; weakness_points: number; mission: Mission; dropped?: string[]; previous_city?: string; city?: string; added?: string[]; report?: Report }
export interface LedgerEntry { seq: number; ts: string; type: string; payload_hash: string; prev: string; entry_hash: string; tx: string }
export interface RagHit { id: string; score: number; title: string; text: string; url: string | null; collection: string }
export interface Health { status: string; llm: string; embedder: string; vector_store: string; passages: number; demo_mode: boolean }
export interface VerifyResult { ok: boolean; entries: { seq: number; payload_ok: boolean; link_ok: boolean }[] }
