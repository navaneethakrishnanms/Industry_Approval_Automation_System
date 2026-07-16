'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}><span className={`status-dot ${status}`} />{status}</span>;
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: '1', page_size: '50' };
      if (filter) params.status = filter;
      if (typeFilter) params.workflow_type = typeFilter;
      const data = await api.workflows(params);
      setWorkflows(data.items || []);
      setTotal(data.total || 0);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [filter, typeFilter]);

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Workflow Executions</h1>
          <div className="section-sub">{total} total workflows across all tenants</div>
        </div>
        <a href="/demo" className="btn btn-primary">+ Run New Workflow</a>
      </div>

      {/* Filters */}
      <div className="card mb-4">
        <div className="flex gap-3 items-center">
          <select className="select" style={{ width: 160 }} value={filter} onChange={e => setFilter(e.target.value)}>
            <option value="">All Status</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="paused">Paused</option>
            <option value="failed">Failed</option>
            <option value="escalated">Escalated</option>
          </select>
          <select className="select" style={{ width: 160 }} value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
            <option value="">All Types</option>
            <option value="travel">Travel</option>
            <option value="leave">Leave</option>
            <option value="visa">Visa</option>
            <option value="finance">Finance</option>
          </select>
          <button className="btn btn-secondary btn-sm" onClick={load}>Refresh</button>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Workflow ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Progress</th>
              <th>SLA Deadline</th>
              <th>Started</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={7} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>Loading...</td></tr>}
            {!loading && workflows.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
                No workflows found. <a href="/demo" style={{ color: 'var(--accent-1)' }}>Run a demo →</a>
              </td></tr>
            )}
            {workflows.map(w => (
              <tr key={w.id} onClick={() => window.location.href = `/workflows/${w.id}`} style={{ cursor: 'pointer' }}>
                <td><span className="text-mono" style={{ color: 'var(--accent-1)' }}>{w.id.slice(0, 12)}...</span></td>
                <td>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{w.workflow_type}</span>
                  </span>
                </td>
                <td><StatusBadge status={w.status} /></td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 120 }}>
                    <div className="progress-bar" style={{ flex: 1 }}>
                      <div className="progress-fill" style={{ width: `${w.total_steps > 0 ? (w.current_step / w.total_steps) * 100 : 0}%` }} />
                    </div>
                    <span className="text-mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{w.current_step}/{w.total_steps}</span>
                  </div>
                </td>
                <td style={{ color: w.sla_deadline && new Date(w.sla_deadline) < new Date() ? 'var(--red)' : 'var(--text-muted)', fontSize: 12 }}>
                  {w.sla_deadline ? new Date(w.sla_deadline).toLocaleString() : '—'}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{new Date(w.created_at).toLocaleString()}</td>
                <td onClick={e => e.stopPropagation()}>
                  <div className="flex gap-2">
                    {w.status === 'failed' && (
                      <button className="btn btn-secondary btn-sm" onClick={() => api.retryWorkflow(w.id).then(load)}>Retry</button>
                    )}
                    {['running', 'paused'].includes(w.status) && (
                      <button className="btn btn-danger btn-sm" onClick={() => api.cancelWorkflow(w.id).then(load)}>Cancel</button>
                    )}
                    <a href={`/workflows/${w.id}`} className="btn btn-secondary btn-sm">View →</a>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
