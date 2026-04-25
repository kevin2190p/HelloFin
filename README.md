# Fakeout

> **Stop scam calls before money leaves your wallet.**
> Private on-device AI scam-call protection for Touch 'n Go eWallet users in Malaysia.

**Track:** Security & Fraud · **Hackathon:** TNG FINHACK 2026

### 🔗 Live demo

**👉 [https://fakeout-tng-finhack.netlify.app](https://fakeout-tng-finhack.netlify.app)**

Open the link, click **Test Cloud** on the verification screen, and watch real AWS + Alibaba Cloud request IDs come back live.

| Resource | Link |
|---|---|
| Live demo | https://fakeout-tng-finhack.netlify.app |
| AWS Lambda monitor | [`scamsense-risk-event` (ap-southeast-5)](https://ap-southeast-5.console.aws.amazon.com/lambda/home?region=ap-southeast-5#/functions/scamsense-risk-event?tab=monitor) |
| Alibaba OSS bucket | [`scamsense-demo-risk-events` (ap-southeast-3)](https://oss.console.aliyun.com/bucket/oss-ap-southeast-3/scamsense-demo-risk-events/object) |

---

## 1. Project overview

Scam-call fraud is one of the most damaging financial threats in Malaysia. Scammers
impersonate **PDRM, Bank Negara, banks, customs, delivery companies, and eWallet
support teams**, then pressure victims into transferring money urgently to "avoid
account freezing" or "clear money laundering allegations."

**Fakeout** intercepts the moment **before** the user transfers money:

1. The phone monitors unknown calls.
2. The call is transcribed locally (speech-to-text).
3. A local Qwen 2.5 model analyzes the transcript for scam intent.
4. The phone produces a **risk score + reason codes**.
5. **Only the risk metadata** is sent to the cloud — never the audio or transcript.
6. AWS logs the event, Alibaba Cloud stores an anonymized risk record / enriches it.
7. Touch 'n Go's wallet displays a **critical-scam warning** before the transfer
   completes, blocking the loss.

## 2. Demo workflow

```
Home  →  Incoming Call  →  Live Transcript  →  Local AI Analysis  →
Risk Score  →  Real AWS + Alibaba Cloud Verification  →  TNG Warning  →
Transfer Prevented  →  Dashboard / Architecture
```

Each step has a polished phone-frame UI with smooth Framer Motion transitions.

## 3. What is real vs simulated

| Real | Simulated |
|---|---|
| AWS API Gateway + Lambda + CloudWatch Logs (region `ap-southeast-5`, Malaysia) | Phone call recording |
| Alibaba OSS upload of anonymized risk-event JSON (region `ap-southeast-3`, Kuala Lumpur) | Speech-to-text on device |
| (Optional) Alibaba Function Compute fraud enrichment | Local Qwen 2.5 0.5B / 1.5B inference |
| Frontend → Next.js `/api/test-cloud` → both clouds | Touch 'n Go backend / wallet behavior |
| Privacy enforcement (audio/transcript fields rejected before any cloud call) | Fraud blocking action |

The `Prototype Simulation` label is shown for everything that is mocked.
The cloud screen shows real responses, request IDs, and timestamps for everything
that is real.

## 4. Tech stack

- **Next.js 14** (App Router) · **React 18** · **TypeScript**
- **Tailwind CSS** with a custom risk-color design system
- **Framer Motion** for screen transitions, risk meter, waveform
- **Lucide React** for icons
- **Recharts** for the dashboard chart
- **ali-oss** for server-side OSS uploads
- **AWS** API Gateway HTTP API · Lambda · CloudWatch
- **Alibaba Cloud** OSS (preferred) or Function Compute

## 5. AWS integration

- Endpoint: `POST {AWS_RISK_API_URL}` (e.g. `https://...execute-api.ap-southeast-5.amazonaws.com/risk-event`)
- Lambda function: `fakeout-risk-event` (Node.js 20.x)
- Logs: CloudWatch Logs group `/aws/lambda/fakeout-risk-event` — every Test Cloud
  click writes a `Fakeout risk event:` line with the same `awsRequestId` returned
  to the frontend.

Setup details: [`cloud/aws/README-AWS.md`](./cloud/aws/README-AWS.md).

## 6. Alibaba Cloud integration

Default path is **OSS**, chosen because the FINHACK RAM role has OSS access
in *Recently visited*.

- Bucket: `fakeout-demo-risk-events` (region `oss-ap-southeast-3`).
- Each Test Cloud click uploads an object at `risk-events/{eventId}.json` with
  user metadata `event-id`, `risk-level`, `risk-score` for verification.
- Optional Function Compute path documented for completeness.

Setup details: [`cloud/alibaba/README-ALIBABA.md`](./cloud/alibaba/README-ALIBABA.md).

## 7. Privacy architecture

- **Audio + full transcript stay on the phone.** Never uploaded.
- The frontend only sends risk metadata: `eventId`, `timestamp`, `riskScore`,
  `riskLevel`, `reasonCodes`, `targetWallet` (masked), `amount`, `currency`,
  `audioShared:false`, `transcriptShared:false`, `riskScoreShared:true`.
- The Next.js API route, the Lambda function, and the Function Compute function
  all **reject** any payload containing fields like `audio`, `audioBase64`,
  `transcript`, or `fullTranscript` before any cloud call is made.
- The Cloud Verification screen explicitly displays the privacy state and lets
  the user inspect the exact JSON that was transmitted.

## 8. AI design

Fakeout simulates an **on-device Qwen 2.5** model in two sizes:

| Variant | Use case |
|---|---|
| **Qwen 2.5 0.5B** | Lightweight, runs on older smartphones |
| **Qwen 2.5 1.5B** | Enhanced reasoning, modern phones |

The simulated pipeline mirrors what a real on-device run would do:

1. Load model weights.
2. Tokenize the local transcript.
3. Detect authority impersonation.
4. Detect urgency / financial pressure.
5. Extract risk signals.
6. Compute a deterministic risk score.

The deterministic scorer (in `src/lib/riskEngine.ts`) is fully visible and
testable — judges can trace exactly why the score is 94/100.

| Reason code | Weight |
|---|---|
| Authority impersonation | +25 |
| Money laundering claim | +20 |
| Urgent transfer request | +25 |
| Account freeze threat | +15 |
| Suspicious eWallet recipient | +10 |
| Unknown number | +5 |
| **Cap** | **100** |

## 9. Hackathon judging criteria mapping

### AI & Intelligent Systems
Fakeout uses **simulated local Qwen 2.5 inference** to analyze a scam-call
transcript and detects authority impersonation, urgency, legal threats,
account-freeze threats, and suspicious transfer instructions. The risk engine
is deterministic and explainable. Production drop-in path is documented.

### Technical Implementation
End-to-end prototype with: polished phone-frame mobile UI, realistic 8-step
workflow, deterministic risk engine, **real AWS API Gateway/Lambda/CloudWatch**
integration, **real Alibaba OSS** integration, cloud verification screen with
live request IDs, fraud intelligence dashboard, architecture diagram, and
README docs.

### Multi-Cloud Service Usage
- **AWS**: API Gateway HTTP API → Lambda function `fakeout-risk-event` →
  CloudWatch Logs (real logs visible in `ap-southeast-5` console).
- **Alibaba Cloud**: OSS bucket `fakeout-demo-risk-events` stores anonymized
  risk-event JSON in `oss-ap-southeast-3` (real objects visible in console).
  Function Compute path also implemented as an alternative.

### Impact & Feasibility
Targets the most damaging fraud type for Malaysian eWallet users: high-pressure
scam calls. Privacy-first design enables adoption by elderly, low-income,
underserved, and unbanked communities — exactly the most-targeted demographics.
Local inference works on entry-level Android devices.

### Presentation & Teamwork
Includes guided demo flow with a step indicator, dashboard with live cloud
status, cloud verification screen with copy-payload button, architecture
diagram with "Why this wins" section, and full setup README.

## 10. How to run

```powershell
# Install dependencies
npm install

# Copy env template and fill in real cloud values
copy .env.example .env.local
# Edit .env.local — see sections 5 and 6 above

# Run dev server
npm run dev

# Open
http://localhost:3000           # mobile demo (phone-frame)
http://localhost:3000/dashboard # fraud intelligence console
http://localhost:3000/architecture # architecture + pitch screen
```

## 11. Environment variables

See [`.env.example`](./.env.example).

```bash
# AWS — required for real AWS integration
AWS_RISK_API_URL=
AWS_REGION=ap-southeast-5

# Alibaba OSS — preferred path
ALIBABA_OSS_REGION=oss-ap-southeast-3
ALIBABA_OSS_BUCKET=fakeout-demo-risk-events
ALIBABA_OSS_ACCESS_KEY_ID=
ALIBABA_OSS_ACCESS_KEY_SECRET=

# Alibaba Function Compute — optional alternative
ALIBABA_FRAUD_API_URL=
```

If any cloud env var is missing, the corresponding card on the Cloud Verification
screen shows **Failed (not configured)** with a clear error message — local
demo still works.

## 12. Cloud setup

- AWS: [`cloud/aws/README-AWS.md`](./cloud/aws/README-AWS.md)
- Alibaba: [`cloud/alibaba/README-ALIBABA.md`](./cloud/alibaba/README-ALIBABA.md)
- OSS fallback notes: [`cloud/alibaba/oss-fallback-notes.md`](./cloud/alibaba/oss-fallback-notes.md)

## 13. Future roadmap

- Native Android `CallScreeningService` integration for real call detection
- Real on-device speech-to-text (Whisper.cpp / Vosk for Malay & English)
- Quantized Qwen 2.5 0.5B running locally via ONNX Runtime Mobile
- TNG risk-engine API integration (replacing the simulated wallet warning)
- Crowd-sourced scam-number reputation database
- On-device multilingual scam detection (BM, EN, Mandarin, Cantonese, Tamil)
- Elderly Protection mode with simplified UI
- Family Alert mode (caregiver gets WhatsApp digest of high-risk events)

## License

Prototype for TNG FINHACK 2026.
