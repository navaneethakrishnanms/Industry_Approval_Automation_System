'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.auditLogs(100);
      setLogs(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Audit Logs</h1>
          <div className="section-sub">Immutable system-wide ledger of operations and decision records</div>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={load}>Refresh Ledger</button>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Actor Role</th>
              <th>Action</th>
              <th>Entity Type</th>
              <th>Entity ID</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>Loading audit trail...</td></tr>
            ) : logs.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>No audit logs recorded yet.</td></tr>
            ) : (
              logs.map(log => (
                <tr key={log.id}>
                  <td className="text-mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleString()}</td>
                  <td>
                    <span className={`badge ${log.actor_role?.includes('admin') ? 'badge-running' : log.actor_role?.includes('manager') ? 'badge-paused' : 'badge-idle'}`}>
                      {log.actor_role || 'System'}
                    </span>
                  </td>
                  <td><strong style={{ fontFamily: 'JetBrains Mono', fontSize: 13 }}>{log.action}</strong></td>
                  <td style={{ textTransform: 'capitalize' }}>{log.entity_type}</td>
                  <td><span className="text-mono" style={{ color: 'var(--accent-1)' }}>{log.entity_id ? log.entity_id.slice(0, 12) + '...' : '—'}</span></td>
                  <td>{log.description}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
