'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function AnalyticsPage() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [cost, setCost] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [d, c] = await Promise.all([api.dashboard(), api.costSummary()]);
        setDashboard(d);
        setCost(c);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="page-content" style={{ color: 'var(--text-muted)' }}>Loading analytics...</div>;

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Platform Analytics</h1>
          <div className="section-sub">Operational efficiency and resource usage insights</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* SLA Card */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: 32 }}>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>SLA SLA Compliance Rate</div>
          <div style={{ fontSize: 64, fontWeight: 800, color: 'var(--green)', lineHeight: 1 }}>{dashboard?.sla_compliance_pct ?? 100}%</div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>Target SLA compliance is 98.0%</div>
        </div>

        {/* Avg Duration Card */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: 32 }}>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Avg Workflow Duration</div>
          <div style={{ fontSize: 64, fontWeight: 800, color: 'var(--accent-1)', lineHeight: 1 }}>
            {dashboard?.avg_workflow_duration_ms ? `${(dashboard.avg_workflow_duration_ms / 1000).toFixed(1)}s` : 'N/A'}
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>Total completion time across all steps</div>
        </div>
      </div>

      {/* Cost breakdowns */}
      {cost && (
        <div className="card mb-6">
          <div className="section-header">
            <div>
              <div className="section-title">Token and Cost Distribution</div>
              <div className="section-sub">LLM API billing analytics</div>
            </div>
            <span className="badge badge-completed">Calculated Daily</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            <div className="card" style={{ background: 'var(--bg-surface)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>Input Tokens</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{cost.today_tokens_in.toLocaleString()}</div>
            </div>
            <div className="card" style={{ background: 'var(--bg-surface)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>Output Tokens</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{cost.today_tokens_out.toLocaleString()}</div>
            </div>
            <div className="card" style={{ background: 'var(--bg-surface)' }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>Cumulative Cost</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--green)' }}>${cost.today_cost_usd.toFixed(6)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
