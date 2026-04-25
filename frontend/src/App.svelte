<script>
  import { onMount, onDestroy } from 'svelte';
  import { startPolling, handleApprove, handleCancel, formatTime, riskColor } from './lib/caregiverDashboard.js';
  import { healthCheck } from './lib/api.js';
  import WhatsAppWidget from './lib/WhatsAppWidget.svelte';

  let alerts = [];
  let error = null;
  let stopPolling;
  let backendOnline = false;
  let now = Date.now();
  let actionLoading = {};
  let actionResult = {};
  let demoMode = false;
  let activeTab = 'dashboard'; // 'dashboard' | 'whatsapp'
  let injectText = '';
  let injectLoading = false;
  let injectResult = null;

  async function injectMessage() {
    if (!injectText.trim()) return;
    injectLoading = true;
    injectResult = null;
    try {
      const res = await fetch('http://localhost:8000/chat/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender_phone: '60163569782', text: injectText, message_type: 'text' }),
      });
      injectResult = await res.json();
    } catch (e) {
      injectResult = { risk_score: 0, status: 'error' };
    }
    injectLoading = false;
  }

  // Tick every second for countdown timers
  let ticker;

  onMount(() => {
    stopPolling = startPolling((data, err) => {
      alerts = data;
      error = err;
    });
    ticker = setInterval(() => { now = Date.now(); }, 1000);
    healthCheck().then(() => backendOnline = true).catch(() => backendOnline = false);
  });

  onDestroy(() => {
    if (stopPolling) stopPolling();
    if (ticker) clearInterval(ticker);
  });

  function countdown(ts) {
    if (!ts) return '—';
    const expire = (ts + 600) * 1000;
    const diff = Math.max(0, Math.floor((expire - now) / 1000));
    const m = Math.floor(diff / 60);
    const s = diff % 60;
    return diff <= 0 ? 'EXPIRED' : `${m}:${s.toString().padStart(2, '0')}`;
  }

  async function onApprove(txnId) {
    actionLoading[txnId] = 'approve';
    try {
      const res = await handleApprove(txnId);
      actionResult[txnId] = { type: 'success', msg: res.message };
    } catch (e) {
      actionResult[txnId] = { type: 'error', msg: e.message };
    }
    actionLoading[txnId] = null;
  }

  async function onCancel(txnId) {
    actionLoading[txnId] = 'cancel';
    try {
      const res = await handleCancel(txnId);
      actionResult[txnId] = { type: 'success', msg: res.message };
    } catch (e) {
      actionResult[txnId] = { type: 'error', msg: e.message };
    }
    actionLoading[txnId] = null;
  }

  $: pendingAlerts = alerts.filter(a => a.status === 'held' || a.status === 'pending');
  $: resolvedAlerts = alerts.filter(a => a.status === 'approved' || a.status === 'cancelled');
</script>

