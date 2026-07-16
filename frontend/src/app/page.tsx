'use client';
import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { useWebSocket, WSEvent } from '@/lib/useWebSocket';

// ── Helpers ────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}><span className={`status-dot ${status}`} />{status}</span>;
}

function KpiCard({ label, value, sub, icon, color }: { label: string; value: any; sub?: string; icon: string; color: string }) {
  return (
    <div className="kpi-card">
      <div className="kpi-icon" style={{ background: color + '22', color }}>{icon}</div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

function EventTypeColor(type: string) {
  if (type.includes('completed') || type.includes('approved') || type.includes('success')) return 'var(--green)';
  if (type.includes('failed') || type.includes('rejected') || type.includes('error')) return 'var(--red)';
  if (type.includes('started') || type.includes('thinking') || type.includes('running')) return 'var(--blue)';
  if (type.includes('approval') || type.includes('paused')) return 'var(--yellow)';
  if (type.includes('tool')) return 'var(--cyan)';
  if (type.includes('agent')) return 'var(--purple)';
  return 'var(--text-muted)';
}

function EventFeedItem({ event }: { event: WSEvent }) {
  const color = EventTypeColor(event.event_type);
  const payload = event.payload || {};
  const msg = payload.message || payload.reasoning || payload.step_name || payload.agent || payload.error || '';
  const ts = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : '';
  return (
    <div className="event-item">
      <div className="event-type-dot" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
      <div className="event-content">
        <div className="event-type">{event.event_type}</div>
        {msg && <div className="event-message">{String(msg).slice(0, 100)}</div>}
      </div>
      <div className="event-time">{ts}</div>
    </div>
  );
}

// ── Dashboard Page ──────────────────────────────────────────────────────
export default function Dashboard() {
  const [kpis, setKpis] = useState<any>(null);
  const [agents, setAgents] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [cost, setCost] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { events, connected, lastEvent } = useWebSocket('/ws/dashboard');

  const load = useCallback(async () => {
    try {
      const [k, a, w, c] = await Promise.all([
        api.dashboard(), api.agents(), api.workflows({ page_size: '8' }), api.costSummary()
      ]);
      setKpis(k); setAgents(a); setWorkflows(w.items || []); setCost(c);
    } catch { /* backend may still be seeding */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Refresh KPIs when workflow events arrive
  useEffect(() => {
    if (lastEvent && lastEvent.event_type?.startsWith('workflow.')) {
      load();
    }
  }, [lastEvent, load]);

  if (loading) return (
    <div className="page-content">
      <div className="kpi-grid mb-6">
        {[...Array(6)].map((_, i) => <div key={i} className="kpi-card skeleton" style={{ height: 90 }} />)}
      </div>
    </div>
  );

  const runningAgents = agents.filter(a => a.status === 'running').length;

  return (
    <div className="page-content hero-gradient" style={{ minHeight: '100vh' }}>
      {/* Topbar */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Command Center</h1>
          <div className="section-sub">Real-time AI Workforce Operations Overview</div>
        </div>
        <div className="flex gap-2 items-center">
          <div className={`live-indicator`}>
            <span className="demo-dot" />
            {connected ? 'LIVE' : 'OFFLINE'}
          </div>
          <span className="badge badge-idle text-mono">SYNTHETIC MODE</span>
        </div>
      </div>

      {/* KPI Row */}
      <div className="kpi-grid mb-6">
        <KpiCard label="Today's Workflows" value={kpis?.total_workflows_today ?? 0} sub="Across all departments" icon="⟳" color="var(--accent-1)" />
        <KpiCard label="Active Now" value={kpis?.active_workflows ?? 0} sub="Running & paused" icon="◈" color="var(--blue)" />
        <KpiCard label="Completed" value={kpis?.completed_today ?? 0} sub="Today's successes" icon="✓" color="var(--green)" />
        <KpiCard label="Failed" value={kpis?.failed_today ?? 0} sub="Need attention" icon="✗" color="var(--red)" />
        <KpiCard label="SLA Compliance" value={`${kpis?.sla_compliance_pct ?? 100}%`} sub="Within deadline" icon="⊛" color="var(--cyan)" />
        <KpiCard label="Pending Approvals" value={kpis?.pending_approvals ?? 0} sub="Awaiting decision" icon="⊘" color="var(--yellow)" />
        <KpiCard label="Active Agents" value={runningAgents} sub={`of ${agents.length} registered`} icon="◉" color="var(--purple)" />
        <KpiCard label="Avg Duration" value={kpis?.avg_workflow_duration_ms ? `${(kpis.avg_workflow_duration_ms / 1000).toFixed(1)}s` : 'N/A'} sub="Workflow completion time" icon="⊞" color="var(--orange)" />
      </div>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16, marginBottom: 16 }}>
        {/* Recent Workflows */}
        <div className="card">
          <div className="section-header">
            <div>
              <div className="section-title">Recent Workflows</div>
              <div className="section-sub">Latest workflow executions across the platform</div>
            </div>
            <a href="/workflows" className="btn btn-secondary btn-sm">View All →</a>
          </div>
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {workflows.length === 0 && (
                  <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>No workflows yet — run a demo!</td></tr>
                )}
                {workflows.map(w => (
                  <tr key={w.id} style={{ cursor: 'pointer' }} onClick={() => window.location.href = `/workflows/${w.id}`}>
                    <td><span className="text-mono" style={{ color: 'var(--accent-1)' }}>{w.id.slice(0, 8)}</span></td>
                    <td><span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{w.workflow_type}</span></td>
                    <td><StatusBadge status={w.status} /></td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-bar" style={{ flex: 1 }}>
                          <div className="progress-fill" style={{ width: `${w.total_steps > 0 ? (w.current_step / w.total_steps) * 100 : 0}%` }} />
                        </div>
                        <span className="text-mono" style={{ color: 'var(--text-muted)', fontSize: 11 }}>{w.current_step}/{w.total_steps}</span>
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{new Date(w.created_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Event Feed */}
        <div className="card">
          <div className="section-header">
            <div>
              <div className="section-title">Live Event Feed</div>
              <div className="section-sub">{events.length} events captured</div>
            </div>
            <div className="live-indicator" style={{ fontSize: 10 }}>
              <span className="demo-dot" />{connected ? 'WS' : 'OFF'}
            </div>
          </div>
          <div className="event-feed">
            {events.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24, fontSize: 13 }}>
                {connected ? 'Waiting for events...' : 'Connecting to WebSocket...'}
              </div>
            )}
            {events.map((e, i) => <EventFeedItem key={i} event={e} />)}
          </div>
        </div>
      </div>

      {/* Agent Fleet Overview */}
      <div className="card mb-4">
        <div className="section-header">
          <div>
            <div className="section-title">Agent Fleet Status</div>
            <div className="section-sub">{agents.length} agents registered · {runningAgents} running</div>
          </div>
          <a href="/agents" className="btn btn-secondary btn-sm">View All →</a>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
          {agents.map(a => (
            <div key={a.name} className="card" style={{ padding: 14 }}>
              <div className="flex items-center justify-between mb-4" style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{a.name.replace('Agent', '')}</div>
                <StatusBadge status={a.status} />
              </div>
              <div className="flex gap-2" style={{ justifyContent: 'space-between' }}>
                <div className="text-mono" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>{a.call_count}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>CALLS</div>
                </div>
                <div className="text-mono" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: a.success_rate > 95 ? 'var(--green)' : 'var(--yellow)' }}>{a.success_rate}%</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>SUCCESS</div>
                </div>
                <div className="text-mono" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>{a.avg_response_ms.toFixed(0)}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>MS</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cost Summary */}
      {cost && (
        <div className="card">
          <div className="section-header">
            <div>
              <div className="section-title">LLM Cost Summary</div>
              <div className="section-sub">{cost.is_mock ? 'Mock mode — no actual API costs' : 'Real Gemini API usage'}</div>
            </div>
            <div className="badge badge-idle">{cost.is_mock ? 'MOCK' : 'LIVE'}</div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            <div className="card" style={{ textAlign: 'center', padding: 16 }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--accent-1)' }}>{cost.today_tokens_in.toLocaleString()}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Tokens In</div>
            </div>
            <div className="card" style={{ textAlign: 'center', padding: 16 }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--cyan)' }}>{cost.today_tokens_out.toLocaleString()}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Tokens Out</div>
            </div>
            <div className="card" style={{ textAlign: 'center', padding: 16 }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--green)' }}>${cost.today_cost_usd.toFixed(6)}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>Total Cost</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
