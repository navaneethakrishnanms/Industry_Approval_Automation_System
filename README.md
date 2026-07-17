# 🤖 AI Workforce OS
### Enterprise Multi-Agent AI Workflow Automation Platform

[![Python](https://img.shields.io/badge/Python-3.13-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org)
[![SQLite](https://img.shields.io/badge/Database-SQLite-lightblue)](https://sqlite.org)

AI Workforce OS is an **enterprise-grade multi-agent AI automation platform** that automates HR, travel, finance, and compliance workflows. Instead of manually filling forms and waiting hours for approvals, employees describe their request in natural language and 15 specialized AI agents handle everything automatically.

---

## 🎯 What It Automates

| Workflow | Manual Time | With AI Workforce OS |
|----------|------------|----------------------|
| International Travel Request | 6–8 hours | **~15 seconds** |
| Annual Leave Request | 4–6 hours | **~45 seconds** |
| Business Visa Application | 2–4 hours | **~30 seconds** |
| Expense Reimbursement | 2–3 hours | **~20 seconds** |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+ (conda environment recommended)
- Node.js 18+

### 1. Clone the Repository

```bash
git clone https://github.com/navaneethakrishnanms/Industry_Approval_Automation_System.git
cd Industry_Approval_Automation_System
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and add your Gemini API key (optional — works in Mock mode without it):

```env
GEMINI_API_KEY="your-gemini-api-key-here"
USE_MOCK_LLM=false
```

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

### 3. Start the Backend (Terminal 1)

```bash
conda activate torch_gpu
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

On first run, the database is created and seeded automatically with 500 employees, 300 travel records, and more.

Watch for this output — it means the backend is ready:

```
  [OK] Database tables created/verified
  [AgentRegistry] 15 agents registered successfully
  [OK] LLM Client initialized
  INFO: Uvicorn running on http://0.0.0.0:8001
```

### 4. Start the Frontend (Terminal 2)

```bash
conda activate torch_gpu
cd frontend
npm install
npm run dev
```

> **Windows users:** The `package.json` already has `--webpack` flag configured to avoid Turbopack compatibility issues.

### 5. Open the App

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Main Application |
| http://localhost:8001/docs | FastAPI Swagger API Docs |
| http://localhost:8001/health | Backend Health Check |

---

## 🏗️ Architecture

```
FRONTEND  (Next.js  → localhost:3000)
    ↕  HTTP REST + WebSocket
BACKEND   (FastAPI  → localhost:8001)
    └─ SupervisorAgent
         └─ 15 Specialist Agents
              └─ SQLite Database
    └─ Event Bus → WebSocket → Live Dashboard
```

---

## 🤖 The 15 AI Agents

| Agent | Role | What It Does |
|-------|------|-------------|
| **SupervisorAgent** | Orchestrator | Parses NL intent, selects workflow, delegates |
| **ValidationAgent** | HR | Employee eligibility, passport validity |
| **PolicyAgent** | Compliance | Corporate policy enforcement |
| **TravelAgent** | Travel Desk | Flight search, selection, booking |
| **HotelAgent** | Travel Desk | Hotel search by city/budget/stars |
| **VisaAgent** | Travel Desk | Visa application, tracking |
| **LeaveAgent** | HR | Leave balance check and deduction |
| **FinanceAgent** | Finance | Budget checks, invoice creation |
| **HRAgent** | HR | HRMS updates, calendar blocking |
| **ApprovalAgent** | Platform | Manager notification, 1-click approval |
| **NotificationAgent** | Platform | Email/SMS/Slack notifications |
| **AuditAgent** | Compliance | Immutable audit trail |
| **DocumentAgent** | HR | Passport/document verification |
| **ReportingAgent** | Analytics | Report generation |
| **AnalyticsAgent** | Analytics | SLA metrics, KPI tracking |

---

## 📋 Workflow Pipelines

### ✈️ International Business Travel (9 steps)
```
1. ValidationAgent   → Verify employee & passport
2. PolicyAgent       → Check travel policy
3. TravelAgent       → Search & book best flight
4. HotelAgent        → Find & reserve hotel
5. VisaAgent         → Apply for visa if required
6. FinanceAgent      → Budget check + cost estimate
7. ApprovalAgent     → ⏸ Manager approves (1-click)
8. FinanceAgent      → Generate invoice
9. NotificationAgent → Email itinerary to employee
```

### 🌴 Annual Leave (7 steps)
```
1. ValidationAgent   → Verify employee
2. PolicyAgent       → Check leave policy
3. LeaveAgent        → Verify balance & dates
4. ApprovalAgent     → ⏸ Manager approves (1-click)
5. LeaveAgent        → Deduct leave balance
6. HRAgent           → Block calendar, update HRMS
7. NotificationAgent → Email confirmation
```

### 🛂 Visa Application (8 steps)
```
1. ValidationAgent   → Check employee data
2. DocumentAgent     → Verify passport validity
3. PolicyAgent       → Check visa policy
4. VisaAgent         → Submit visa application
5. VisaAgent         → Track & get reference number
6. ApprovalAgent     → ⏸ Manager authorizes
7. FinanceAgent      → Invoice visa fees
8. NotificationAgent → Email tracking details
```

### 💰 Expense Reimbursement (7 steps)
```
1. ValidationAgent   → Verify employee
2. FinanceAgent      → Check budget codes & limits
3. PolicyAgent       → Validate expense policy
4. FinanceAgent      → Create draft invoice
5. ApprovalAgent     → ⏸ Finance approval
6. FinanceAgent      → Approve for payment
7. AuditAgent        → Compliance audit record
```

---

## 📱 Application Pages

| Page | URL | Description |
|------|-----|-------------|
| Live Dashboard | `/` | KPIs, real-time events, agent fleet, cost tracking |
| Demo Launcher | `/demo` | Launch any workflow with natural language |
| Workflow History | `/workflows` | All past workflows with filtering |
| Workflow Detail | `/workflows/[id]` | Steps, events, agent conversation |
| Approval Center | `/approvals` | Approve/reject paused workflows |
| Agent Fleet | `/agents` | All 15 agents, metrics, logs |
| Employees | `/employees` | Browse 500 seeded employees |
| Analytics | `/analytics` | SLA, volume, performance charts |
| Prompt Registry | `/prompts` | View and edit AI agent prompts live |
| Process Designer | `/process-designer` | Workflow JSON definitions |
| Audit Logs | `/audit` | Immutable compliance ledger |

---

## ⚙️ Configuration (.env)

```env
# Application
APP_NAME="AI Workforce OS"
APP_ENV=development
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite+aiosqlite:///./ai_workforce_v2.db

# AI / LLM
GEMINI_API_KEY=""            # Add key to enable real Gemini AI
GEMINI_MODEL=gemini-1.5-flash
USE_MOCK_LLM=false           # Auto-true when no API key is set

# Backend runs on port 8001
# Frontend runs on port 3000
```

---

## 🛠️ Project Structure

```
Industry_Approval_Automation_System/
├── backend/
│   ├── app/
│   │   ├── agents/           # All 15 AI agent implementations
│   │   ├── auth/             # JWT authentication
│   │   ├── config/           # Constants and settings
│   │   ├── core/             # LLM client, event bus, memory
│   │   ├── database/         # SQLAlchemy async setup
│   │   ├── models/           # ORM models
│   │   ├── routers/          # FastAPI route handlers
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── workflow_engine/  # Execution engine + workflow JSONs
│   │   └── main.py           # Application entry point
│   ├── demo_data/            # Database seeding scripts
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js app router pages
│   │   ├── components/       # UI components
│   │   └── lib/
│   │       └── api.ts        # API client (connects to :8001)
│   └── package.json
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 🧪 Running a Demo

1. Go to **http://localhost:3000/demo**
2. Click **"International Business Travel"**
3. Select any employee from the dropdown
4. Click **▶ Start Workflow**
5. Watch the **Live Dashboard** for real-time agent events
6. Go to **Approvals** → click **✓ Approve**
7. Watch the workflow complete all remaining steps automatically
8. Check **Audit Logs** for the compliance record

---

## 🚀 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI 0.115 + Python 3.13 |
| Database | SQLAlchemy Async + SQLite |
| Frontend | Next.js 16 + TypeScript |
| Styling | Vanilla CSS |
| AI/LLM | Google Gemini 1.5 Flash (Mock fallback included) |
| Real-time | WebSocket (native FastAPI) |
| Auth | JWT (python-jose) |

---

*AI Workforce OS — Turn your manual SOP into a 15-second AI workflow.*
