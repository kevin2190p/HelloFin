<script>
  import { onMount, onDestroy } from 'svelte';

  export let demoMode = false; // set true for hardcoded demo

  // ── State ─────────────────────────────────────────────────
  let messages = [];
  let scanning = false;
  let chatBottom;
  let pollInterval;

  const SCAMMER_NAME  = 'Unknown (+60163569782)';
  const SCAMMER_PHONE = '60163569782';
  const MY_NAME       = 'You (Kevin)';

  // ── Demo Script (hardcoded backup) ────────────────────────
  const DEMO_SCRIPT = [
    { from: 'scammer', type: 'text', delay: 1000,
      text: 'Selamat petang. Saya dari Jabatan Kastam Diraja Malaysia. Bungkusan anda yang mengandungi barang terlarang telah ditahan di lapangan terbang.' },
    { from: 'scammer', type: 'text', delay: 5000,
      text: 'Kes jenayah serius telah dibuka terhadap anda. Anda mungkin akan ditangkap dalam masa 2 jam jika tidak bayar denda RM 4,800 sekarang.' },
    { from: 'me', type: 'text', delay: 7500, text: 'Apa? Saya tidak pesan apa-apa...' },
    { from: 'scammer', type: 'text', delay: 9000,
      text: 'Transfer terus ke akaun selamat kami: Maybank 5621 4489 0012. Ini urgent! Jangan beritahu sesiapa.' },
    { from: 'scammer', type: 'voice', delay: 12000, duration: 18,
      text: 'Hello this is Inspector Rajan from PDRM. We have a warrant for your arrest. To avoid arrest you must transfer five thousand ringgit to the safe account immediately. Do not tell your family. This is confidential police operation.' },
  ];

  // ── Risk level helpers ─────────────────────────────────────
  function riskClass(score) {
    if (score >= 80) return 'critical';
    if (score >= 50) return 'warning';
    return 'safe';
  }

  function riskEmoji(score) {
    if (score >= 80) return '🚨';
    if (score >= 50) return '⚠️';
    return '✅';
  }

  // ── Scroll to bottom ───────────────────────────────────────
  function scrollBottom() {
    setTimeout(() => chatBottom?.scrollIntoView({ behavior: 'smooth' }), 60);
  }

  // ── Real-time polling (live mode) ─────────────────────────
  async function pollMessages() {
    try {
      const res = await fetch('http://localhost:8000/chat/messages');
      if (!res.ok) return;
      const data = await res.json();
      messages = data;
      scrollBottom();
    } catch (_) { /* backend offline — silent */ }
  }

  // ── Demo mode playback ────────────────────────────────────
  function runDemo() {
    messages = [];
    DEMO_SCRIPT.forEach((step) => {
      setTimeout(() => {
        const msg = {
          id: Math.random().toString(36).slice(2),
          from: step.from,
          type: step.type,
          text: step.text,
          duration: step.duration || 0,
          time: new Date().toLocaleTimeString('en-MY', { hour: '2-digit', minute: '2-digit' }),
          scanning: step.from === 'scammer',
          risk_score: null,
          risk_level: null,
          llm_label: null,
        };
        messages = [...messages, msg];
        scrollBottom();

        // Simulate detection pipeline after 2s
        if (step.from === 'scammer') {
          setTimeout(() => {
            const score = step.type === 'voice' ? 97 : (
              step.text.includes('Transfer') ? 95 :
              step.text.includes('warrant') || step.text.includes('tangkap') ? 88 : 72
            );
            messages = messages.map(m =>
              m.id === msg.id
                ? { ...m, scanning: false, risk_score: score,
                    risk_level: score >= 80 ? 'HIGH' : 'MEDIUM',
                    llm_label: score >= 80 ? 'Macau Scam' : 'Suspicious' }
                : m
            );
            scrollBottom();
          }, 2200);
        }
      }, step.delay);
    });
  }

  onMount(() => {
    if (demoMode) {
      runDemo();
    } else {
      pollMessages();
      pollInterval = setInterval(pollMessages, 3000);
    }
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });
</script>

