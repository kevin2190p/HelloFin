# 🛡️ HelloFin – Voice Phishing Detection System

> **TNG Digital FINHACK 2026** | Bank-grade voice phishing detection with multi-cloud security

HelloFin intercepts WhatsApp voice notes in real-time, transcribes them using OpenAI Whisper, detects phishing patterns with a multi-factor risk engine, and holds suspicious transactions — giving caregivers the power to block scams before money moves.

## 🎬 Demo Flow

```
WhatsApp Voice Note → n8n Workflow → Whisper Transcription → Risk Scoring
    → HIGH RISK (≥80) → Transaction HELD → User sees "Processing"
    → Caregiver WhatsApp Alert → Dashboard Review → Approve or Cancel
    → Auto-cancel after 10 minutes if no action
```

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────┐    ┌──────────────┐
│  WhatsApp   │───▶│   n8n    │───▶│   FastAPI    │
│  Voice Note │    │ Workflow │    │   Backend    │
└─────────────┘    └──────────┘    └──────┬───────┘
                                          │
                   ┌──────────────────────┼──────────────────────┐
                   │                      │                      │
            ┌──────▼──────┐    ┌──────────▼──────┐    ┌─────────▼────────┐
            │   OpenAI    │    │      Redis      │    │   Alibaba OSS    │
            │   Whisper   │    │   (Tx Store)    │    │  (Audio Vault)   │
            └─────────────┘    └────────┬────────┘    └──────────────────┘
                                        │
                               ┌────────▼────────┐
                               │  Svelte Dashboard│
                               │  (Caregiver UI)  │
                               └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Configure Environment
```bash
cp .env.example .env   # or edit the existing .env
# Fill in your API keys (see Credentials section below)
```

### 2. Run with Docker Compose
```bash
docker compose up -d
```

Services will be available at:
- **FastAPI**: http://localhost:8000 (API docs: http://localhost:8000/docs)
- **n8n**: http://localhost:5678
- **Dashboard**: http://localhost:3000
- **Redis**: localhost:6379

### 3. Import n8n Workflow
1. Open http://localhost:5678
2. Go to Workflows → Import from File
3. Select `n8n/voice_phishing_workflow.json`
4. Configure WhatsApp credentials in n8n
5. Optional: import `n8n/telegram_integration_workflow.json` for Telegram-based alerts and configure the Telegram bot credential

## 📁 Project Structure

```
HelloFin/
├── .env                          # Environment variables (gitignored)
├── .gitignore
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI entry + audit middleware
│       ├── routers/
│       │   ├── webhook.py        # WhatsApp voice note receiver
│       │   ├── risk.py           # Risk scoring endpoint
│       │   └── tng.py            # TNG hold + caregiver alerts
│       ├── services/
│       │   ├── whisper_client.py  # OpenAI Whisper integration
│       │   ├── risk_scorer.py     # Multi-factor risk engine
│       │   ├── cloud_clients.py   # AWS Lambda + Alibaba OSS/KMS
│       │   └── audit_logger.py    # SOC2-ready JSON audit logs
│       └── models/
│           └── schemas.py         # Pydantic request/response models
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.svelte             # Caregiver dashboard
│       ├── main.js
│       └── lib/
│           ├── api.js             # API client
│           └── caregiverDashboard.js
├── n8n/
│   └── voice_phishing_workflow.json
├── openclaw/
│   └── config.yaml
└── README.md
```

## 🔑 Credentials Required

| Service | Key | Where to Get |
|---------|-----|-------------|
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) |
| Meta App | `META_APP_ID`, `META_APP_SECRET` | [developers.facebook.com](https://developers.facebook.com) |
| WhatsApp | `WHATSAPP_BUSINESS_ACCOUNT_ID`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN` | Meta Business Suite |
| AWS | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | IAM Console (Lambda/S3) |
| Alibaba | `ALIBABA_ACCESS_KEY_ID`, `ALIBABA_ACCESS_KEY_SECRET` | RAM Console (OSS/KMS) |
| TNG | `TNG_MINI_PROGRAM_APP_ID`, `TNG_MINI_PROGRAM_APP_SECRET` | [miniprogram.tngdigital.com.my](https://miniprogram.tngdigital.com.my) |
| Telegram | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PUSH_CHAT_ID` | Telegram BotFather + your caregiver chat/group ID |

## 🔒 Security (Bank-Grade / SOC2 Ready)

- **Zero-trust**: All endpoints validated, no implicit trust
- **Encryption at rest**: Alibaba OSS AES-256 server-side encryption
- **Encryption in transit**: TLS 1.2+ enforced
- **Audit logging**: Every API request logged as JSON (SOC2 compliant)
- **Secrets management**: All credentials via environment variables
- **Key management**: Alibaba KMS for PII encryption
- **No credential leakage**: `.env` gitignored, no hardcoded secrets

## 🤖 OpenClaw Integration

OpenClaw can be used as an alternative to n8n for WhatsApp webhook handling. For this hackathon, **n8n is the primary orchestrator**, but the `openclaw/config.yaml` provides a ready-to-use configuration that:

- Listens for WhatsApp voice messages on port 9000
- Auto-downloads media attachments
- Forwards audio to the same FastAPI endpoint
- Sends caregiver alerts via WhatsApp

To use OpenClaw instead of n8n, deploy the OpenClaw service with the provided config and point your Meta webhook URL to the OpenClaw endpoint.

## 🧪 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhook/whatsapp-voice` | Receive audio, transcribe, score risk |
| `POST` | `/risk/score` | Score risk from transcript + context |
| `POST` | `/tng/hold` | Hold high-risk transaction |
| `GET` | `/caregiver/alerts` | List pending alerts |
| `POST` | `/caregiver/approve/{txn_id}` | Approve transaction |
| `POST` | `/caregiver/cancel/{txn_id}` | Cancel transaction |
| `GET` | `/health` | Health check |

## 👥 Team

| Branch | Member |
|--------|--------|
| `kv` | Kevin |
| `shawn` | Shawn |
| `jane` | Jane |
| `sy` | SY |

---

**Built with ❤️ for TNG Digital FINHACK 2026**