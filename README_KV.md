# 📱 KV's Setup Guide – WhatsApp Voice Note → n8n → Jane's Backend

> **Your job:** Receive WhatsApp voice notes and forward them to Jane's FastAPI backend for phishing analysis.
> **Time required:** ~30 minutes.

---

## 🗺️ How It Works

```
User sends voice note on WhatsApp
        │
        ▼
Meta Cloud API delivers webhook (POST)
        │
        ▼
┌──────────────────────────────────┐
│  n8n Workflow (your part)        │
│                                  │
│  1. Receive POST from Meta       │
│  2. Extract audio media_id       │
│  3. GET media URL from Graph API │
│  4. Download .ogg audio file     │
│  5. POST to Jane's backend       │
└──────────────────────────────────┘
        │
        ▼
Jane's FastAPI → Whisper → Risk Score → Hold/Clear
```

---

## 📁 Files You Own

| File | Purpose |
|------|---------|
| `n8n/voice_phishing_workflow.json` | Main workflow – processes voice notes |
| `n8n/webhook_verify.json` | One-time webhook verification with Meta |

---

## 🚀 Step-by-Step Setup

### Step 1: Install n8n locally

```bash
# Option A: npm (recommended)
npm install -g n8n
n8n start

# Option B: npx (no global install)
npx n8n
```

n8n opens at **http://localhost:5678**. Create an account when prompted.

### Step 2: Expose n8n with ngrok

Meta needs a **public HTTPS URL** to send webhooks. Use ngrok:

```bash
# Install ngrok (if you don't have it)
brew install ngrok

# Expose n8n's port
ngrok http 5678
```

You'll see something like:
```
Forwarding  https://abc123.ngrok-free.app → http://localhost:5678
```

**Copy that `https://...ngrok-free.app` URL.** You'll need it in Step 4.

> ⚠️ Free ngrok URLs change every restart. Keep ngrok running during development.

### Step 3: Set Up Meta WhatsApp Cloud API