<!-- ═══════════════════════════ WhatsApp Widget ═══════════════════════════ -->
<div class="wa-shell">

  <!-- Header -->
  <div class="wa-header">
    <div class="wa-avatar">
      <span>👤</span>
    </div>
    <div class="wa-contact">
      <div class="wa-name">{SCAMMER_NAME}</div>
      <div class="wa-sub">
        {#if demoMode}
          <span class="demo-tag">DEMO MODE</span>
        {:else}
          <span class="live-dot"></span> Live Monitoring
        {/if}
      </div>
    </div>
    <div class="wa-icons">
      <span>📹</span>
      <span>📞</span>
      <span>⋮</span>
    </div>
  </div>

  <!-- Chat Body -->
  <div class="wa-body">
    <div class="wa-date-chip">Today</div>

    {#each messages as msg (msg.id)}
      <div class="wa-msg-row" class:mine={msg.from === 'me'} class:theirs={msg.from === 'scammer'}>

        <!-- Message Bubble -->
        <div class="wa-bubble" class:mine={msg.from === 'me'} class:theirs={msg.from === 'scammer'}
          class:risk-critical={msg.risk_level === 'HIGH'}
          class:risk-warning={msg.risk_level === 'MEDIUM'}>

          <!-- Voice Note UI -->
          {#if msg.type === 'voice'}
            <div class="wa-voice">
              <div class="wa-voice-avatar">
                {msg.from === 'me' ? '🧑' : '👤'}
              </div>
              <div class="wa-voice-body">
                <div class="wa-waveform">
                  {#each Array(20) as _, i}
                    <div class="wa-wave-bar" style="height: {12 + Math.sin(i * 0.8) * 10}px;
                      animation-delay: {i * 0.05}s"></div>
                  {/each}
                </div>
                <div class="wa-voice-meta">
                  <span>🎤 {msg.duration}s</span>
                  <span class="wa-time">{msg.time}</span>
                </div>
              </div>
            </div>

          <!-- Text Message UI -->
          {:else}
            <p class="wa-text">{msg.text}</p>
            <span class="wa-time">{msg.time} {msg.from === 'me' ? '✓✓' : ''}</span>
          {/if}

          <!-- Scanning Indicator -->
          {#if msg.scanning}
            <div class="wa-scanning">
              <div class="scan-dots">
                <span></span><span></span><span></span>
              </div>
              <span class="scan-text">AI Scanning…</span>
            </div>
          {/if}

          <!-- Risk Verdict Badge -->
          {#if msg.risk_score !== null && !msg.scanning}
            <div class="wa-risk-badge {riskClass(msg.risk_score)}">
              <span class="risk-emoji">{riskEmoji(msg.risk_score)}</span>
              <div class="risk-info">
                <span class="risk-score">{msg.risk_score}/100</span>
                <span class="risk-type">{msg.llm_label || msg.risk_level}</span>
              </div>
            </div>
          {/if}
        </div>
      </div>
    {/each}

    {#if messages.length === 0}
      <div class="wa-empty">
        <div class="wa-empty-icon">🛡️</div>
        <p>Monitoring for scam messages from<br><strong>+60163569782</strong></p>
        {#if demoMode}
          <p class="wa-empty-sub">Demo starting…</p>
        {:else}
          <p class="wa-empty-sub">Will detect automatically when scammer messages you</p>
        {/if}
      </div>
    {/if}

    <div bind:this={chatBottom}></div>
  </div>

  <!-- Input Bar (decorative) -->
  <div class="wa-input-bar">
    <div class="wa-input-emoji">😊</div>
    <div class="wa-input-field">Message</div>
    <div class="wa-input-attach">📎</div>
    <div class="wa-input-mic">🎤</div>
  </div>
</div>

<!-- Demo Replay Button -->
{#if demoMode}
  <button class="replay-btn" on:click={runDemo}>↺ Replay Demo</button>
{/if}

<style>
  /* ═══ WhatsApp Shell ═══ */
  .wa-shell {
    width: 100%;
    max-width: 420px;
    height: 580px;
    border-radius: 20px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    background: #0b141a;
    box-shadow: 0 24px 80px rgba(0,0,0,.6);
    border: 1px solid rgba(255,255,255,.06);
    font-family: -apple-system, 'Segoe UI', sans-serif;
  }

  /* ═══ Header ═══ */
  .wa-header {
    background: #1f2c34;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid rgba(255,255,255,.05);
    flex-shrink: 0;
  }
  .wa-avatar {
    width: 40px; height: 40px; border-radius: 50%;
    background: #2a3942; display: flex; align-items: center;
    justify-content: center; font-size: 1.2rem; flex-shrink: 0;
  }
  .wa-contact { flex: 1; }
  .wa-name { font-size: .88rem; font-weight: 600; color: #e9edef; }
  .wa-sub { font-size: .72rem; color: #8696a0; display: flex; align-items: center; gap: 5px; margin-top: 2px; }
  .live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #25d366; animation: pulse 1.5s infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  .demo-tag {
    background: rgba(251,191,36,.2); color: #fbbf24;
    padding: 1px 8px; border-radius: 8px; font-size: .65rem; font-weight: 700;
  }
  .wa-icons { display: flex; gap: 18px; color: #8696a0; font-size: 1.1rem; cursor: pointer; }

  /* ═══ Chat Body ═══ */
  .wa-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px 12px 4px;
    background: #0b141a;
    background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23182229' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .wa-body::-webkit-scrollbar { width: 4px; }
  .wa-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,.1); border-radius: 2px; }

  .wa-date-chip {
    text-align: center; font-size: .7rem; color: #8696a0;
    background: rgba(17,27,33,.8); border-radius: 8px;
    padding: 3px 10px; margin: 4px auto 8px; width: fit-content;
  }

  /* ═══ Message Rows ═══ */
  .wa-msg-row {
    display: flex;
    margin-bottom: 2px;
    animation: msgIn .25s ease-out;
  }
  @keyframes msgIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
  .wa-msg-row.mine { justify-content: flex-end; }
  .wa-msg-row.theirs { justify-content: flex-start; }

  /* ═══ Bubbles ═══ */
  .wa-bubble {
    max-width: 78%;
    border-radius: 8px;
    padding: 7px 10px 5px;
    position: relative;
    transition: box-shadow .3s;
  }
  .wa-bubble.mine {
    background: #005c4b;
    border-top-right-radius: 2px;
    color: #e9edef;
  }
  .wa-bubble.theirs {
    background: #1f2c34;
    border-top-left-radius: 2px;
    color: #e9edef;
  }
  .wa-bubble.risk-critical {
    background: rgba(239,68,68,.15) !important;
    border: 1px solid rgba(239,68,68,.4);
    box-shadow: 0 0 20px rgba(239,68,68,.2);
  }
  .wa-bubble.risk-warning {
    background: rgba(251,191,36,.1) !important;
    border: 1px solid rgba(251,191,36,.3);
  }

  .wa-text { font-size: .88rem; line-height: 1.45; margin-bottom: 2px; word-break: break-word; }
  .wa-time { font-size: .65rem; color: #8696a0; float: right; margin-left: 8px; margin-top: 2px; }

  /* ═══ Voice Note ═══ */
  .wa-voice {
    display: flex; align-items: center; gap: 10px; padding: 4px 0;
  }
  .wa-voice-avatar {
    width: 36px; height: 36px; border-radius: 50%;
    background: rgba(255,255,255,.1); display: flex;
    align-items: center; justify-content: center; flex-shrink: 0; font-size: 1.1rem;
  }
  .wa-voice-body { flex: 1; }
  .wa-waveform {
    display: flex; align-items: center; gap: 2px; height: 28px; margin-bottom: 4px;
  }
  .wa-wave-bar {
    width: 3px; background: #25d366; border-radius: 2px;
    animation: wave 1.2s ease-in-out infinite alternate;
  }
  @keyframes wave { 0%{transform:scaleY(.4)} 100%{transform:scaleY(1)} }
  .wa-voice-meta { display: flex; justify-content: space-between; font-size: .68rem; color: #8696a0; }

  /* ═══ Scanning State ═══ */
  .wa-scanning {
    display: flex; align-items: center; gap: 8px;
    margin-top: 6px; padding: 5px 8px; border-radius: 6px;
    background: rgba(99,102,241,.15); border: 1px solid rgba(99,102,241,.3);
  }
  .scan-dots { display: flex; gap: 4px; }
  .scan-dots span {
    width: 5px; height: 5px; border-radius: 50%; background: #818cf8;
    animation: scanPulse 1s ease-in-out infinite;
  }
  .scan-dots span:nth-child(2) { animation-delay: .2s; }
  .scan-dots span:nth-child(3) { animation-delay: .4s; }
  @keyframes scanPulse { 0%,100%{opacity:.3;transform:scale(.8)} 50%{opacity:1;transform:scale(1)} }
  .scan-text { font-size: .68rem; color: #818cf8; font-weight: 600; }

  /* ═══ Risk Badge ═══ */
  .wa-risk-badge {
    display: flex; align-items: center; gap: 8px;
    margin-top: 7px; padding: 6px 10px; border-radius: 8px;
    animation: badgeIn .4s ease-out;
  }
  @keyframes badgeIn { from{opacity:0;transform:scale(.9)} to{opacity:1;transform:scale(1)} }
  .wa-risk-badge.critical { background: rgba(239,68,68,.2); border: 1px solid rgba(239,68,68,.5); }
  .wa-risk-badge.warning  { background: rgba(251,191,36,.15); border: 1px solid rgba(251,191,36,.4); }
  .wa-risk-badge.safe     { background: rgba(37,211,102,.1); border: 1px solid rgba(37,211,102,.3); }
  .risk-emoji { font-size: 1.1rem; }
  .risk-info { display: flex; flex-direction: column; }
  .risk-score { font-size: .78rem; font-weight: 800; color: #f1f5f9; }
  .risk-type { font-size: .65rem; color: #94a3b8; text-transform: uppercase; letter-spacing: .05em; }

  /* ═══ Empty State ═══ */
  .wa-empty {
    text-align: center; padding: 40px 20px; color: #4a5568;
  }
  .wa-empty-icon { font-size: 2.5rem; margin-bottom: 12px; }
  .wa-empty p { font-size: .82rem; line-height: 1.6; }
  .wa-empty strong { color: #ef4444; }
  .wa-empty-sub { font-size: .72rem; margin-top: 8px; color: #374151; }

  /* ═══ Input Bar ═══ */
  .wa-input-bar {
    background: #1f2c34;
    padding: 8px 12px;
    display: flex; align-items: center; gap: 8px;
    border-top: 1px solid rgba(255,255,255,.04);
    flex-shrink: 0;
  }
  .wa-input-emoji, .wa-input-attach, .wa-input-mic { font-size: 1.2rem; color: #8696a0; cursor: pointer; }
  .wa-input-field {
    flex: 1; background: #2a3942; border-radius: 24px;
    padding: 8px 16px; font-size: .85rem; color: #8696a0;
  }
  .wa-input-mic {
    width: 40px; height: 40px; border-radius: 50%;
    background: #25d366; display: flex; align-items: center;
    justify-content: center; font-size: 1rem; color: white;
  }

  /* ═══ Replay Button ═══ */
  .replay-btn {
    display: block; margin: 12px auto 0;
    background: rgba(37,211,102,.15); color: #25d366;
    border: 1px solid rgba(37,211,102,.4); border-radius: 20px;
    padding: 8px 24px; font-size: .8rem; font-weight: 700;
    cursor: pointer; transition: all .2s;
  }
  .replay-btn:hover { background: rgba(37,211,102,.25); transform: translateY(-1px); }
</style>
