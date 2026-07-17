# 🤖 AI Workforce OS — Complete System Guide

## What Is This Platform?

**AI Workforce OS** is an **enterprise multi-agent AI automation platform** that automates HR, travel, finance, and compliance workflows using 15 specialized AI agents orchestrated by a Supervisor Agent.

Instead of employees filling forms and waiting days for approvals, they simply describe their request in **natural language** (e.g., *"I need to travel to Dubai from Aug 1-5 for a client meeting"*) and the system automatically handles everything — flight search, hotel booking, budget checks, visa processing, manager approvals, invoice generation, and email notifications.

---

## 🏗️ Architecture

```
FRONTEND (Next.js :3000)
  ↕ HTTP REST + WebSocket
BACKEND (FastAPI :8001)
  └─ Supervisor Agent
       └─ 15 Specialist Agents
            └─ SQLite Database (ai_workforce_v2.db)
  └─ Event Bus → WebSocket streams to dashboard
```

**Tech Stack:**
- **Backend**: FastAPI + SQLAlchemy Async + SQLite + Python 3.13
- **Frontend**: Next.js 16 + TypeScript + Vanilla CSS
- **AI**: Mock LLM (default) or Google Gemini Flash
- **Real-time**: WebSocket event bus

---

## 🚀 Start Commands (copy-paste into 2 terminals)

