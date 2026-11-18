import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AgentMessageView, AgentRegistryEntry, BandStatus, CollaborationEvent, Mission, WorkflowView } from "../lib/types";

export default function CollaborationPanel({ mission }: { mission: Mission | null }) {
  const [status, setStatus] = useState<BandStatus | null>(null);
  const [agents, setAgents] = useState<AgentRegistryEntry[]>([]);
  const [messages, setMessages] = useState<AgentMessageView[]>([]);
  const [events, setEvents] = useState<CollaborationEvent[]>([]);
  const [workflow, setWorkflow] = useState<WorkflowView | null>(null);
  const [running, setRunning] = useState(false);
  const workflowId = mission ? `workflow-${mission.id}` : null;

  useEffect(() => {
    api.bandStatus().then(setStatus).catch(() => null);
    api.agentRegistry().then((r) => setAgents(r.agents)).catch(() => null);
  }, []);

  useEffect(() => {
    if (!workflowId) return;
    let timer = window.setInterval(() => {
      Promise.all([api.workflow(workflowId), api.workflowEvents(workflowId), api.agentMessages(workflowId)])
        .then(([w, e, m]) => { setWorkflow(w); setEvents(e.events); setMessages(m.messages); })
        .catch(() => null);
    }, 1000);
    Promise.all([api.workflow(workflowId), api.workflowEvents(workflowId), api.agentMessages(workflowId)])
      .then(([w, e, m]) => { setWorkflow(w); setEvents(e.events); setMessages(m.messages); })
      .catch(() => null);
    return () => window.clearInterval(timer);
  }, [workflowId]);

  const start = async () => {
    if (!mission || running) return;
    setRunning(true);
    try {
      await api.collaborativeWorkflow(mission.id);
      const [w, e, m] = await Promise.all([api.workflow(workflowId!), api.workflowEvents(workflowId!), api.agentMessages(workflowId!)]);
      setWorkflow(w); setEvents(e.events); setMessages(m.messages);
    } finally { setRunning(false); }
  };

  const connect = async () => setStatus(await api.bandConnect());

  return <>
    <section className="card">
      <h3>BAND Connection</h3>
      <div className="kv">
        <dt>Status</dt><dd>{status?.connected ? "Connected" : "Disconnected"}</dd>
        <dt>Provider</dt><dd>{status?.mode === "mock" ? "Mock (simulated)" : "BAND"}</dd>
        <dt>Authentication</dt><dd>{status?.authentication ?? "Checking"}</dd>
        <dt>Last sync</dt><dd>{status?.last_sync ?? "Never"}</dd>
      </div>
      {status?.error && <p className="note">{status.error}</p>}
      <button className="btn sm" onClick={connect} disabled={status?.connected && status.mode === "mock"}>Connect provider</button>
    </section>

    <section className="card">
      <h3>Agent Network</h3>
      <div className="agents">
        {agents.map((a) => <div className="agent" key={a.agent_id}><span className="dot" style={{background:a.status === "registered" ? "var(--ok)" : "var(--muted)"}}/><span className="nm">{a.name}</span><span className="mt">{a.role ?? a.description ?? "Agent"}</span><span className="dispatch-value">registered</span></div>)}
      </div>
      <div className="row" style={{marginTop:8}}>
        <button className="btn pri" onClick={start} disabled={!mission || running}>{running ? "Coordinating…" : "Run collaborative workflow"}</button>
      </div>
    </section>

    <section className="card">
      <h3>Workflow Monitor</h3>
      {workflow ? <>
        <div className="kv"><dt>Workflow</dt><dd>{workflow.workflow_id}</dd><dt>Completed</dt><dd>{workflow.completed}</dd><dt>Pending</dt><dd>{workflow.pending}</dd><dt>Failed</dt><dd>{workflow.failed}</dd></div>
        <div className="bar"><i style={{width:`${workflow.tasks.length ? workflow.completed / workflow.tasks.length * 100 : 0}%`}} /></div>
      </> : <p className="mini">No collaborative workflow started.</p>}
    </section>

    <section className="card">
      <h3>Live Message Stream</h3>
      <div className="ev">{messages.length ? messages.slice(-20).map((m) => <div className="blk" key={m.message_id}><b>{m.sender_agent} → {m.recipient_agent}</b><div>{m.message_type} · {m.status}</div><div className="meta">{m.timestamp} · {m.correlation_id}</div></div>) : <p className="mini">No agent messages yet.</p>}</div>
    </section>

    <section className="card">
      <h3>Collaboration Events & Analytics</h3>
      <div className="kv"><dt>Messages</dt><dd>{messages.length}</dd><dt>Events</dt><dd>{events.length}</dd><dt>Tasks</dt><dd>{workflow?.tasks.length ?? 0}</dd><dt>Completed</dt><dd>{workflow?.completed ?? 0}</dd></div>
      <div className="ev" style={{marginTop:8}}>{events.slice(-12).map((e) => <div className="blk" key={e.event_id}><b>{e.type}</b><div>{e.summary}</div><div className="meta">{e.timestamp}</div></div>)}</div>
    </section>
  </>
}
