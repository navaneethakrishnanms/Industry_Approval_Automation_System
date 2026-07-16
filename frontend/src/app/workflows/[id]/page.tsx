'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 90 ? 'var(--green)' : pct >= 70 ? 'var(--yellow)' : 'var(--red)';
  return (
    <div className="confidence-bar">
      <div className="confidence-track"><div className="confidence-fill" style={{ width: `${pct}%`, background: color }} /></div>
      <div className="confidence-label" style={{ color }}>{pct}%</div>
    </div>
  );
}

export default function WorkflowDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const [wf, setWf] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [conversation, setConversation] = useState<any[]>([]);
  const [tab, setTab] = useState('steps');
  const [loading, setLoading] = useState(true);
  const { events: liveEvents } = useWebSocket(`/ws/workflow/${id}`);

  const load = async () => {
    if (!id) return;
    try {
      const [w, ev, conv] = await Promise.all([
        api.workflow(id),
        api.workflowEvents(id),
        api.workflowConversation(id),
      ]);
      setWf(w); setEvents(ev); setConversation(conv.turns || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [id]);
  useEffect(() => { if (liveEvents.length > 0) load(); }, [liveEvents]);

  if (loading) return <div className="page-content" style={{ color: 'var(--text-muted)' }}>Loading workflow...</div>;
  if (!wf) return <div className="page-content" style={{ color: 'var(--red)' }}>Workflow not found.</div>;

  const pct = wf.total_steps > 0 ? (wf.current_step / wf.total_steps) * 100 : 0;

  return (
    <div className="page-content">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <a href="/workflows" style={{ color: 'var(--text-muted)', textDecoration: 'none', fontSize: 13 }}>← Workflows</a>
        <span style={{ color: 'var(--border)' }}>/</span>
        <span className="text-mono" style={{ color: 'var(--accent-1)' }}>{id.slice(0, 12)}...</span>
        <StatusBadge status={wf.status} />
        {liveEvents.length > 0 && <div className="live-indicator" style={{ fontSize: 10 }}><span className="demo-dot" />LIVE</div>}
      </div>

      {/* Progress hero */}
      <div className="card mb-6" style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.08), rgba(6,182,212,0.04))', border: '1px solid rgba(99,102,241,0.2)' }}>
        <div className="flex items-center justify-between mb-4" style={{ marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, textTransform: 'capitalize' }}>{wf.workflow_type} Workflow</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{wf.raw_request?.slice(0, 120)}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 28, fontWeight: 800 }}>{wf.current_step}<span style={{ fontSize: 16, color: 'var(--text-muted)', fontWeight: 400 }}>/{wf.total_steps}</span></div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Steps Complete</div>
          </div>
        </div>
        <div className="progress-bar" style={{ height: 8, marginBottom: 12 }}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex gap-4" style={{ gap: 24, fontSize: 12, color: 'var(--text-muted)' }}>
          <span>Started: {wf.started_at ? new Date(wf.started_at).toLocaleString() : '—'}</span>
          <span>Completed: {wf.completed_at ? new Date(wf.completed_at).toLocaleString() : 'In Progress'}</span>
          {wf.sla_deadline && <span style={{ color: new Date(wf.sla_deadline) < new Date() ? 'var(--red)' : 'var(--green)' }}>
            SLA: {new Date(wf.sla_deadline).toLocaleString()}
          </span>}
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {['steps', 'events', 'conversation'].map(t => (
          <div key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}
            style={{ textTransform: 'capitalize' }}>{t}</div>
        ))}
      </div>

      {tab === 'steps' && (
        <div className="steps-timeline">
          {(wf.steps || []).map((s: any, i: number) => (
            <div key={i} className={`step-item ${s.status}`}>
              <div className="step-num">{i + 1}</div>
              <div className="step-info">
                <div className="step-name">{s.step_name}</div>
                <div className="step-agent">→ {s.agent_name}</div>
                {s.reasoning && <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.4 }}>{s.reasoning.slice(0, 120)}</div>}
              </div>
              <div style={{ textAlign: 'right' }}>
                <StatusBadge status={s.status} />
                {s.confidence_score != null && <div style={{ marginTop: 6, minWidth: 120 }}><ConfidenceBar value={s.confidence_score} /></div>}
                {s.duration_ms && <div className="step-duration">{s.duration_ms}ms</div>}
              </div>
            </div>
          ))}
          {(wf.steps || []).length === 0 && <div style={{ color: 'var(--text-muted)', padding: 24, textAlign: 'center' }}>No steps recorded yet.</div>}
        </div>
      )}

      {tab === 'events' && (
        <div className="event-feed">
          {events.map((e: any, i) => (
            <div key={i} className="event-item">
              <div className="event-type-dot" style={{ background: e.event_type.includes('complete') ? 'var(--green)' : e.event_type.includes('fail') ? 'var(--red)' : 'var(--blue)' }} />
              <div className="event-content">
                <div className="event-type">{e.event_type}</div>
                {e.payload?.message && <div className="event-message">{e.payload.message}</div>}
                {e.payload?.reasoning && <div className="event-message">{e.payload.reasoning}</div>}
              </div>
              <div className="event-time">{e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : ''}</div>
            </div>
          ))}
          {events.length === 0 && <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32 }}>No events recorded.</div>}
        </div>
      )}

      {tab === 'conversation' && (
        <div className="chat-container">
          {conversation.map((turn: any, i) => (
            <div key={i}>
              <div className={`chat-bubble ${turn.role}`}>{turn.message}</div>
              <div className="chat-meta" style={{ textAlign: turn.role === 'employee' ? 'left' : 'right', paddingLeft: 6, paddingRight: 6 }}>
                {turn.agent} · {turn.created_at ? new Date(turn.created_at).toLocaleTimeString() : ''}
              </div>
            </div>
          ))}
          {conversation.length === 0 && <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32 }}>No conversation recorded yet.</div>}
        </div>
      )}
    </div>
  );
}
