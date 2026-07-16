'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { lastEvent } = useWebSocket('/ws/agents');

  const load = async () => {
    const [a, h] = await Promise.all([api.agents(), api.agentHealth()]);
    setAgents(a); setHealth(h); setLoading(false);
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { if (lastEvent?.event_type === 'agents.status_snapshot') load(); }, [lastEvent]);

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Agent Fleet</h1>
          <div className="section-sub">Live registry of all AI agents in the platform</div>
        </div>
        <div className="flex gap-2">
          {health && <>
            <span className="badge badge-idle">{health.total_agents} Total</span>
            <span className="badge badge-running">{health.running} Running</span>
            <span className="badge badge-idle">{health.idle} Idle</span>
            {health.failed > 0 && <span className="badge badge-failed">{health.failed} Failed</span>}
          </>}
        </div>
      </div>

      {loading ? (
        <div className="agent-grid">
          {[...Array(8)].map((_, i) => <div key={i} className="agent-card skeleton" style={{ height: 160 }} />)}
        </div>
      ) : (
        <div className="agent-grid">
          {agents.map(a => (
            <div key={a.name} className="agent-card glow-card">
              <div className="agent-card-header">
                <div>
                  <div className="agent-name">{a.name}</div>
                  <div className="agent-owner">Owner: {a.owner} · v{a.version}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>{a.description}</div>
                </div>
                <StatusBadge status={a.status} />
              </div>

              {/* Capabilities */}
              <div className="agent-caps">
                {(a.capabilities || []).slice(0, 4).map((c: string) => (
                  <span key={c} className="cap-tag">{c}</span>
                ))}
              </div>

              {/* Tools */}
              {(a.tools || []).length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>Tools</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {a.tools.slice(0, 4).map((t: string) => (
                      <span key={t} style={{ fontSize: 10, padding: '2px 6px', borderRadius: 8, background: 'rgba(6,182,212,0.08)', color: 'var(--cyan)', border: '1px solid rgba(6,182,212,0.15)' }}>{t}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Metrics */}
              <div className="agent-metrics">
                <div className="metric-item">
                  <div className="metric-value">{a.call_count}</div>
                  <div className="metric-label">Calls</div>
                </div>
                <div className="metric-item">
                  <div className="metric-value" style={{ color: a.success_rate >= 95 ? 'var(--green)' : 'var(--yellow)' }}>{a.success_rate}%</div>
                  <div className="metric-label">Success</div>
                </div>
                <div className="metric-item">
                  <div className="metric-value">{Math.round(a.avg_response_ms)}</div>
                  <div className="metric-label">Avg ms</div>
                </div>
              </div>

              {/* Success rate bar */}
              <div style={{ marginTop: 12 }}>
                <div className="progress-bar" style={{ height: 3 }}>
                  <div className="progress-fill" style={{
                    width: `${a.success_rate}%`,
                    background: a.success_rate >= 95 ? 'var(--green)' : a.success_rate >= 80 ? 'var(--yellow)' : 'var(--red)'
                  }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
