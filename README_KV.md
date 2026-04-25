# 🛡️ KV's Module – OpenClaw + n8n Voice Phishing Interceptor

> **Role:** Intercept scam voice notes & texts from WhatsApp, forward to Jane's AI backend.
> **No Meta Business API needed.** Just scan a QR code and go.

---

## 🎬 How It Works

```
Scammer (+60 16-356 9782) sends voice note / text
        │
        ▼
┌──────────────────────────────────────┐
│  OpenClaw (WhatsApp Bridge)          │
│  • Connects via QR code scan        │
│  • Monitors watchlisted numbers     │
│  • Downloads voice notes            │
│  • Forwards to n8n webhook          │
└──────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│  n8n (Orchestrator)                  │
│  • Voice → Jane (Whisper + Risk)    │
│  • Text  → Jane (Direct scoring)   │
│  • High risk? → Shawn (Hold)       │
└──────────────────────────────────────┘
        │
        ▼
Jane (FastAPI) → Shawn (AWS/Alibaba) → SY (Dashboard)
```

---

## 🚀 Setup (5 Minutes)

### Step 1: Install OpenClaw
```bash
cd ~/Desktop/Fakeout/openclaw
npm install
```

### Step 2: Start Redis
```bash
brew install redis
brew services start redis
```

### Step 3: Start Everything (4 Terminal Tabs)

**Tab 1 – OpenClaw (WhatsApp Bridge):**
```bash
cd ~/Desktop/Fakeout/openclaw
npm start
```
A QR code will appear. **Scan it with your WhatsApp** (Settings > Linked Devices > Link a Device).

**Tab 2 – n8n (Orchestrator):**
```bash
npx n8n start
```
Then open http://localhost:5678, import `n8n/voice_phishing_workflow.json`, and toggle **Active**.

**Tab 3 – Jane's Backend (FastAPI):**
```bash
cd ~/Desktop/Fakeout/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Tab 4 – SY's Dashboard (Svelte):**
```bash
cd ~/Desktop/Fakeout/frontend
npm install && npm run dev
```

### Step 4: Test It!
Ask the scammer number (+60 16-356 9782) to send you a voice note.
Watch the OpenClaw terminal light up! 🚨

---

## 📁 Files

| File | Owner | Purpose |
|------|-------|---------|
| `openclaw/server.js` | KV | WhatsApp bridge – QR scan, message monitoring |
| `openclaw/package.json` | KV | Dependencies (Baileys, axios) |
| `n8n/voice_phishing_workflow.json` | KV | n8n pipeline: OpenClaw → Jane → Shawn |
| `backend/` | Jane | FastAPI + Whisper + Risk Scoring |
| `frontend/` | SY | Svelte Caregiver Dashboard |

---

## 🔌 The Full Team Flow

```
KV (OpenClaw + n8n)
  │
  ├── Voice Note → POST /webhook/whatsapp-voice (Jane)
  │     → Whisper transcription
  │     → Risk scoring (keywords, patterns, caller analysis)
  │
  ├── Text Message → POST /risk/score (Jane)
  │     → Direct risk scoring
  │
  └── If risk ≥ 80 → POST /tng/hold (Shawn)
        → AWS Lambda secondary scoring
        → Alibaba OSS encrypted storage
        → Transaction HELD
        → SY's Dashboard shows alert
        → Caregiver approves or cancels
        → Auto-cancel after 10 minutes
```

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| QR code not showing | Delete `auth_info_fakeout/` folder and restart OpenClaw |
| "Forward failed" | Make sure n8n is running and workflow is Active |
| No messages detected | Check that the scammer number is in `WATCHLIST_NUMBERS` in `.env` |
| Backend errors | Make sure Redis is running: `brew services start redis` |

---

**Built by KV for TNG Digital FINHACK 2026** 🛡️
