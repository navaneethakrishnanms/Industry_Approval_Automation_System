'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: string } | null>(null);
  const { lastEvent } = useWebSocket('/ws/dashboard');

  const load = async () => { const data = await api.allApprovals(); setApprovals(data); setLoading(false); };
  useEffect(() => { load(); }, []);
  useEffect(() => { if (lastEvent?.event_type?.includes('approval')) load(); }, [lastEvent]);

  const showToast = (msg: string, type: string) => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const handleApprove = async (id: string) => {
    setProcessing(id);
    try {
      await api.approve(id, { approver_name: 'Manager (Demo)', reason: 'Approved via dashboard' });
      showToast('Workflow approved. Resuming execution...', 'success');
      load();
    } catch (e: any) { showToast(e.message, 'error'); }
    finally { setProcessing(null); }
  };

  const handleReject = async (id: string) => {
    setProcessing(id);
    try {
      await api.reject(id, { approver_name: 'Manager (Demo)', reason: 'Rejected via dashboard' });
      showToast('Request rejected.', 'error');
      load();
    } catch (e: any) { showToast(e.message, 'error'); }
    finally { setProcessing(null); }
  };

  const pending = approvals.filter(a => a.status === 'pending');
  const decided = approvals.filter(a => a.status !== 'pending');

  return (
    <div className="page-content">
      {toast && (
        <div className="toast-container">
          <div className={`toast toast-${toast.type}`}>{toast.msg}</div>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Approval Center</h1>
          <div className="section-sub">{pending.length} pending · {decided.length} decided</div>
        </div>
        <div className="flex gap-2">
          {pending.length > 0 && <span className="badge badge-pending" style={{ padding: '6px 12px', fontSize: 13 }}>{pending.length} Awaiting Action</span>}
        </div>
      </div>

      {/* Pending Approvals */}
      {pending.length > 0 && (
        <div className="mb-6">
          <div className="section-title mb-4" style={{ marginBottom: 12 }}>Pending Approvals</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {pending.map(a => (
              <div key={a.id} className="card" style={{ border: '1px solid rgba(245,158,11,0.25)', background: 'rgba(245,158,11,0.03)' }}>
                <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700 }}>Level {a.level} Approval — <span style={{ textTransform: 'capitalize' }}>{a.requested_from_role}</span></div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Workflow: <span className="text-mono" style={{ color: 'var(--accent-1)' }}>{a.workflow_id.slice(0, 12)}...</span></div>
                  </div>
                  <span className="badge badge-pending">Pending</span>
                </div>
                {a.summary && (
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 16, padding: '10px 14px', background: 'var(--bg-surface)', borderRadius: 8, borderLeft: '3px solid var(--yellow)' }}>
                    {a.summary}
                  </div>
                )}
                <div className="flex gap-2 items-center" style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                  <span>Requested: {a.requested_at ? new Date(a.requested_at).toLocaleString() : '—'}</span>
                  {a.expires_at && <span>· Expires: {new Date(a.expires_at).toLocaleString()}</span>}
                </div>
                <div className="flex gap-2">
                  <button className="btn btn-success" disabled={processing === a.id} onClick={() => handleApprove(a.id)}>
                    {processing === a.id ? 'Processing...' : '✓ Approve'}
                  </button>
                  <button className="btn btn-danger" disabled={processing === a.id} onClick={() => handleReject(a.id)}>
                    ✗ Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* History */}
      <div className="section-title mb-4" style={{ marginBottom: 12 }}>Decision History</div>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr><th>Workflow</th><th>Level</th><th>Role</th><th>Status</th><th>Approver</th><th>Decided</th></tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>Loading...</td></tr>}
            {decided.map(a => (
              <tr key={a.id}>
                <td><span className="text-mono" style={{ color: 'var(--accent-1)' }}>{a.workflow_id.slice(0, 12)}...</span></td>
                <td>Level {a.level}</td>
                <td style={{ textTransform: 'capitalize' }}>{a.requested_from_role}</td>
                <td><span className={`badge badge-${a.status}`}>{a.status}</span></td>
                <td>{a.approver_name || '—'}</td>
                <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{a.decided_at ? new Date(a.decided_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
            {!loading && decided.length === 0 && <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>No decisions yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
