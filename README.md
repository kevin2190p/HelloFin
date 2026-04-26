# Fakeout

**Protecting Everyone, Not Just Banks. Your Money Stays Safe.**

FAKEOUT is a mobile application designed to protect Malaysians from elder fraud and scam calls. We empower caregivers and users with real-time alerts and instant control over suspicious transactions, ensuring that money never leaves their hands without verification. The app aims to stand out from its competition by combining AI-powered voice analysis with automated holds, giving users complete peace of mind.

## Features

**Real-time scam detection**  
AI transcribes and detects scam patterns instantly.

**Instant caregiver alerts**  
WhatsApp notifications with one-tap approve or cancel.

**Smart hold & auto-cancel**  
Funds stay safe and auto-return if unverified.

**Caregiver dashboard**  
Live risk view with actions and countdown timer.

**Multi-cloud security**  
Separated systems ensure no single point of failure.

**Fallback detection**  
Uses call, number, and behavior signals when audio is unavailable.

## ⚙️ Technical Architecture

### Core Stack
- **Frontend**: Svelte, SvelteKit, Tailwind CSS, Chart.js  
- **Backend**: FastAPI, Groq‑whisper‑large‑v3 (speech‑to‑text), Hugging Face API (risk detection)  
- **Bot platform**: Telegram Bot API (access token)  
- **Workflow / optional**: n8n (automation)

### ☁️ AWS Integrations
1. **AWS Bedrock** – Claude 3 Haiku scam analyzer  
2. **AWS KMS** – primary Data Encryption Key generator  
3. **AWS Lambda** – optional secondary scorer  

### ☁️ Alibaba Cloud Integrations
1. **Alibaba DashScope (Model Studio)** – Qwen‑Turbo scam analyzer  
2. **Alibaba OSS** – encrypted Data Encryption Key vault  
3. **Alibaba KMS** – second‑layer wrap of the DEK (via OSS‑SSE‑KMS)  

### 📦 Other Dependencies
- `Next.js (App Router)` frontend with React, TypeScript, Tailwind CSS, Framer Motion  
- Next.js server API route as the backend fan‑out layer  
- Firebase / PostgreSQL (configurable)  
- Alibaba OSS (encrypted storage)  

![Screenshot 1](https://drive.google.com/uc?export=view&id=1wxcQoGzXgIAgf3U5DbZbIgC0lqee27Pn)

![Screenshot 2](https://drive.google.com/uc?export=view&id=1dm1afJ38XWoURnaBCzB7sTDH9p9D49m4)

![Screenshot 3](https://drive.google.com/uc?export=view&id=1SLcYfbup_vPl4WH8cFQSiNqcnOKRKdcS)

![Screenshot 4](https://drive.google.com/uc?export=view&id=1HfuY42gvqI0Q2agH-xiItMwmO5iirikN)

![Screenshot 5](https://drive.google.com/uc?export=view&id=1X_BQGtnBvoMyArsEIPFeJq8jPAyftjwQ)


## Videos

<video width="640" height="480" controls>
  <source src="https://drive.google.com/uc?export=download&id=172RgwGpJBYTLuyjxyHXH4cWFEaST-mSN" type="video/mp4">
  Your browser does not support the video tag.
</video>

[Download Video 1](https://drive.google.com/uc?export=download&id=172RgwGpJBYTLuyjxyHXH4cWFEaST-mSN)


<video width="640" height="480" controls>
  <source src="https://drive.google.com/uc?export=download&id=1PQ_k0TqhzEjqubqP4VbxVxYL1Fu2N50F" type="video/mp4">
  Your browser does not support the video tag.
</video>

[Download Video 2](https://drive.google.com/uc?export=download&id=1PQ_k0TqhzEjqubqP4VbxVxYL1Fu2N50F)

## License

MIT License

## Closing

Banks release your money to scammers. FAKEOUT gives it back to you.
