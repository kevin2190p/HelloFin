/**
 * ═══════════════════════════════════════════════════════════
 * OpenClaw – WhatsApp Voice Phishing Interceptor
 * ═══════════════════════════════════════════════════════════
 *
 * Connects to YOUR personal WhatsApp via QR code scan.
 * Monitors incoming messages from watchlisted scam numbers.
 * Forwards voice notes + text to n8n → Jane's backend.
 *
 * Flow:
 *   Scammer sends voice/text → OpenClaw intercepts
 *   → Downloads audio → Forwards to n8n webhook
 *   → n8n sends to FastAPI → Whisper + Risk Scoring
 *
 * TNG Digital FINHACK 2026
 */

import { default as makeWASocket, useMultiFileAuthState, downloadMediaMessage, DisconnectReason } from '@whiskeysockets/baileys';
import pino from 'pino';
import qrcode from 'qrcode-terminal';
import axios from 'axios';
import FormData from 'form-data';
import fs from 'fs';
import path from 'path';
import { config } from 'dotenv';

config({ path: path.resolve('..', '.env') });

// ────────────────────────────────────────────
// Configuration
// ────────────────────────────────────────────
const WATCHLIST = (process.env.WATCHLIST_NUMBERS || '60163569782')
  .split(',')
  .map(n => n.trim().replace(/[^0-9]/g, ''));

const WEBHOOK_URL = process.env.OPENCLAW_WEBHOOK_URL || 'http://localhost:5678/webhook/openclaw-voice';
const AUTH_DIR = process.env.OPENCLAW_AUTH_DIR || 'auth_info_hellofin';
const AUDIO_DIR = path.resolve('..', 'audios');

// Ensure audio directory exists
if (!fs.existsSync(AUDIO_DIR)) fs.mkdirSync(AUDIO_DIR, { recursive: true });

const logger = pino({ level: 'info' });

console.log(`
╔═══════════════════════════════════════════════════╗
║   🛡️  OpenClaw – Voice Phishing Interceptor       ║
║   TNG Digital FINHACK 2026                        ║
╚═══════════════════════════════════════════════════╝

📡 Monitoring numbers: ${WATCHLIST.join(', ')}
🔗 Forwarding to:     ${WEBHOOK_URL}
📁 Audio storage:     ${AUDIO_DIR}
`);

// ────────────────────────────────────────────
// WhatsApp Connection
// ────────────────────────────────────────────
async function startOpenClaw() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger: pino({ level: 'silent' }),
    browser: ['HelloFin Shield', 'Chrome', '120.0'],
  });

  // ── QR Code Display ──
  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('\n📱 Scan this QR code with your WhatsApp:\n');
      qrcode.generate(qr, { small: true });
      console.log('\n⏳ Waiting for scan...\n');
    }

    if (connection === 'close') {
      const reason = lastDisconnect?.error?.output?.statusCode;
      if (reason !== DisconnectReason.loggedOut) {
        console.log('🔄 Reconnecting...');
        startOpenClaw();
      } else {
        console.log('❌ Logged out. Delete auth folder and restart.');
      }
    }

    if (connection === 'open') {
      console.log('✅ Connected to WhatsApp!');
      console.log(`🛡️  Watching for scam messages from: ${WATCHLIST.join(', ')}`);
      console.log('────────────────────────────────────────────\n');
    }
  });

  sock.ev.on('creds.update', saveCreds);

  // ── Message Handler ──
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue;

      const sender = msg.key.remoteJid?.replace('@s.whatsapp.net', '') || '';
      const isWatchlisted = WATCHLIST.some(w => sender.includes(w));

      if (!isWatchlisted) continue;

      const timestamp = msg.messageTimestamp?.toString() || Date.now().toString();
      const pushName = msg.pushName || 'Unknown';

      console.log(`\n🚨 ═══ WATCHLISTED MESSAGE DETECTED ═══`);
      console.log(`   From:      +${sender} (${pushName})`);
      console.log(`   Time:      ${new Date(parseInt(timestamp) * 1000).toLocaleString()}`);

      // ── Handle Voice Notes ──
      if (msg.message?.audioMessage) {
        console.log(`   Type:      🎤 VOICE NOTE`);
        console.log(`   Duration:  ${msg.message.audioMessage.seconds}s`);
        console.log(`   MIME:      ${msg.message.audioMessage.mimetype}`);

        try {
          const buffer = await downloadMediaMessage(msg, 'buffer', {}, {
            logger,
            reuploadRequest: sock.updateMediaMessage,
          });

          const filename = `${sender}_${timestamp}.ogg`;
          const filepath = path.join(AUDIO_DIR, filename);
          fs.writeFileSync(filepath, buffer);
          console.log(`   💾 Saved:   ${filepath}`);

          await forwardToN8N({
            type: 'voice',
            sender,
            timestamp,
            push_name: pushName,
            audio_path: filepath,
            audio_buffer: buffer,
            duration: msg.message.audioMessage.seconds,
            mime_type: msg.message.audioMessage.mimetype,
          });
        } catch (err) {
          console.error(`   ❌ Download failed:`, err.message);
        }
      }

      // ── Handle Text Messages ──
      const textContent = msg.message?.conversation
        || msg.message?.extendedTextMessage?.text;

      if (textContent) {
        console.log(`   Type:      💬 TEXT MESSAGE`);
        console.log(`   Content:   "${textContent.substring(0, 100)}..."`);

        await forwardToN8N({
          type: 'text',
          sender,
          timestamp,
          push_name: pushName,
          text: textContent,
        });
      }

      console.log(`   ═══════════════════════════════════\n`);
    }
  });
}

// ────────────────────────────────────────────
// Forward to n8n Webhook
// ────────────────────────────────────────────
async function forwardToN8N(data) {
  const MAX_RETRIES = 3;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      if (data.type === 'voice' && data.audio_buffer) {
        const form = new FormData();
        form.append('audio', data.audio_buffer, {
          filename: `${data.sender}_${data.timestamp}.ogg`,
          contentType: data.mime_type || 'audio/ogg',
        });
        form.append('sender_phone', data.sender);
        form.append('timestamp', data.timestamp);
        form.append('push_name', data.push_name);
        form.append('message_type', 'voice');
        form.append('duration', String(data.duration || 0));

        const res = await axios.post(WEBHOOK_URL, form, {
          headers: form.getHeaders(),
          timeout: 30000,
        });
        console.log(`   📤 Forwarded voice to n8n (${res.status})`);
      } else if (data.type === 'text') {
        const res = await axios.post(WEBHOOK_URL, {
          sender_phone: data.sender,
          timestamp: data.timestamp,
          push_name: data.push_name,
          message_type: 'text',
          text: data.text,
        }, { timeout: 10000 });
        console.log(`   📤 Forwarded text to n8n (${res.status})`);
      }
      return;
    } catch (err) {
      console.error(`   ⚠️  Forward attempt ${attempt}/${MAX_RETRIES} failed:`, err.message);
      if (attempt < MAX_RETRIES) await sleep(2000);
    }
  }
  console.error(`   ❌ All ${MAX_RETRIES} forward attempts failed!`);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Start ──
startOpenClaw().catch(console.error);
