'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<any[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<any>(null);
  const [editingContent, setEditingContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.prompts();
      setPrompts(data);
      if (data.length > 0) {
        const detail = await api.prompt(data[0].name);
        setSelectedPrompt(detail);
        setEditingContent(detail.content);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSelect = async (name: string) => {
    setLoading(true);
    setMessage('');
    try {
      const detail = await api.prompt(name);
      setSelectedPrompt(detail);
      setEditingContent(detail.content);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedPrompt) return;
    setSaving(true);
    setMessage('');
    try {
      await api.updatePrompt(selectedPrompt.name, editingContent);
      setMessage('Prompt updated successfully! Changes will take effect immediately.');
      setTimeout(() => setMessage(''), 4000);
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="section-title" style={{ fontSize: 20, fontWeight: 800 }}>Prompt Registry</h1>
          <div className="section-sub">View and live-edit AI Agent instructions and context templates</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16 }}>
        {/* Left list */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: 0.5 }}>Registry Prompts</div>
          <div className="flex flex-col gap-2">
            {prompts.map(p => (
              <div
                key={p.name}
                onClick={() => handleSelect(p.name)}
                className={`nav-item ${selectedPrompt?.name === p.name ? 'active' : ''}`}
                style={{ display: 'block', padding: '10px 12px' }}
              >
                <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>v{p.version}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Editor */}
        <div className="card">
          {loading ? (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 48 }}>Loading prompt content...</div>
          ) : selectedPrompt ? (
            <div>
              <div className="flex items-center justify-between mb-6" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 16 }}>
                <div>
                  <h2 style={{ fontSize: 16, fontWeight: 700 }}>{selectedPrompt.name}</h2>
                  <div className="section-sub">{selectedPrompt.description || 'System prompt template'}</div>
                </div>
                <span className="badge badge-running">Version {selectedPrompt.version}</span>
              </div>

              {message && (
                <div style={{
                  padding: 12,
                  background: message.startsWith('Error') ? 'var(--red-dim)' : 'var(--green-dim)',
                  color: message.startsWith('Error') ? 'var(--red)' : 'var(--green)',
                  borderRadius: 8,
                  fontSize: 13,
                  marginBottom: 16
                }}>
                  {message}
                </div>
              )}

              <div style={{ marginBottom: 16 }}>
                <textarea
                  className="textarea"
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 13,
                    lineHeight: 1.5,
                    minHeight: 380,
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)'
                  }}
                  value={editingContent}
                  onChange={e => setEditingContent(e.target.value)}
                />
              </div>

              <div className="flex gap-2">
                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                  {saving ? 'Saving...' : 'Save & Publish Prompt'}
                </button>
                <button className="btn btn-secondary" onClick={() => setEditingContent(selectedPrompt.content)}>
                  Reset Changes
                </button>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 48 }}>No prompt selected.</div>
          )}
        </div>
      </div>
    </div>
  );
}
