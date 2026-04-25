---
title: Fakeout Backend
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Multi-cloud voice phishing detection API for Malaysia
---

# Fakeout Backend

FastAPI backend that powers the Fakeout caregiver dashboard. It analyses
incoming voice / text messages and assigns a 0-100 scam risk score using:

- **AWS Bedrock (Claude 3 Haiku)** – semantic scam detection
- **Alibaba DashScope (Qwen)** – cross-cloud second opinion
- **Groq Llama 3.3 70B** – deep tactic analysis + risk reasoning
- **HuggingFace** – scam-classifier confidence
- **OpenAI / Groq Whisper** – voice transcription

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET  | `/health` | Liveness probe |
| POST | `/risk/scan` | Score a text message |
| POST | `/audio/risk` | Score an uploaded audio file |
| GET  | `/caregiver/alerts` | List recent alerts |
| POST | `/caregiver/approve/{txn_id}` | Approve a held transaction |
| POST | `/caregiver/cancel/{txn_id}` | Block a held transaction |
| POST | `/telegram/webhook` | Telegram bot ingest |

See `/docs` for the full OpenAPI schema once running.

## Required secrets (set in Space → Settings → Variables and secrets)

- `GROQ_API_KEY`
- `HUGGINGFACE_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- `ALIBABA_ACCESS_KEY_ID`, `ALIBABA_ACCESS_KEY_SECRET`
- `ALIBABA_OSS_ENDPOINT`, `ALIBABA_OSS_BUCKET`
- `ALIBABA_KMS_REGION`, `ALIBABA_KMS_KEY_ID`
- `DASHSCOPE_API_KEY` (optional)
