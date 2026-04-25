# FAKEOUT

**Protecting Everyone, Not Just Banks. Your Money Stays Safe.**

FAKEOUT is a mobile application designed to protect Malaysians from elder fraud and scam calls. We empower caregivers and users with real-time alerts and instant control over suspicious transactions, ensuring that money never leaves their hands without verification. The app aims to stand out from its competition by combining AI-powered voice analysis with automated holds, giving users complete peace of mind.

## Features

**Detect scam calls and voice notes in real-time:**
- AI-powered voice analysis using OpenAI Whisper for instant speech-to-text transcription.
- Risk scoring algorithm that identifies scam keywords and urgency patterns.
- Automatic flagging of suspicious transactions within seconds.

**Receive instant caregiver alerts via WhatsApp:**
- Caregivers are notified immediately when suspicious activity is detected.
- One-click approval or cancellation directly from WhatsApp.
- Real-time dashboard for complete transaction overview.

**Smart hold and auto-cancel protection:**
- Suspicious transactions display "Processing" to trap scammers psychologically.
- Money is held securely in Alibaba vault during verification window.
- Auto-cancel after 60 minutes if user doesn't respond—money returns safely.
- User maintains full control throughout the entire process.

**Caregiver dashboard with real-time monitoring:**
- View all flagged transactions with risk scores and detected keywords.
- Approve or cancel transactions with a single click.
- Monitor processing timers and auto-cancel countdowns.
- Complete audit trail for compliance and record-keeping.

**Cross-cloud security and encryption:**
- Alibaba OSS stores encrypted audio and real balance state.
- AWS Lambda handles deception layer and risk trigger evaluation.
- AES-256 encryption for all sensitive data.
- No single point of failure—multi-cloud protection.

**Fallback detection methods:**
- Call duration analysis for calls without voice consent.
- Unknown number detection and location pattern analysis.
- Behavioral scoring from transaction history.

## Dependencies used

- **Frontend**: Svelte, SvelteKit, Tailwind CSS, Chart.js
- **Backend**: FastAPI, OpenAI Whisper, Claude AI
- **Automation**: n8n, OpenClaw
- **Cloud**: AWS Lambda, Alibaba OSS, Alibaba KMS
- **Communications**: Meta WhatsApp API
- **Database**: Firebase/PostgreSQL (configurable)

## Screenshots

![Screenshot 1](https://github.com/YOUR_USERNAME/fakeout/releases/download/v1.0-images/FK1.jpeg)

*Caregiver dashboard showing real-time fraud alerts with risk scores*

---

![Screenshot 2](https://github.com/YOUR_USERNAME/fakeout/releases/download/v1.0-images/FK2.jpeg)

*High-risk alert notification with one-click approve/cancel buttons*

---

![Screenshot 3](https://github.com/YOUR_USERNAME/fakeout/releases/download/v1.0-images/FK3.jpeg)

*Multi-cloud setup: Voice Analysis → Risk Scoring → Multi-Cloud Hold*

---
![Screenshot 4](https://github.com/YOUR_USERNAME/fakeout/releases/download/v1.0-images/FK4.jpeg)

*3-Stage Protection: Detection → Analysis → Trap*

---

![Screenshot 5](https://github.com/YOUR_USERNAME/fakeout/releases/download/v1.0-images/FK5.jpeg)

*Transaction processing with auto-cancel safety feature*

## Videos
[![FAKEOUT Demo 1](https://img.youtube.com/vi/YOUR_VIDEO_ID/maxresdefault.jpg)](https://youtube.com/shorts/AD6FtyKAbxI?feature=share)
[![FAKEOUT Demo 2](https://img.youtube.com/vi/YOUR_VIDEO_ID/maxresdefault.jpg)](https://youtube.com/shorts/MwPh_bhscX0)

## License

MIT License

## Closing

Banks release your money to scammers. FAKEOUT gives it back to you.
