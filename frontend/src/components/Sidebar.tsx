'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useWebSocket } from '@/lib/useWebSocket';

const NAV = [
  { section: 'Command Center', items: [
    { href: '/', label: 'Live Dashboard', icon: '▦' },
    { href: '/workflows', label: 'Workflows', icon: '⟳' },
    { href: '/agents', label: 'Agent Fleet', icon: '◈' },
    { href: '/approvals', label: 'Approvals', icon: '✓', badge: true },
  ]},
  { section: 'Platform', items: [
    { href: '/process-designer', label: 'Process Designer', icon: '⊞' },
    { href: '/employees', label: 'Employees', icon: '◉' },
    { href: '/analytics', label: 'Analytics', icon: '⊛' },
    { href: '/prompts', label: 'Prompt Registry', icon: '⊘' },
  ]},
  { section: 'Demo', items: [
    { href: '/demo', label: 'Run Demo', icon: '▶' },
    { href: '/audit', label: 'Audit Logs', icon: '≡' },
  ]},
];

export function Sidebar() {
  const pathname = usePathname();
  const { connected, events } = useWebSocket('/ws/dashboard');
  const pendingApprovals = events.filter(e => e.event_type === 'approval.requested').length;

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="sidebar-logo-text">AI Workforce OS</span>
        <span className="sidebar-logo-sub">Enterprise v1.0</span>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(({ section, items }) => (
          <div key={section}>
            <div className="nav-section-label">{section}</div>
            {items.map(({ href, label, icon, badge }) => (
              <Link
                key={href}
                href={href}
                className={`nav-item ${pathname === href ? 'active' : ''}`}
              >
                <span className="nav-icon" style={{ fontSize: '14px' }}>{icon}</span>
                <span>{label}</span>
                {badge && pendingApprovals > 0 && (
                  <span className="nav-badge">{pendingApprovals}</span>
                )}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="demo-mode-badge">
          <span className={connected ? 'demo-dot' : ''} style={!connected ? { background: 'var(--red)', width: 6, height: 6, borderRadius: '50%', display: 'inline-block' } : {}} />
          <span style={{ color: connected ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
            {connected ? 'Live Feed' : 'Reconnecting'}
          </span>
          <span style={{ marginLeft: 'auto', opacity: 0.5 }}>SYNTHETIC</span>
        </div>
      </div>
    </aside>
  );
}