1. Go to [developers.facebook.com](https://developers.facebook.com) and log in.
2. Click **My Apps** → **Create App** → Choose **Business** → name it `HelloFin`.
3. In the app dashboard, click **Add Product** → find **WhatsApp** → **Set Up**.
4. Under **WhatsApp > API Setup**, you'll see:
   - **Temporary Access Token** – copy this (valid 24h)
   - **Phone Number ID** – copy this
   - **WhatsApp Business Account ID** – copy this

5. Save these in your `.env`:
   ```
   META_APP_ID=<from app dashboard header>
   META_APP_SECRET=<App Settings > Basic > App Secret>
   WHATSAPP_PHONE_NUMBER_ID=<from Step 4>
   WHATSAPP_ACCESS_TOKEN=<temporary token from Step 4>
   WHATSAPP_VERIFY_TOKEN=hellofin-webhook-verify-2026
   ```

### Step 4: Configure the Webhook in Meta

1. In the Meta dashboard, go to **WhatsApp > Configuration**.
2. Click **Edit** next to Webhook.
3. Enter:
   - **Callback URL:** `https://abc123.ngrok-free.app/webhook/whatsapp`
     (replace with YOUR ngrok URL)
   - **Verify Token:** `hellofin-webhook-verify-2026`
4. **Before clicking Verify** → go to Step 5 first!

### Step 5: Import & Activate the Verification Workflow

1. In n8n (http://localhost:5678), go to **Workflows**.
2. Click **⋮** (menu) → **Import from File**.
3. Select `n8n/webhook_verify.json`.
4. Click **Save**, then toggle **Active** (top-right) to ON.
5. Now go back to Meta and click **Verify and Save**.
   - Meta sends a GET request → n8n returns the challenge → ✅ verified!
6. After verification succeeds, you can **deactivate** this workflow.

### Step 6: Subscribe to Messages

Still in Meta's **WhatsApp > Configuration**:
1. Under **Webhook fields**, click **Manage**.
2. Check the box for **`messages`**.
3. Click **Done**.

### Step 7: Create n8n Credentials

1. In n8n, go to **Settings** (gear icon) → **Credentials**.
2. Click **Add Credential** → search for **Header Auth**.
3. Configure:
   - **Name:** `Meta WhatsApp Token`
   - **Header Name:** `Authorization`
   - **Header Value:** `Bearer <YOUR_WHATSAPP_ACCESS_TOKEN>`
     (paste the token from Step 3, with the word `Bearer` before it)
4. Click **Save**.

### Step 8: Import & Activate the Main Workflow

1. In n8n, import `n8n/voice_phishing_workflow.json`.
2. Open the workflow. You'll see n8n asking to map credentials:
   - For **"Get Media URL"** and **"Download Audio"** nodes → select **Meta WhatsApp Token**.
3. **Edit the "Forward to Jane" node:**
   - If Jane's backend runs locally: change URL to `http://localhost:8000/webhook/whatsapp-voice`
   - If using Docker: keep as `http://jane-backend:8000/webhook/whatsapp-voice`
   - If Jane is on another machine: use her IP/hostname
4. Click **Save**, then toggle **Active** to ON.

### Step 9: Test It!

#### Option A: Send a real voice note
1. Open WhatsApp on your phone.
2. Add the **test phone number** shown in Meta's API Setup page to your contacts.
3. Send a voice note to that number.
4. Watch n8n's **Executions** tab – you should see the workflow run.

#### Option B: Use Meta's Graph API Explorer
1. Go to [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer).
2. This is harder for audio – Option A is recommended.

#### Option C: Use curl to simulate
```bash
# Simulate a Meta webhook POST (for testing without WhatsApp)
curl -X POST http://localhost:5678/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "YOUR_WABA_ID",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "metadata": {
            "display_phone_number": "601234567890",
            "phone_number_id": "YOUR_PHONE_NUMBER_ID"
          },
          "messages": [{
            "from": "601187654321",
            "id": "wamid.test123",
            "timestamp": "1714000000",
            "type": "audio",
            "audio": {
              "mime_type": "audio/ogg; codecs=opus",
              "sha256": "abc123",
              "id": "MEDIA_ID_HERE"
            }
          }]
        },
        "field": "messages"
      }]
    }]
  }'
```

> ⚠️ The curl test will fail at "Get Media URL" because the MEDIA_ID is fake.
> Use it to verify the webhook receives data and extraction works.

---

## 🔌 Connecting to Jane's Backend

Jane's backend expects this POST to `/webhook/whatsapp-voice`:

| Field | Type | Description |
|-------|------|-------------|
| `audio` | file (binary) | The voice note `.ogg` file |
| `sender_phone` | string | Phone number of the sender |
| `is_new_payee` | string | `"true"` or `"false"` |
| `transaction_amount` | string | Amount in MYR (default `"0"`) |

The n8n workflow sends all of these automatically.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| Meta says "Callback URL not reachable" | Make sure ngrok is running AND the verification workflow is active |
| n8n shows "credential not found" | Re-map the "Meta WhatsApp Token" credential in each HTTP Request node |
| "Forward to Jane" fails | Check Jane's backend is running on the correct host/port |
| No executions showing up | Ensure the main workflow is **Active** (green toggle) |
| ngrok URL changed | Update the Callback URL in Meta's webhook config |
| Token expired (24h) | Get a new temporary token from Meta, or set up a System User for a permanent token |

---

## 📋 Quick Reference

| Item | Value |
|------|-------|
| n8n URL | http://localhost:5678 |
| Webhook path (production) | `/webhook/whatsapp` |
| Webhook path (test mode) | `/webhook-test/whatsapp` |
| Verify token | `hellofin-webhook-verify-2026` |
| Jane's endpoint | `http://localhost:8000/webhook/whatsapp-voice` |
| FastAPI docs | http://localhost:8000/docs |

---

**Questions? Ping KV in the group chat.** 🤙
