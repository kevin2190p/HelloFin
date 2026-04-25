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
  let activeTab = 'whatsapp';
  let injectText = '';
  let injectLoading = false;
  let injectResult = null;

  const PRESETS = [
    { label: '📸 Instagram Verification Code', cat: 'Phishing', text: '02172269 is your verification code. Enter this code in the Instagram app to verify your account. For your security, do not share this code. Instagram will never ask you to share this code by phone call or email.' },
    { label: '👮 Sergeant Michael – Macau Scam', cat: 'Macau Scam', text: 'Hello, this is Sergeant Michael from Bukit Aman. I\'m calling about an urgent matter. Your identity is involved in a money laundering case. We have records showing RM4.2 million in criminal proceeds linked to your bank account. You must cooperate fully, or a warrant for your arrest will be issued within 24 hours. Do not tell anyone about this call, as the investigation is confidential. I need you to transfer funds to the company account I\'m about to send for investigation purposes. Once the case is cleared, your money will be returned immediately. This is your only chance to avoid being arrested.' },
    { label: '📱 Fake Friend – Phone Rosak Loan', cat: 'Emergency Scam', text: 'Hey, it\'s me. I\'m using a friend\'s phone because mine rosak and my wallet got stolen. I need a favour urgently – can you lend me RM5,000? I\'m stuck at a shop and need to pay for repairs before they close. I\'ll definitely pay you back by the end of this month. Please don\'t call my number – my phone is dead. Just trust me on this, I wouldn\'t ask if it wasn\'t serious.' },
    { label: '🎙️ Deepfake Voice – Help Me', cat: 'Family Scam', text: 'Ma, it\'s me. I\'m in bad trouble. I left my wallet at work and I can\'t get home. Please transfer RM1,500 to this account number I\'m sending. Don\'t call my phone, I\'m using a borrowed phone and my boss is right next to me. Just send it quickly. I promise I\'ll explain everything later.' },
    { label: '🏦 Bank Negara / LHDN Scam', cat: 'Authority Scam', text: 'This is a call from Bank Negara Malaysia. Your identity card has been flagged for fraudulent activities involving illicit funds totalling RM706,000. I am now transferring you to the police fraud department. Do not hang up. You are required to transfer your savings into the corporate accounts we provide for investigation. Failure to comply will result in immediate legal action, including freezing of all your bank accounts and a warrant for your arrest.' },
    { label: '📦 COD Parcel Scam', cat: 'Parcel Scam', text: '[WhatsApp from "Pos Laju Courier"]\nYth. Customer,\nThere are 2 unpaid packages under your name with total value RM60. Your package delivery has been FAILED due to incomplete payment.\nClick the link below to complete payment now:\nhttps://pos-laju-pay.xyz/claim\nIf payment is not made within 30 minutes, the package will be returned to sender and a penalty fee of RM25 will be charged.\nThank you.' },
    { label: '💼 Fake Job Offer – WFH', cat: 'Job Scam', text: 'Job Offer: RM8,000 - RM15,000/month! Work from home, flexible hours. No experience needed. Simple tasks: like and share social media posts, leave product reviews. Daily commission paid directly to your TNG eWallet. Our company is partnered with Shopee, Lazada, and TikTok. We have over 200 members already earning. To start, just click the link below, register, and pay a small registration fee of RM50 + Free RM20 credited to your account as a starter bonus!' },
    { label: '📈 Investment Scam – 10% Returns', cat: 'Investment Scam', text: '🚀 URGENT INVESTMENT ALERT 🚀\nOur special "Growth Investment" scheme is now open for new members! Guaranteed returns are paid every 30 minutes. For every RM1,000 invested, you receive RM100 profit in just half an hour.\n✅ 0% risk\n✅ No hidden fees\n✅ Withdraw anytime\nOur members have earned over RM23,000 in just their first week! This offer will close at midnight tonight. Click here to view our profit screenshots and join our VIP group now.' },
    { label: '📮 Customs Parcel – Prohibited Items', cat: 'Customs Scam', text: 'This is an automated message from Pos Malaysia & Customs Department. A parcel under your name containing prohibited items and an undeclared amount of cash has been detained at our warehouse. To avoid legal charges and court summons, please contact our investigation officer immediately at the number provided. Your cooperation is required within 2 hours before we escalate this matter to Bank Negara Malaysia.' },
  ];

  function selectPreset(p) { injectText = p.text; injectResult = null; }

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

  let ticker;
  onMount(() => {
    stopPolling = startPolling((data, err) => { alerts = data; error = err; });
    ticker = setInterval(() => { now = Date.now(); }, 1000);
    healthCheck().then(() => backendOnline = true).catch(() => backendOnline = false);
  });
  onDestroy(() => { if (stopPolling) stopPolling(); if (ticker) clearInterval(ticker); });

  function countdown(ts) {
    if (!ts) return '—';
    const expire = (ts + 600) * 1000;
    const diff = Math.max(0, Math.floor((expire - now) / 1000));
    return diff <= 0 ? 'EXPIRED' : `${Math.floor(diff/60)}:${(diff%60).toString().padStart(2,'0')}`;
  }

  async function onApprove(txnId) {
    actionLoading[txnId] = 'approve';
    try { const res = await handleApprove(txnId); actionResult[txnId] = { type: 'success', msg: res.message }; }
    catch (e) { actionResult[txnId] = { type: 'error', msg: e.message }; }
    actionLoading[txnId] = null;
  }
  async function onCancel(txnId) {
    actionLoading[txnId] = 'cancel';
    try { const res = await handleCancel(txnId); actionResult[txnId] = { type: 'success', msg: res.message }; }
    catch (e) { actionResult[txnId] = { type: 'error', msg: e.message }; }
    actionLoading[txnId] = null;
  }

  $: pendingAlerts = alerts.filter(a => a.status === 'held' || a.status === 'pending');
  $: resolvedAlerts = alerts.filter(a => a.status === 'approved' || a.status === 'cancelled');