<main>
  <!-- ─── Animated Background ─── -->
  <div class="bg-grid"></div>
  <div class="bg-glow glow-1"></div>
  <div class="bg-glow glow-2"></div>

  <!-- ─── Header ─── -->
  <header>
    <div class="header-inner">
      <div class="logo-group">
        <div class="logo-icon">
          <svg viewBox="0 0 40 40" fill="none">
            <circle cx="20" cy="20" r="18" stroke="url(#g1)" stroke-width="2.5"/>
            <path d="M14 20 L18 24 L26 16" stroke="url(#g1)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <defs><linearGradient id="g1" x1="0" y1="0" x2="40" y2="40"><stop stop-color="#6EE7B7"/><stop offset="1" stop-color="#3B82F6"/></linearGradient></defs>
          </svg>
        </div>
        <div>
          <h1>HelloFin<span class="accent">Shield</span></h1>
          <p class="subtitle">Voice Phishing Detection • Caregiver Dashboard</p>
        </div>
      </div>
      <div class="status-group">
        <div class="status-badge" class:online={backendOnline} class:offline={!backendOnline}>
          <span class="dot"></span>
          {backendOnline ? 'System Online' : 'Connecting...'}
        </div>
        <div class="live-badge">
          <span class="pulse-dot"></span>
          LIVE
        </div>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="tab-nav">
      <button class="tab-btn" class:active={activeTab === 'dashboard'} on:click={() => activeTab = 'dashboard'}>
        🛡️ Alert Dashboard
      </button>
      <button class="tab-btn" class:active={activeTab === 'whatsapp'} on:click={() => activeTab = 'whatsapp'}>
        💬 WhatsApp Monitor
      </button>
      {#if activeTab === 'whatsapp'}
        <button class="demo-toggle" class:demo-on={demoMode} on:click={() => demoMode = !demoMode}>
          {demoMode ? '🔴 DEMO MODE ON' : '⚡ Live Mode'}
        </button>
      {/if}
    </div>
  </header>

  <!-- ─── WhatsApp Tab ─── -->
  {#if activeTab === 'whatsapp'}
    <section class="wa-section">
      <div class="wa-panel-left">
        <h2 class="section-title">💬 Intercepted Conversation</h2>
        <p class="wa-caption">
          {demoMode
            ? '🎬 Hardcoded demo — playing pre-scripted scam scenario'
            : '📡 Live — messages from +60163569782 appear here in real-time'}
        </p>
        {#key demoMode}
          <WhatsAppWidget demoMode={demoMode} />
        {/key}
      </div>
      <div class="wa-panel-right">
        <h2 class="section-title">🧠 Detection Engine</h2>
        <div class="engine-card">
          <div class="engine-row">
            <span class="engine-label">STT Engine</span>
            <span class="engine-val green">Groq Whisper large-v3</span>
          </div>
          <div class="engine-row">
            <span class="engine-label">Text Analysis</span>
            <span class="engine-val green">Qwen3-32B via Groq</span>
          </div>
          <div class="engine-row">
            <span class="engine-label">Keyword Engine</span>
            <span class="engine-val green">200+ Malaysian phrases</span>
          </div>
          <div class="engine-row">
            <span class="engine-label">Score Fusion</span>
            <span class="engine-val green">35% KW + 65% LLM</span>
          </div>
          <div class="engine-row">
            <span class="engine-label">Languages</span>
            <span class="engine-val">BM · EN · Manglish · 中文</span>
          </div>
          <div class="engine-row">
            <span class="engine-label">Watchlist</span>
            <span class="engine-val red">+60163569782</span>
          </div>
        </div>

        <h2 class="section-title" style="margin-top:24px">🎯 Detected Scam Types</h2>
        <div class="scam-types">
          {#each ['Macau Scam','Parcel Scam','Love Scam','Investment Scam','LHDN Scam','Authority Impersonation'] as s}
            <span class="scam-chip">{s}</span>
          {/each}
        </div>

        <h2 class="section-title" style="margin-top:24px">🧪 Inject Test Message</h2>
        <div class="inject-panel">
          <textarea class="inject-input" bind:value={injectText} placeholder="Paste a scam message here to test the AI…"></textarea>
          <button class="inject-btn" on:click={injectMessage} disabled={injectLoading}>
            {injectLoading ? '⏳ Analyzing...' : '🚀 Send to AI Engine'}
          </button>
          {#if injectResult}
            <div class="inject-result" class:inject-scam={injectResult.risk_score >= 80}>
              <span class="inject-score">{injectResult.risk_score}/100</span>
              <span>{injectResult.status === 'held' ? '🚨 SCAM DETECTED' : '✅ SAFE'}</span>
            </div>
          {/if}
        </div>
      </div>
    </section>
  {/if}

  <!-- ─── Dashboard Tab ─── -->
  {#if activeTab === 'dashboard'}

  <!-- ─── Stats Bar ─── -->
  <section class="stats-bar">
    <div class="stat-card">
      <span class="stat-value">{alerts.length}</span>
      <span class="stat-label">Total Alerts</span>
    </div>
    <div class="stat-card critical-bg">
      <span class="stat-value">{pendingAlerts.length}</span>
      <span class="stat-label">Pending Review</span>
    </div>
    <div class="stat-card safe-bg">
      <span class="stat-value">{resolvedAlerts.length}</span>
      <span class="stat-label">Resolved</span>
    </div>
  </section>

  <!-- ─── Error Banner ─── -->
  {#if error}
    <div class="error-banner">
      <span>⚠️ {error}</span>
      <span class="error-sub">Auto-retrying every 15s…</span>
    </div>
  {/if}

  <!-- ─── Pending Alerts ─── -->
  <section class="alerts-section">
    <h2 class="section-title">
      <span class="icon-shield">🛡️</span>
      Pending Alerts
      {#if pendingAlerts.length > 0}
        <span class="badge-count">{pendingAlerts.length}</span>
      {/if}
    </h2>

    {#if pendingAlerts.length === 0}
      <div class="empty-state">
        <div class="empty-icon">✅</div>
        <p>No pending alerts. All transactions are clear.</p>
      </div>
    {:else}
      <div class="alerts-grid">
        {#each pendingAlerts as alert (alert.txn_id)}
          <div class="alert-card" class:critical={alert.risk_score >= 80} class:warning={alert.risk_score >= 50 && alert.risk_score < 80}>
            <!-- Risk Score Ring -->
            <div class="risk-ring-wrap">
              <svg class="risk-ring" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="34" class="ring-bg"/>
                <circle cx="40" cy="40" r="34" class="ring-fill {riskColor(alert.risk_score)}"
                  style="stroke-dasharray: {(alert.risk_score / 100) * 213.6} 213.6"/>
              </svg>
              <span class="ring-text">{alert.risk_score}</span>
            </div>

            <!-- Alert Details -->
            <div class="alert-details">
              <div class="alert-header">
                <span class="risk-tag {riskColor(alert.risk_score)}">
                  {alert.risk_score >= 80 ? '🔴 CRITICAL' : '🟡 WARNING'}
                </span>
                <span class="timer" class:expired={countdown(alert.timestamp) === 'EXPIRED'}>
                  ⏱ {countdown(alert.timestamp)}
                </span>
              </div>
              <div class="detail-row">
                <span class="label">Transaction</span>
                <span class="value mono">{alert.txn_id.slice(0, 8)}…</span>
              </div>
              <div class="detail-row">
                <span class="label">Sender</span>
                <span class="value">{alert.sender_phone}</span>
              </div>
              <div class="detail-row">
                <span class="label">Amount</span>
                <span class="value amount">RM {alert.transaction_amount.toLocaleString('en-MY', {minimumFractionDigits: 2})}</span>
              </div>
              <div class="detail-row">
                <span class="label">Reason</span>
                <span class="value reason">{alert.reason || 'Voice phishing pattern detected'}</span>
              </div>
              <div class="detail-row">
                <span class="label">Time</span>
                <span class="value">{formatTime(alert.timestamp)}</span>
              </div>

              {#if actionResult[alert.txn_id]}
                <div class="action-result {actionResult[alert.txn_id].type}">
                  {actionResult[alert.txn_id].msg}
                </div>
              {/if}

              <div class="action-buttons">
                <button class="btn btn-cancel" disabled={!!actionLoading[alert.txn_id]}
                  on:click={() => onCancel(alert.txn_id)}>
                  {actionLoading[alert.txn_id] === 'cancel' ? '⏳ Cancelling…' : '🚫 Block & Cancel'}
                </button>
                <button class="btn btn-approve" disabled={!!actionLoading[alert.txn_id]}
                  on:click={() => onApprove(alert.txn_id)}>
                  {actionLoading[alert.txn_id] === 'approve' ? '⏳ Approving…' : '✅ Approve'}
                </button>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </section>

  <!-- ─── Resolved ─── -->
  {#if resolvedAlerts.length > 0}
    <section class="alerts-section resolved-section">
      <h2 class="section-title"><span class="icon-shield">📋</span> Resolved</h2>
      <div class="resolved-list">
        {#each resolvedAlerts as alert (alert.txn_id)}
          <div class="resolved-row">
            <span class="resolved-status {alert.status}">{alert.status === 'approved' ? '✅' : '🚫'} {alert.status}</span>
            <span class="mono">{alert.txn_id.slice(0, 8)}…</span>
            <span>Score: {alert.risk_score}</span>
            <span>RM {alert.transaction_amount.toFixed(2)}</span>
            <span>{formatTime(alert.timestamp)}</span>
          </div>
        {/each}
      </div>
    </section>
  {/if}

  <footer>
    <p>HelloFin Shield v1.0 • TNG Digital FINHACK 2026 • Bank-Grade Voice Phishing Detection</p>
  </footer>
  {/if}
</main>



<style>
  /* ═══════════════════════════════════════════════
     DESIGN SYSTEM – HelloFin Shield Dashboard
     ═══════════════════════════════════════════════ */
  :global(*) { margin: 0; padding: 0; box-sizing: border-box; }
  :global(body) {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #0a0e1a;
    color: #e2e8f0;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* ── Animated BG ── */
  .bg-grid {
    position: fixed; inset: 0; z-index: 0;
    background-image:
      linear-gradient(rgba(99,102,241,.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(99,102,241,.04) 1px, transparent 1px);
    background-size: 48px 48px;
  }
  .bg-glow {
    position: fixed; border-radius: 50%; filter: blur(120px); z-index: 0; pointer-events: none;
  }
  .glow-1 { width: 500px; height: 500px; top: -100px; right: -100px; background: rgba(59,130,246,.12); animation: drift 20s ease-in-out infinite; }
  .glow-2 { width: 400px; height: 400px; bottom: -80px; left: -80px; background: rgba(16,185,129,.1); animation: drift 25s ease-in-out infinite reverse; }
  @keyframes drift { 0%,100%{transform:translate(0,0)} 50%{transform:translate(40px,30px)} }

  main { position: relative; z-index: 1; max-width: 1400px; margin: 0 auto; padding: 0 24px 60px; }

  /* ── Header ── */
  header {
    padding: 24px 0 0;
    border-bottom: 1px solid rgba(99,102,241,.15);
    margin-bottom: 32px;
  }
  .header-inner { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; padding-bottom: 16px; }
  .logo-group { display: flex; align-items: center; gap: 14px; }
  .logo-icon svg { width: 44px; height: 44px; }
  h1 { font-size: 1.75rem; font-weight: 800; letter-spacing: -.02em; color: #f1f5f9; }
  .accent { background: linear-gradient(135deg, #6EE7B7, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .subtitle { font-size: .8rem; color: #64748b; margin-top: 2px; letter-spacing: .03em; }
  .status-group { display: flex; align-items: center; gap: 12px; }
  .status-badge {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 14px; border-radius: 20px; font-size: .78rem; font-weight: 600;
    background: rgba(30,41,59,.7); border: 1px solid rgba(99,102,241,.2);
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
  .online .dot { background: #34d399; box-shadow: 0 0 8px #34d399; }
  .offline .dot { background: #f87171; }
  .live-badge {
    display: flex; align-items: center; gap: 6px;
    padding: 5px 12px; border-radius: 20px; font-size: .7rem; font-weight: 700;
    background: rgba(239,68,68,.15); color: #f87171; border: 1px solid rgba(239,68,68,.3);
    letter-spacing: .08em;
  }
  .pulse-dot {
    width: 7px; height: 7px; border-radius: 50%; background: #ef4444;
    animation: pulse 1.5s ease-in-out infinite;
  }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.8)} }

  /* ── Tab Nav ── */
  .tab-nav {
    display: flex; align-items: center; gap: 8px; padding: 0 0 0;
    border-top: 1px solid rgba(99,102,241,.08);
  }
  .tab-btn {
    padding: 12px 22px; background: none; border: none;
    color: #64748b; font-size: .85rem; font-weight: 600;
    cursor: pointer; border-bottom: 2px solid transparent;
    transition: all .2s; letter-spacing: .01em;
  }
  .tab-btn:hover { color: #cbd5e1; }
  .tab-btn.active { color: #6EE7B7; border-bottom-color: #6EE7B7; }
  .demo-toggle {
    margin-left: auto; padding: 6px 16px; border-radius: 20px;
    font-size: .75rem; font-weight: 700; cursor: pointer;
    background: rgba(99,102,241,.1); color: #818cf8;
    border: 1px solid rgba(99,102,241,.3); transition: all .2s;
  }
  .demo-toggle.demo-on {
    background: rgba(239,68,68,.15); color: #f87171;
    border-color: rgba(239,68,68,.4);
    animation: pulse 2s infinite;
  }

  /* ── WhatsApp Section ── */
  .wa-section {
    display: grid; grid-template-columns: 440px 1fr; gap: 32px; align-items: start;
  }
  .wa-caption {
    font-size: .78rem; color: #64748b; margin-bottom: 14px;
  }
  .wa-panel-left { }
  .wa-panel-right { }

  /* ── Engine Card ── */
  .engine-card {
    background: rgba(30,41,59,.6); border: 1px solid rgba(99,102,241,.12);
    border-radius: 16px; padding: 20px; margin-bottom: 4px;
    backdrop-filter: blur(12px);
  }
  .engine-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid rgba(99,102,241,.06);
    font-size: .83rem;
  }
  .engine-row:last-child { border-bottom: none; }
  .engine-label { color: #64748b; font-weight: 500; }
  .engine-val { font-weight: 600; color: #cbd5e1; }
  .engine-val.green { color: #34d399; }
  .engine-val.red { color: #f87171; }

  /* ── Scam Type Chips ── */
  .scam-types { display: flex; flex-wrap: wrap; gap: 8px; }
  .scam-chip {
    background: rgba(99,102,241,.1); border: 1px solid rgba(99,102,241,.2);
    color: #818cf8; padding: 4px 12px; border-radius: 20px;
    font-size: .72rem; font-weight: 600;
  }

  /* ── Stats Bar ── */
  .stats-bar { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }
  .stat-card {
    background: rgba(30,41,59,.6); border: 1px solid rgba(99,102,241,.12);
    border-radius: 16px; padding: 20px 24px; text-align: center;
    backdrop-filter: blur(12px);
    transition: transform .2s, border-color .2s;
  }
  .stat-card:hover { transform: translateY(-2px); border-color: rgba(99,102,241,.3); }
  .critical-bg { border-color: rgba(239,68,68,.25); background: rgba(239,68,68,.06); }
  .safe-bg { border-color: rgba(52,211,153,.25); background: rgba(52,211,153,.06); }
  .stat-value { display: block; font-size: 2.2rem; font-weight: 800; }
  .critical-bg .stat-value { color: #f87171; }
  .safe-bg .stat-value { color: #34d399; }
  .stat-label { font-size: .78rem; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em; }

  /* ── Section ── */
  .alerts-section { }
  .section-title {
    display: flex; align-items: center; gap: 10px;
    font-size: 1.05rem; font-weight: 700; margin-bottom: 16px; color: #f1f5f9;
  }
  .badge-count {
    background: rgba(239,68,68,.2); color: #f87171; font-size: .75rem;
    padding: 2px 10px; border-radius: 12px; font-weight: 700;
  }

  /* ── Error ── */
  .error-banner {
    background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3);
    border-radius: 12px; padding: 14px 20px; margin-bottom: 24px;
    display: flex; justify-content: space-between; align-items: center;
  }
  .error-sub { font-size: .75rem; color: #94a3b8; }

  /* ── Empty ── */
  .empty-state {
    text-align: center; padding: 60px 20px;
    background: rgba(30,41,59,.4); border-radius: 20px;
    border: 1px dashed rgba(99,102,241,.2);
  }
  .empty-icon { font-size: 3rem; margin-bottom: 12px; }

  /* ── Alerts Grid ── */
  .alerts-grid { display: grid; gap: 20px; }
  .alert-card {
    display: flex; gap: 24px; align-items: flex-start;
    background: rgba(30,41,59,.65); border: 1px solid rgba(99,102,241,.12);
    border-radius: 20px; padding: 28px;
    backdrop-filter: blur(16px);
    transition: transform .25s, box-shadow .25s;
    animation: slideIn .4s ease-out;
  }
  .alert-card:hover { transform: translateY(-3px); box-shadow: 0 12px 40px rgba(0,0,0,.3); }
  .alert-card.critical { border-color: rgba(239,68,68,.3); background: rgba(239,68,68,.04); }
  .alert-card.warning { border-color: rgba(251,191,36,.3); background: rgba(251,191,36,.04); }
  @keyframes slideIn { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }

  /* ── Risk Ring ── */
  .risk-ring-wrap { position: relative; flex-shrink: 0; width: 80px; height: 80px; }
  .risk-ring { width: 80px; height: 80px; transform: rotate(-90deg); }
  .ring-bg { fill: none; stroke: rgba(99,102,241,.1); stroke-width: 6; }
  .ring-fill { fill: none; stroke-width: 6; stroke-linecap: round; transition: stroke-dasharray .8s ease; }
  .ring-fill.critical { stroke: #ef4444; }
  .ring-fill.warning { stroke: #fbbf24; }
  .ring-fill.safe { stroke: #34d399; }
  .ring-text {
    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; font-weight: 800;
  }

  /* ── Alert Details ── */
  .alert-details { flex: 1; min-width: 0; }
  .alert-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
  .risk-tag {
    padding: 4px 12px; border-radius: 8px; font-size: .72rem; font-weight: 700;
    letter-spacing: .04em; text-transform: uppercase;
  }
  .risk-tag.critical { background: rgba(239,68,68,.15); color: #f87171; }
  .risk-tag.warning { background: rgba(251,191,36,.15); color: #fbbf24; }
  .timer { font-size: .85rem; font-weight: 600; font-variant-numeric: tabular-nums; color: #94a3b8; }
  .timer.expired { color: #f87171; animation: pulse 1s infinite; }
  .detail-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid rgba(99,102,241,.06); font-size: .85rem; }
  .label { color: #64748b; font-weight: 500; }
  .value { color: #cbd5e1; }
  .mono { font-family: 'JetBrains Mono', monospace; font-size: .8rem; }
  .amount { color: #fbbf24; font-weight: 700; }
  .reason { font-size: .78rem; color: #f87171; max-width: 300px; text-align: right; }

  /* ── Action Buttons ── */
  .action-buttons { display: flex; gap: 10px; margin-top: 16px; }
  .btn {
    flex: 1; padding: 10px 16px; border: none; border-radius: 12px;
    font-size: .82rem; font-weight: 700; cursor: pointer;
    transition: all .2s; letter-spacing: .02em;
  }
  .btn:disabled { opacity: .5; cursor: not-allowed; }
  .btn-cancel {
    background: rgba(239,68,68,.12); color: #f87171; border: 1px solid rgba(239,68,68,.3);
  }
  .btn-cancel:hover:not(:disabled) { background: rgba(239,68,68,.25); transform: translateY(-1px); }
  .btn-approve {
    background: rgba(52,211,153,.12); color: #34d399; border: 1px solid rgba(52,211,153,.3);
  }
  .btn-approve:hover:not(:disabled) { background: rgba(52,211,153,.25); transform: translateY(-1px); }

  .action-result {
    margin-top: 10px; padding: 8px 14px; border-radius: 8px; font-size: .78rem; font-weight: 500;
  }
  .action-result.success { background: rgba(52,211,153,.1); color: #34d399; }
  .action-result.error { background: rgba(239,68,68,.1); color: #f87171; }

  /* ── Resolved ── */
  .resolved-section { margin-top: 40px; opacity: .8; }
  .resolved-list { display: flex; flex-direction: column; gap: 8px; }
  .resolved-row {
    display: flex; align-items: center; gap: 20px;
    padding: 12px 20px; border-radius: 12px;
    background: rgba(30,41,59,.4); font-size: .82rem;
    border: 1px solid rgba(99,102,241,.08);
  }
  .resolved-status { font-weight: 700; text-transform: uppercase; font-size: .72rem; min-width: 100px; }
  .resolved-status.approved { color: #34d399; }
  .resolved-status.cancelled { color: #f87171; }

  /* ── Footer ── */
  footer {
    text-align: center; padding: 40px 0 20px;
    color: #475569; font-size: .75rem; letter-spacing: .04em;
  }

  /* ── Responsive ── */
  @media (max-width: 900px) {
    .wa-section { grid-template-columns: 1fr; }
    .stats-bar { grid-template-columns: 1fr; }
    .alert-card { flex-direction: column; align-items: center; text-align: center; }
    .alert-header { justify-content: center; }
    .detail-row { flex-direction: column; gap: 2px; }
    .reason { max-width: 100%; text-align: center; }
    .action-buttons { flex-direction: column; }
    h1 { font-size: 1.3rem; }
  }

  /* ── Inject Panel ── */
  .inject-panel { margin-top: 8px; }
  .inject-input {
    width: 100%; min-height: 80px; padding: 12px; border-radius: 12px;
    background: rgba(30,41,59,.8); border: 1px solid rgba(99,102,241,.15);
    color: #e2e8f0; font-size: .82rem; font-family: inherit; resize: vertical;
  }
  .inject-input:focus { outline: none; border-color: rgba(99,102,241,.4); }
  .inject-input::placeholder { color: #4a5568; }
  .inject-btn {
    margin-top: 10px; width: 100%; padding: 10px; border-radius: 12px;
    background: linear-gradient(135deg, #6EE7B7, #3B82F6); color: #0a0e1a;
    font-weight: 700; font-size: .82rem; border: none; cursor: pointer;
    transition: all .2s;
  }
  .inject-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(110,231,183,.3); }
  .inject-btn:disabled { opacity: .5; cursor: not-allowed; }
  .inject-result {
    margin-top: 10px; padding: 10px 14px; border-radius: 10px;
    display: flex; align-items: center; gap: 10px;
    background: rgba(52,211,153,.1); border: 1px solid rgba(52,211,153,.3);
    font-size: .82rem; font-weight: 600; color: #34d399;
  }
  .inject-result.inject-scam {
    background: rgba(239,68,68,.12); border-color: rgba(239,68,68,.4); color: #f87171;
  }
  .inject-score { font-size: 1.2rem; font-weight: 800; }
</style>


