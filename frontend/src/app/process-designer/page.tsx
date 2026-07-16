'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function ProcessDesignerPage() {
  const [definitions, setDefinitions] = useState<any[]>([]);
  const [selectedDef, setSelectedDef] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.definitions();
        setDefinitions(data);
        if (data.length > 0) {
          const detail = await api.definition(data[0].name, data[0].version);
          setSelectedDef(detail);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleSelect = async (name: string, version: string) => {
    setLoading(true);
    try {
      const detail = await api.definition(name, version);
      setSelectedDef(detail);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Process Designer</h1>
          <div className="section-sub">Define, version, and orchestrate agent-driven workflows</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16 }}>
        {/* Left Side: Def List */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>Definitions</div>
          <div className="flex flex-col gap-2">
            {definitions.map(d => (
              <div
                key={`${d.name}-${d.version}`}
                onClick={() => handleSelect(d.name, d.version)}
                className={`nav-item ${selectedDef?.name === d.name && selectedDef?.version === d.version ? 'active' : ''}`}
                style={{ justifyContent: 'space-between', padding: '10px 12px' }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{d.name.charAt(0).toUpperCase() + d.name.slice(1)}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>v{d.version}</div>
                </div>
                <span className={`badge ${d.is_active ? 'badge-completed' : 'badge-idle'}`} style={{ fontSize: 9 }}>
                  {d.is_active ? 'Active' : 'Draft'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right Side: Definition Pipeline Visualizer */}
        <div className="card">
          {loading ? (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 48 }}>Loading pipeline configuration...</div>
          ) : selectedDef ? (
            <div>
              <div className="flex items-center justify-between mb-6" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
                <div>
                  <h2 style={{ fontSize: 16, fontWeight: 700 }}>{selectedDef.name.charAt(0).toUpperCase() + selectedDef.name.slice(1)} Workflow Spec</h2>
                  <div className="section-sub">{selectedDef.description || 'No description provided'}</div>
                </div>
                <span className="badge badge-running" style={{ padding: '6px 12px' }}>v{selectedDef.version} Configuration</span>
              </div>

              {/* Steps timeline visualization */}
              <div className="steps-timeline" style={{ position: 'relative' }}>
                {(selectedDef.definition?.steps || []).map((step: any, index: number) => (
                  <div key={index} className="step-item" style={{ background: 'var(--bg-surface)' }}>
                    <div className="step-num">{index + 1}</div>
                    <div className="step-info">
                      <div className="step-name">{step.name}</div>
                      <div className="step-agent" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span>Agent:</span>
                        <span style={{ color: 'var(--accent-1)', fontWeight: 600 }}>{step.agent}</span>
                      </div>
                      {step.args && (
                        <div style={{ marginTop: 8, padding: 8, background: 'var(--bg-card)', borderRadius: 6, border: '1px solid var(--border)' }}>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>ARGUMENTS</div>
                          <pre style={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)', overflowX: 'auto' }}>
                            {JSON.stringify(step.args, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                    {step.approval_required && (
                      <span className="badge badge-paused" style={{ alignSelf: 'flex-start' }}>Requires Human Approval</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 48 }}>No workflow definition selected.</div>
          )}
        </div>
      </div>
    </div>
  );
}