</script>

<main>
  <header>
    <div class="hdr-left"><h1>HelloFin Shield</h1><p class="tagline">Phishing Detection · FINHACK 2026</p></div>
    <div class="hdr-right"><span class="status" class:on={backendOnline}>{backendOnline ? 'Online' : 'Offline'}</span></div>
  </header>

  <nav class="tabs">
    <button class:active={activeTab==='whatsapp'} on:click={()=>activeTab='whatsapp'}>WhatsApp Monitor</button>
    <button class:active={activeTab==='dashboard'} on:click={()=>activeTab='dashboard'}>Alert Dashboard</button>
    {#if activeTab==='whatsapp'}
      <button class="mode-btn" class:demo={demoMode} on:click={()=>demoMode=!demoMode}>{demoMode ? 'Demo Mode' : 'Live Mode'}</button>
    {/if}
  </nav>

  {#if activeTab==='whatsapp'}
  <div class="wa-layout">
    <div class="wa-left">
      <div class="panel-label">Intercepted Messages</div>
      <p class="panel-sub">{demoMode ? 'Playing hardcoded demo scenario' : 'Live from +60163569782'}</p>
      {#key demoMode}<WhatsAppWidget demoMode={demoMode} />{/key}
    </div>
    <div class="wa-right">
      <div class="card">
        <div class="card-title">Detection Engine</div>
        <div class="row"><span>STT</span><span class="val ok">Groq Whisper large-v3</span></div>
        <div class="row"><span>LLM</span><span class="val ok">Qwen3-32B via Groq</span></div>
        <div class="row"><span>Keywords</span><span class="val ok">200+ MY phrases</span></div>
        <div class="row"><span>Fusion</span><span class="val">35% KW + 65% LLM</span></div>
        <div class="row"><span>Watchlist</span><span class="val danger">+60163569782</span></div>
      </div>

      <div class="card">
        <div class="card-title">🧪 Quick Inject – Select a Scam Script</div>
        <div class="preset-grid">
          {#each PRESETS as p, i}
            <button class="preset-btn" on:click={() => selectPreset(p)}>
              <span class="preset-label">{p.label}</span>
              <span class="preset-cat">{p.cat}</span>
            </button>
          {/each}
        </div>
      </div>

      <div class="card">
        <div class="card-title">Custom Message</div>
        <textarea class="inject-ta" bind:value={injectText} placeholder="Paste or select a preset above…"></textarea>
        <button class="inject-btn" on:click={injectMessage} disabled={injectLoading}>
          {injectLoading ? 'Analyzing…' : '🚀 Send to AI Engine'}
        </button>
        {#if injectResult}
          <div class="inject-res" class:scam={injectResult.risk_score >= 50}>
            <strong>{injectResult.risk_score}/100</strong>
            <span>{injectResult.risk_score >= 80 ? '🚨 SCAM DETECTED — HELD' : injectResult.risk_score >= 50 ? '⚠️ SUSPICIOUS' : '✅ CLEARED'}</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
  {/if}

  {#if activeTab==='dashboard'}
  <div class="stats">
    <div class="stat"><span class="stat-n">{alerts.length}</span><span class="stat-l">Total</span></div>
    <div class="stat warn-bg"><span class="stat-n">{pendingAlerts.length}</span><span class="stat-l">Pending</span></div>
    <div class="stat ok-bg"><span class="stat-n">{resolvedAlerts.length}</span><span class="stat-l">Resolved</span></div>
  </div>
  {#if error}<div class="err">⚠ {error}</div>{/if}
  <div class="panel-label">Pending Alerts</div>
  {#if pendingAlerts.length === 0}
    <div class="empty">No pending alerts.</div>
  {:else}
    {#each pendingAlerts as alert (alert.txn_id)}
      <div class="alert-row" class:crit={alert.risk_score >= 80}>
        <div class="a-score" class:crit={alert.risk_score>=80}>{alert.risk_score}</div>
        <div class="a-body">
          <div class="a-top">
            <span class="a-tag" class:crit={alert.risk_score>=80}>{alert.risk_score >= 80 ? 'CRITICAL' : 'WARNING'}</span>
            <span class="a-timer">{countdown(alert.timestamp)}</span>
          </div>
          <div class="a-detail"><span>Sender</span><span>{alert.sender_phone}</span></div>
          <div class="a-detail"><span>Amount</span><span>RM {alert.transaction_amount?.toLocaleString('en-MY',{minimumFractionDigits:2}) || '0.00'}</span></div>
          <div class="a-detail"><span>Reason</span><span class="reason-text">{alert.reason || 'Phishing detected'}</span></div>
          <div class="a-actions">
            <button class="btn-blk" disabled={!!actionLoading[alert.txn_id]} on:click={()=>onCancel(alert.txn_id)}>Block</button>
            <button class="btn-ok" disabled={!!actionLoading[alert.txn_id]} on:click={()=>onApprove(alert.txn_id)}>Approve</button>
          </div>
        </div>
      </div>
    {/each}
  {/if}
  {/if}

  <footer>HelloFin Shield v1.0 · TNG Digital FINHACK 2026</footer>
</main>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  :global(*){margin:0;padding:0;box-sizing:border-box}
  :global(body){font-family:'Inter',system-ui,sans-serif;background:#f5f5f7;color:#1d1d1f;min-height:100vh}
  main{max-width:1200px;margin:0 auto;padding:20px 28px 60px}

  header{display:flex;justify-content:space-between;align-items:center;padding:16px 0 12px;border-bottom:1px solid #d2d2d7}
  h1{font-size:1.4rem;font-weight:700;letter-spacing:-.02em}
  .tagline{font-size:.75rem;color:#86868b;margin-top:2px}
  .status{font-size:.75rem;font-weight:600;padding:4px 14px;border-radius:20px;background:#f5f5f7;border:1px solid #d2d2d7;color:#86868b}
  .status.on{background:#e8f5e9;border-color:#a5d6a7;color:#2e7d32}

  .tabs{display:flex;gap:0;border-bottom:1px solid #d2d2d7;margin-bottom:24px}
  .tabs button{padding:12px 20px;background:none;border:none;font-size:.85rem;font-weight:600;color:#86868b;cursor:pointer;border-bottom:2px solid transparent;transition:all .15s}
  .tabs button:hover{color:#1d1d1f}
  .tabs button.active{color:#0071e3;border-bottom-color:#0071e3}
  .mode-btn{margin-left:auto!important;font-size:.72rem!important;padding:6px 14px!important;border-radius:16px!important;background:#f0f0f0!important;border:1px solid #ccc!important;color:#555!important}
  .mode-btn.demo{background:#fff3cd!important;border-color:#ffc107!important;color:#856404!important}

  .wa-layout{display:grid;grid-template-columns:420px 1fr;gap:24px;align-items:start}
  .panel-label{font-size:.9rem;font-weight:700;margin-bottom:6px}
  .panel-sub{font-size:.75rem;color:#86868b;margin-bottom:12px}

  .card{background:#fff;border:1px solid #e5e5ea;border-radius:12px;padding:16px;margin-bottom:16px}
  .card-title{font-size:.82rem;font-weight:700;margin-bottom:10px}
  .row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f2f2f7;font-size:.8rem}
  .row:last-child{border:none}
  .row span:first-child{color:#86868b}
  .val{font-weight:600}.val.ok{color:#2e7d32}.val.danger{color:#c62828}

  /* Preset grid */
  .preset-grid{display:flex;flex-direction:column;gap:6px}
  .preset-btn{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;border:1px solid #e5e5ea;border-radius:8px;background:#fafafa;cursor:pointer;transition:all .12s;text-align:left}
  .preset-btn:hover{background:#e8f4fd;border-color:#90caf9}
  .preset-label{font-size:.78rem;font-weight:500;color:#1d1d1f}
  .preset-cat{font-size:.65rem;color:#86868b;background:#f2f2f7;padding:2px 8px;border-radius:10px;flex-shrink:0}

  .inject-ta{width:100%;min-height:60px;padding:10px;border:1px solid #e5e5ea;border-radius:8px;font-size:.8rem;font-family:inherit;resize:vertical;background:#fafafa;color:#1d1d1f}
  .inject-ta:focus{outline:none;border-color:#0071e3}
  .inject-ta::placeholder{color:#aaa}
  .inject-btn{margin-top:8px;width:100%;padding:10px;border:none;border-radius:8px;background:#0071e3;color:#fff;font-size:.82rem;font-weight:600;cursor:pointer}
  .inject-btn:hover:not(:disabled){background:#005bb5}
  .inject-btn:disabled{opacity:.5;cursor:not-allowed}
  .inject-res{margin-top:8px;padding:8px 12px;border-radius:8px;font-size:.8rem;font-weight:600;background:#e8f5e9;color:#2e7d32;border:1px solid #a5d6a7;display:flex;gap:8px;align-items:center}
  .inject-res.scam{background:#fce4e4;color:#c62828;border-color:#ef9a9a}

  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}
  .stat{background:#fff;border:1px solid #e5e5ea;border-radius:12px;padding:20px;text-align:center}
  .stat-n{display:block;font-size:2rem;font-weight:700}
  .stat-l{font-size:.72rem;color:#86868b;text-transform:uppercase}
  .warn-bg{border-color:#ffcdd2}.warn-bg .stat-n{color:#c62828}
  .ok-bg{border-color:#a5d6a7}.ok-bg .stat-n{color:#2e7d32}

  .err{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:10px 16px;margin-bottom:16px;font-size:.8rem}
  .empty{background:#fff;border:1px solid #e5e5ea;border-radius:12px;padding:40px;text-align:center;color:#86868b}

  .alert-row{display:flex;gap:16px;background:#fff;border:1px solid #e5e5ea;border-radius:12px;padding:20px;margin-bottom:12px}
  .alert-row.crit{border-color:#ef9a9a;background:#fffbfb}
  .a-score{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:800;flex-shrink:0;background:#f2f2f7;color:#555}
  .a-score.crit{background:#fce4e4;color:#c62828}
  .a-body{flex:1}
  .a-top{display:flex;justify-content:space-between;margin-bottom:10px}
  .a-tag{font-size:.68rem;font-weight:700;text-transform:uppercase;padding:3px 10px;border-radius:6px;background:#fff8e1;color:#e65100}
  .a-tag.crit{background:#fce4e4;color:#c62828}
  .a-timer{font-size:.78rem;color:#86868b}
  .a-detail{display:flex;justify-content:space-between;padding:4px 0;font-size:.8rem;border-bottom:1px solid #f2f2f7}
  .a-detail span:first-child{color:#86868b}
  .reason-text{color:#c62828;font-size:.78rem;max-width:260px;text-align:right}
  .a-actions{display:flex;gap:8px;margin-top:12px}
  .btn-blk,.btn-ok{flex:1;padding:8px;border:none;border-radius:8px;font-size:.78rem;font-weight:600;cursor:pointer}
  .btn-blk{background:#fce4e4;color:#c62828;border:1px solid #ef9a9a}
  .btn-ok{background:#e8f5e9;color:#2e7d32;border:1px solid #a5d6a7}
  .btn-blk:disabled,.btn-ok:disabled{opacity:.5;cursor:not-allowed}

  footer{text-align:center;padding:32px 0 16px;color:#86868b;font-size:.7rem}
  @media(max-width:900px){.wa-layout{grid-template-columns:1fr}.stats{grid-template-columns:1fr}}
</style>