### Terminal 1 — Backend
```bash
conda activate torch_gpu
cd C:\Users\nk\AI-Workforce-OS\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
On first boot: auto-creates DB + seeds 500 employees, 300 travel requests, etc.

### Terminal 2 — Frontend
```bash
conda activate torch_gpu
cd C:\Users\nk\AI-Workforce-OS\frontend
npm install
npx next dev -p 3000
```

| URL | What |
|-----|------|
| http://localhost:3000 | Main Dashboard |
| http://localhost:8001/docs | API Swagger Docs |
| http://localhost:8001/health | Health check |

---

## 📄 All 11 Pages — What They Do

| Page | URL | Purpose |
|------|-----|---------|
| Live Dashboard | `/` | KPIs, live event feed, agent fleet, cost summary |
| Demo Launcher | `/demo` | Pick scenario → launch AI pipeline → see results |
| Workflows | `/workflows` | History of all workflow runs with filtering |
| Workflow Detail | `/workflows/[id]` | Steps timeline, events, agent conversation |
| Approval Center | `/approvals` | Review and approve/reject paused workflows |
| Agent Fleet | `/agents` | All 15 agents, their status, metrics, logs |
| Employees | `/employees` | Browse 500 seeded employees |
| Analytics | `/analytics` | SLA charts, volume trends, performance |
| Prompt Registry | `/prompts` | View/edit AI prompts live |
| Process Designer | `/process-designer` | View workflow JSON definitions |
| Audit Ledger | `/audit` | Immutable log of all system actions |

---

## 🤖 The 15 AI Agents

| Agent | Owner | Capabilities |
|-------|-------|-------------|
| **SupervisorAgent** | platform | Parse NL intent, orchestrate full workflow, resume after approval |
| **ValidationAgent** | hr | Verify employee data, passport validity, eligibility checks |
| **PolicyAgent** | compliance | Check travel/expense policy via RAG vector search |
| **TravelAgent** | travel_desk | Search flights, select optimal option, create booking |
| **HotelAgent** | travel_desk | Search hotels by city/budget/stars, create hotel booking |
| **VisaAgent** | travel_desk | Apply for visa, verify documents, track application |
| **LeaveAgent** | hr | Check balance, approve dates, deduct from entitlement |
| **FinanceAgent** | finance | Budget check, invoice creation, expense approval |
| **HRAgent** | hr | HRMS update, calendar blocking, org chart lookup |
| **ApprovalAgent** | platform | Create approval request, pause workflow, notify manager |
| **NotificationAgent** | platform | Email/SMS/Slack (all mocked in demo mode) |
| **AuditAgent** | compliance | Immutable compliance log every step |
| **DocumentAgent** | hr | Verify passport, visas, certificates |
| **ReportingAgent** | analytics | Generate summary reports for managers |
| **AnalyticsAgent** | analytics | SLA metrics, cost forecasting, anomaly detection |

---

## 📋 Workflow Pipelines (Step-by-Step)

### ✈ International Business Travel (9 steps)
```
Step 1 → ValidationAgent    Verify employee & passport
Step 2 → PolicyAgent        Check travel policy compliance
Step 3 → TravelAgent        Search & book best flight
Step 4 → HotelAgent         Find & reserve hotel
Step 5 → VisaAgent          Apply for visa if required
Step 6 → FinanceAgent       Budget check + cost estimate
Step 7 → ApprovalAgent      ⏸ PAUSE — manager must approve
Step 8 → FinanceAgent       Generate invoice
Step 9 → NotificationAgent  Email full itinerary to employee
```

### 🌴 Annual Leave Request (7 steps)
```
Step 1 → ValidationAgent   Verify employee
Step 2 → PolicyAgent       Check leave policy
Step 3 → LeaveAgent        Verify balance & dates
Step 4 → ApprovalAgent     ⏸ PAUSE — manager approves
Step 5 → LeaveAgent        Deduct leave days from balance
Step 6 → HRAgent           Block calendar, update HRMS
Step 7 → NotificationAgent Email leave confirmation
```

### 🛂 Business Visa (8 steps)
```
Step 1 → ValidationAgent   Verify employee record
Step 2 → DocumentAgent     Check passport validity (≥6 months)
Step 3 → PolicyAgent       Check visa policy for country
Step 4 → VisaAgent         Submit visa application
Step 5 → VisaAgent         Get tracking number & status
Step 6 → ApprovalAgent     ⏸ PAUSE — manager authorization
Step 7 → FinanceAgent      Invoice visa fees
Step 8 → NotificationAgent Email tracking details
```

### 💰 Expense Reimbursement (7 steps)
```
Step 1 → ValidationAgent   Verify employee
Step 2 → FinanceAgent      Check budget codes & limits
Step 3 → PolicyAgent       Validate expense policy
Step 4 → FinanceAgent      Create draft invoice
Step 5 → ApprovalAgent     ⏸ PAUSE — finance approval
Step 6 → FinanceAgent      Approve & schedule payment
Step 7 → AuditAgent        Create compliance audit record
```

---

## ⚙️ Configuration (`.env`)

| Key | Value | Notes |
|-----|-------|-------|
| `GEMINI_API_KEY` | (blank) | Add key to get real AI reasoning |
| `USE_MOCK_LLM` | false | Auto-true when no Gemini key |
| `GROQ_API_KEY` | your key | Optional Groq/Llama alternative |
| `DATABASE_URL` | sqlite:///./ai_workforce_v2.db | Change for PostgreSQL |
| `DEMO_MODE` | true | true = synthetic data |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | JWT expiry |

---

## 🔧 Bugs Fixed in This Session

1. **`faker` not installed** — `pip install -r requirements.txt` in `torch_gpu` env
2. **Tenant ID mismatch** — `jwt_handler.py` default was `demo-tenant-001`, fixed to `tenant-globaltech-001` (actual seeded data)
3. **Missing CSS classes** — Added `btn-success`, `btn-danger`, all `badge-*` status variants, `chat-bubble` styles
4. **WebSocket connection** — Confirmed WS connects directly to `ws://localhost:8001` (not through Next.js proxy)

---

## 💡 To Enable Real AI (Gemini)

1. Get free key: https://aistudio.google.com/app/apikey
2. Edit `.env`: `GEMINI_API_KEY="AIza...yourkey"`
3. Restart backend
4. Watch real LLM reasoning appear in Workflow Detail → Conversation tab
