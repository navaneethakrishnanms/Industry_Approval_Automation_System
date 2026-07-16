'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useWebSocket } from '@/lib/useWebSocket';

const DEMO_SCENARIOS = [
  {
    id: 'travel',
    title: 'International Business Travel',
    icon: '✈',
    color: 'var(--accent-1)',
    description: 'Employee requesting Dubai travel with flight, hotel, visa',
    message: 'I need to travel to Dubai for a client meeting from August 1st to August 5th 2026. Please arrange flight and hotel.',
    tag: 'Full 9-step pipeline',
  },
  {
    id: 'leave',
    title: 'Annual Leave Request',
    icon: '🌴',
    color: 'var(--green)',
    description: 'Employee requesting 5 days annual leave',
    message: 'I would like to take 5 days of annual leave from August 10th to August 14th for a family vacation.',
    tag: '7-step pipeline',
  },
  {
    id: 'visa',
    title: 'Business Visa Application',
    icon: '🛂',
    color: 'var(--cyan)',
    description: 'USA business visa processing',
    message: 'I need a business visa for USA for an upcoming conference in September. Travel date is September 15th.',
    tag: '8-step pipeline',
  },
  {
    id: 'finance',
    title: 'Expense Reimbursement',
    icon: '💰',
    color: 'var(--yellow)',
    description: 'Client entertainment expense claim',
    message: 'I need to submit an expense claim for client entertainment worth INR 25,000 for the Q2 product launch event.',
    tag: '7-step pipeline',
  },
];

export default function DemoPage() {
  const [employees, setEmployees] = useState<any[]>([]);
  const [selectedEmp, setSelectedEmp] = useState('');
  const [message, setMessage] = useState('');
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const { events, connected } = useWebSocket('/ws/dashboard');

  useEffect(() => {
    api.employees({ page_size: '20' }).then(d => {
      const emps = d.items || [];
      setEmployees(emps);
      if (emps.length > 0) setSelectedEmp(emps[0].id);
    });
  }, []);

  const runScenario = (scenario: typeof DEMO_SCENARIOS[0]) => {
    setMessage(scenario.message);
  };

  const startWorkflow = async () => {
    if (!message.trim() || !selectedEmp) return;
    setRunning(true); setResult(null); setError('');
    try {
      const res = await api.startWorkflow({ message, employee_id: selectedEmp, demo_mode: true });
      setResult(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const liveWorkflowEvents = result?.workflow_id
    ? events.filter(e => e.workflow_id === result.workflow_id)
    : [];

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Demo Launcher</h1>
          <div className="section-sub">Trigger any workflow to see the AI agent pipeline execute in real-time</div>
        </div>
        <div className={`live-indicator`}><span className="demo-dot" />{connected ? 'WS Connected' : 'Connecting...'}</div>
      </div>

      {/* Scenario cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16, marginBottom: 24 }}>
        {DEMO_SCENARIOS.map(s => (
          <div key={s.id} className="card glow-card" style={{ cursor: 'pointer', border: message === s.message ? `1px solid ${s.color}` : undefined }}
            onClick={() => runScenario(s)}>
            <div style={{ fontSize: 28, marginBottom: 10 }}>{s.icon}</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{s.title}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{s.description}</div>
            <span className="cap-tag">{s.tag}</span>
          </div>
        ))}
      </div>

      {/* Compose */}
      <div className="card mb-6">
        <div className="section-title mb-4" style={{ marginBottom: 16 }}>Configure & Launch</div>
        <div className="grid-2 mb-4" style={{ marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Employee</div>
            <select className="select" value={selectedEmp} onChange={e => setSelectedEmp(e.target.value)}>
              {employees.map(e => (
                <option key={e.id} value={e.id}>{e.name} — {e.designation} ({e.employee_id})</option>
              ))}
            </select>
          </div>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Mode</div>
            <div className="badge badge-idle" style={{ padding: '9px 12px', borderRadius: 8, display: 'block', textAlign: 'center' }}>
              SYNTHETIC (Mock LLM + Fake APIs)
            </div>
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Natural Language Request</div>
          <textarea className="textarea" rows={3} value={message} onChange={e => setMessage(e.target.value)}
            placeholder="Describe the employee request in natural language..." />
        </div>
        <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
          disabled={running || !message.trim() || !selectedEmp} onClick={startWorkflow}>
          {running ? (
            <span>Processing... (Watch the Live Feed)</span>
          ) : (
            <span>▶ Start Workflow — Supervisor Agent will orchestrate</span>
          )}
        </button>
        {error && <div style={{ color: 'var(--red)', fontSize: 13, marginTop: 12, padding: 12, background: 'var(--red-dim)', borderRadius: 8 }}>{error}</div>}
      </div>

      {/* Result */}
      {result && (
        <div className="card" style={{ border: '1px solid rgba(16,185,129,0.25)' }}>
          <div className="section-title mb-4" style={{ marginBottom: 16, color: 'var(--green)' }}>
            Workflow Complete
          </div>
          <div className="grid-2 mb-4" style={{ marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>WORKFLOW ID</div>
              <div className="text-mono" style={{ color: 'var(--accent-1)' }}>{result.workflow_id}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>TYPE</div>
              <div style={{ textTransform: 'capitalize', fontWeight: 600 }}>{result.workflow_type}</div>
            </div>
          </div>

          {result.selected_flight && (
            <div className="card mb-4" style={{ marginBottom: 12, background: 'rgba(99,102,241,0.05)' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-1)', marginBottom: 8 }}>Selected Flight</div>
              <div style={{ fontSize: 13 }}>
                {result.selected_flight.airline} {result.selected_flight.flight_number} ·
                {result.selected_flight.departure} → {result.selected_flight.arrival} ·
                ₹{result.selected_flight.price?.toLocaleString()}
                {result.selected_flight.booking_ref && <span style={{ color: 'var(--green)', marginLeft: 8 }}>REF: {result.selected_flight.booking_ref}</span>}
              </div>
            </div>
          )}

          {result.selected_hotel && (
            <div className="card mb-4" style={{ marginBottom: 12, background: 'rgba(6,182,212,0.05)' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--cyan)', marginBottom: 8 }}>Selected Hotel</div>
              <div style={{ fontSize: 13 }}>
                {result.selected_hotel.name} · {result.selected_hotel.stars}★ · ₹{result.selected_hotel.price_per_night?.toLocaleString()}/night
              </div>
            </div>
          )}

          {result.invoice_number && (
            <div style={{ fontSize: 13, padding: '8px 12px', background: 'var(--green-dim)', borderRadius: 8, color: 'var(--green)' }}>
              Invoice Created: <strong>{result.invoice_number}</strong>
            </div>
          )}

          <div style={{ marginTop: 12 }}>
            <a href={`/workflows/${result.workflow_id}`} className="btn btn-primary btn-sm">View Full Execution →</a>
          </div>
        </div>
      )}
    </div>
  );
}
