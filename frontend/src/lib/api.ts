// Centralized API client — all calls go through here
const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API error');
  }
  return res.json();
}

export const api = {
  // ── Health ─────────────────────────────────────────────────
  health: () => request<any>('/health'),

  // ── Dashboard Analytics ────────────────────────────────────
  dashboard: () => request<any>('/api/v1/analytics/dashboard'),
  costSummary: () => request<any>('/api/v1/analytics/cost'),
  recentEvents: (limit = 50) => request<any>(`/api/v1/analytics/events/recent?limit=${limit}`),
  auditLogs: (limit = 50) => request<any>(`/api/v1/analytics/audit-logs?limit=${limit}`),

  // ── Agents ────────────────────────────────────────────────
  agents: () => request<any[]>('/api/v1/agents/'),
  agentHealth: () => request<any>('/api/v1/agents/health'),
  agentLogs: (name: string) => request<any[]>(`/api/v1/agents/${name}/logs`),

  // ── Workflows ─────────────────────────────────────────────
  workflows: (params?: Record<string, string>) => {
    const q = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<any>(`/api/v1/workflow/${q}`);
  },
  workflow: (id: string) => request<any>(`/api/v1/workflow/${id}`),
  workflowEvents: (id: string) => request<any[]>(`/api/v1/workflow/${id}/events`),
  workflowConversation: (id: string) => request<any>(`/api/v1/workflow/${id}/conversation`),

  startWorkflow: (body: { message: string; employee_id: string; demo_mode?: boolean }) =>
    request<any>('/api/v1/workflow/start/sync', { method: 'POST', body: JSON.stringify(body) }),

  retryWorkflow: (id: string) => request<any>(`/api/v1/workflow/${id}/retry`, { method: 'POST' }),
  cancelWorkflow: (id: string) => request<any>(`/api/v1/workflow/${id}`, { method: 'DELETE' }),

  // ── Approvals ─────────────────────────────────────────────
  pendingApprovals: () => request<any[]>('/api/v1/approvals/pending'),
  allApprovals: (status?: string) => {
    const q = status ? `?status=${status}` : '';
    return request<any[]>(`/api/v1/approvals/${q}`);
  },
  approve: (id: string, body: { reason?: string; approver_name: string }) =>
    request<any>(`/api/v1/approvals/${id}/approve`, { method: 'POST', body: JSON.stringify(body) }),
  reject: (id: string, body: { reason?: string; approver_name: string }) =>
    request<any>(`/api/v1/approvals/${id}/reject`, { method: 'POST', body: JSON.stringify(body) }),

  // ── Employees ─────────────────────────────────────────────
  employees: (params?: Record<string, string>) => {
    const q = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<any>(`/api/v1/employees/${q}`);
  },
  employee: (id: string) => request<any>(`/api/v1/employees/${id}`),

  // ── Process Designer ──────────────────────────────────────
  definitions: () => request<any[]>('/api/v1/definitions/'),
  definition: (name: string, version = 'v1') => request<any>(`/api/v1/definitions/${name}/${version}`),

  // ── Prompts ────────────────────────────────────────────────
  prompts: () => request<any[]>('/api/v1/prompts/'),
  prompt: (name: string) => request<any>(`/api/v1/prompts/${name}`),
  updatePrompt: (name: string, content: string) =>
    request<any>(`/api/v1/prompts/${name}`, { method: 'PUT', body: JSON.stringify({ content }) }),

  // ── Demo ──────────────────────────────────────────────────
  demoMode: () => request<any>('/api/v1/demo/mode'),
};

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001';
