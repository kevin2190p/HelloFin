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
  let activeTab = 'whatsapp';
  let chatMessages = [];
  let injecting = false;
  let currentContact = 'Unknown';
  let currentAvatar = '';

  const PRESETS = [
    { label: '📸 Instagram Verification Code', cat: 'Phishing', name: 'Instagram', avatar: 'https://i.pravatar.cc/100?img=60', parts: [
      { from:'them', text:'02172269 is your verification code. Enter this code in the Instagram app to verify your account. For your security, do not share this code. Instagram will never ask you to share this code by phone call or email.', score: 30 },
      { from:'me', text:'Hmm I didn\'t request any code... who is this?' },
      { from:'them', text:'This is Instagram support. Your account has been flagged for suspicious activity. Please share the code now or your account will be permanently disabled within 1 hour.', score: 62 },
      { from:'me', text:'Wait, Instagram wouldn\'t message me on WhatsApp right? This is suspicious...' },
    ]},
    { label: '👮 Sgt. Michael – Macau Scam', cat: 'Police Scam', name: 'Sergeant Michael', avatar: 'https://i.pravatar.cc/100?img=12', parts: [
      { from:'them', text:'Hello, this is Sergeant Michael from Bukit Aman. I\'m calling about an urgent matter.', score: 45 },
      { from:'me', text:'Hello? What matter?' },
      { from:'them', type:'voice', duration:18, transcript:'Your identity is involved in a money laundering case under investigation by PDRM. We have records showing RM4.2 million in criminal proceeds linked to your bank account.', score: 95 },
      { from:'me', text:'What?! That\'s impossible, I\'m just a student...' },
      { from:'them', text:'You must cooperate fully, or a warrant for your arrest will be issued within 24 hours. Do not tell anyone about this call, as the investigation is confidential.', score: 97 },
      { from:'me', text:'Ok ok, what do I need to do?' },
      { from:'them', text:'I need you to transfer funds to the safe account I\'m about to send for investigation purposes. Once the case is cleared, your money will be returned immediately. This is your only chance to avoid being arrested.', score: 98 },
    ]},
    { label: '📱 Fake Friend – Phone Rosak', cat: 'Emergency Scam', name: 'Ahmad Razif', avatar: 'https://i.pravatar.cc/100?img=33', parts: [
      { from:'them', text:'Hey, it\'s me. I\'m using a friend\'s phone because mine rosak and my wallet got stolen.', score: 45 },
      { from:'me', text:'Eh who is this? Which friend?' },
      { from:'them', type:'voice', duration:12, transcript:'It\'s me la bro! I need a favour urgently, can you lend me RM5,000? I\'m stuck at a shop and need to pay for repairs before they close.', score: 72 },
      { from:'me', text:'RM5,000?? That\'s a lot leh...' },
      { from:'them', text:'I\'ll definitely pay you back by the end of this month. Please don\'t call my number – my phone is dead. Just trust me on this, I wouldn\'t ask if it wasn\'t serious.', score: 82 },
    ]},
    { label: '🎙️ Deepfake Voice – Help Me', cat: 'Family Scam', name: 'Mama', avatar: 'https://i.pravatar.cc/100?img=49', parts: [
      { from:'them', type:'voice', duration:8, transcript:'Ma, it\'s me. I\'m in bad trouble. I left my wallet at work and I can\'t get home.', score: 68 },
      { from:'me', text:'Hello?? What happened to you?!' },
      { from:'them', text:'Please transfer RM1,500 to this account number I\'m sending. Don\'t call my phone, I\'m using a borrowed phone and my boss is right next to me.', score: 85 },
      { from:'me', text:'Ok wait let me check...' },
      { from:'them', type:'voice', duration:15, transcript:'Just send it quickly ma. I promise I\'ll explain everything later. Don\'t call my number, just transfer now please.', score: 88 },
    ]},
    { label: '🏦 Bank Negara / LHDN', cat: 'Authority Scam', name: 'BNM Officer Tan', avatar: 'https://i.pravatar.cc/100?img=14', parts: [
      { from:'them', text:'This is a call from Bank Negara Malaysia. Your identity card has been flagged for fraudulent activities involving illicit funds totalling RM706,000.', score: 85 },
      { from:'me', text:'What? I don\'t have that kind of money!' },
      { from:'them', type:'voice', duration:22, transcript:'I am now transferring you to the police fraud department at PDRM. Do not hang up. You are under investigation for money laundering.', score: 97 },
      { from:'me', text:'Ok ok I\'m listening...' },
      { from:'them', text:'You are required to transfer your savings into the corporate accounts we provide for investigation. Failure to comply will result in immediate legal action, including freezing of all your bank accounts and a warrant for your arrest.', score: 99 },
    ]},
    { label: '📦 COD Parcel Scam', cat: 'Parcel Scam', name: 'Pos Laju Delivery', avatar: 'https://i.pravatar.cc/100?img=69', parts: [
      { from:'them', text:'[Pos Laju Courier]\nYth. Customer,\nThere are 2 unpaid packages under your name with total value RM60. Your package delivery has been FAILED due to incomplete payment.', score: 55 },
      { from:'me', text:'Huh? I didn\'t order anything recently...' },
      { from:'them', text:'Click the link below to complete payment now:\nhttps://pos-laju-pay.xyz/claim\nIf payment is not made within 30 minutes, the package will be returned to sender and a penalty fee of RM25 will be charged.', score: 82 },
    ]},
    { label: '💼 Fake Job – WFH RM8K', cat: 'Job Scam', name: 'HR Jenny Lim', avatar: 'https://i.pravatar.cc/100?img=47', parts: [
      { from:'them', text:'Job Offer: RM8,000 - RM15,000/month! Work from home, flexible hours. No experience needed.', score: 42 },
      { from:'me', text:'Sounds too good to be true... what\'s the catch?' },
      { from:'them', type:'voice', duration:20, transcript:'Simple tasks only. Like and share social media posts, leave product reviews. Daily commission paid directly to your TNG eWallet. Our company is partnered with Shopee, Lazada, and TikTok.', score: 68 },
      { from:'me', text:'What do I need to do to start?' },
      { from:'them', text:'We have over 200 members already earning. To start, just click the link below, register, and pay a small registration fee of RM50 + Free RM20 credited to your account as a starter bonus!', score: 85 },
    ]},
    { label: '📈 Investment – 10% Returns', cat: 'Investment Scam', name: 'FYCMAX Admin', avatar: 'https://i.pravatar.cc/100?img=52', parts: [
      { from:'them', text:'🚀 URGENT INVESTMENT ALERT 🚀\nOur special "Growth Investment" scheme is now open for new members! Guaranteed returns are paid every 30 minutes.', score: 55 },
      { from:'me', text:'Every 30 minutes? That doesn\'t sound real...' },
      { from:'them', text:'For every RM1,000 invested, you receive RM100 profit in just half an hour.\n✅ 0% risk\n✅ No hidden fees\n✅ Withdraw anytime', score: 78 },
      { from:'me', text:'How do I know this is legit?' },
      { from:'them', text:'Our members have earned over RM23,000 in just their first week! This offer will close at midnight tonight. Click here to view our profit screenshots and join our VIP group now.', score: 88 },
    ]},
    { label: '📮 Customs – Prohibited Items', cat: 'Customs Scam', name: 'Kastam Officer', avatar: 'https://i.pravatar.cc/100?img=11', parts: [
      { from:'them', text:'This is an automated message from Pos Malaysia & Customs Department. A parcel under your name containing prohibited items and an undeclared amount of cash has been detained at our warehouse.', score: 72 },
      { from:'me', text:'What?? I never sent any parcel with cash!' },
      { from:'them', type:'voice', duration:25, transcript:'To avoid legal charges and court summons, please contact our investigation officer immediately. Your cooperation is required within 2 hours before we escalate this matter to Bank Negara Malaysia and PDRM for further action.', score: 92 },
    ]},
  ];

  async function runPreset(preset) {
    if (injecting) return;
    injecting = true;
    chatMessages = [];
    currentContact = preset.name;
    currentAvatar = preset.avatar;

    for (let i = 0; i < preset.parts.length; i++) {
      const part = preset.parts[i];
      const t = new Date().toLocaleTimeString('en-MY',{hour:'2-digit',minute:'2-digit'});
      const id = Date.now().toString(36) + Math.random().toString(36).slice(2,6);

      if (part.from === 'them') {
        chatMessages = [...chatMessages, { id, from:'them', type:part.type||'text', text:part.text||'', transcript:part.transcript||'', duration:part.duration||0, time:t, scanning:true, risk_score:null }];
        await sleep(1800);
        chatMessages = chatMessages.map(m => m.id===id ? {...m, scanning:false, risk_score:part.score} : m);
        if (part.score >= 80) {
          alerts = [...alerts, { txn_id: id, sender_phone: currentContact, risk_score: part.score, status:'held', timestamp: Math.floor(Date.now()/1000), transaction_amount: Math.floor(Math.random()*8000)+1000, reason: preset.cat + ' — flagged by AI engine' }];
        }
      } else {
        chatMessages = [...chatMessages, { id, from:'me', type:'text', text:part.text, time:t, scanning:false, risk_score:null }];
      }
      await sleep(1200);
    }
    injecting = false;
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  let ticker;
  onMount(() => {
    stopPolling = startPolling((data, err) => { if (data.length) alerts = [...alerts, ...data.filter(d => !alerts.find(a => a.txn_id === d.txn_id))]; error = err; });
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
    alerts = alerts.map(a => a.txn_id===txnId ? {...a, status:'approved'} : a);
    actionLoading[txnId] = null;
  }
  async function onCancel(txnId) {
    actionLoading[txnId] = 'cancel';
    alerts = alerts.map(a => a.txn_id===txnId ? {...a, status:'cancelled'} : a);
    actionLoading[txnId] = null;
  }

  $: pendingAlerts = alerts.filter(a => a.status === 'held' || a.status === 'pending');
  $: resolvedAlerts = alerts.filter(a => a.status === 'approved' || a.status === 'cancelled');
</script>

<main>
  <header><h1>Fakeout</h1></header>
  <nav class="tabs">
    <button class:active={activeTab==='whatsapp'} on:click={()=>activeTab='whatsapp'}>WhatsApp Monitor</button>
    <button class:active={activeTab==='dashboard'} on:click={()=>activeTab='dashboard'}>Alert Dashboard {#if pendingAlerts.length > 0}<span class="tab-badge">{pendingAlerts.length}</span>{/if}</button>
  </nav>

  {#if activeTab==='whatsapp'}
  <div class="wa-layout">
    <div class="wa-left">
      <WhatsAppWidget messages={chatMessages} contactName={currentContact} avatarUrl={currentAvatar} />
    </div>
    <div class="wa-right">
      <div class="card">
        <div class="card-title">Real-World Scam Scenario</div>
        <div class="preset-grid">
          {#each PRESETS as p}
            <button class="preset-btn" on:click={() => runPreset(p)} disabled={injecting}>
              <span class="preset-label">{p.label}</span>
              <span class="preset-cat">{p.cat}</span>
            </button>
          {/each}
        </div>
        {#if injecting}<div class="injecting-bar">⏳ Scenario playing…</div>{/if}
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
  {#if pendingAlerts.length === 0 && resolvedAlerts.length === 0}
    <div class="empty">No alerts yet. Run a scam scenario in WhatsApp Monitor to see detections here.</div>
  {/if}
  {#if pendingAlerts.length > 0}
    <div class="panel-label">🚨 Pending Review</div>
    {#each pendingAlerts as alert (alert.txn_id)}
      <div class="alert-row crit">
        <div class="a-score crit">{alert.risk_score}</div>
        <div class="a-body">
          <div class="a-top">
            <span class="a-tag crit">CRITICAL</span>
            <span class="a-timer">⏱ {countdown(alert.timestamp)}</span>
          </div>
          <div class="a-detail"><span>From</span><span>{alert.sender_phone}</span></div>
          <div class="a-detail"><span>Amount</span><span>RM {alert.transaction_amount?.toLocaleString('en-MY',{minimumFractionDigits:2}) || '0.00'}</span></div>
          <div class="a-detail"><span>Reason</span><span class="reason-text">{alert.reason}</span></div>
          <div class="a-actions">
            <button class="btn-blk" on:click={()=>onCancel(alert.txn_id)}>🚫 Block & Cancel</button>
            <button class="btn-ok" on:click={()=>onApprove(alert.txn_id)}>✅ Approve</button>
          </div>
        </div>
      </div>
    {/each}
  {/if}
  {#if resolvedAlerts.length > 0}
    <div class="panel-label" style="margin-top:24px">📋 Resolved</div>
    {#each resolvedAlerts as alert (alert.txn_id)}
      <div class="resolved-row">
        <span class="r-status" class:approved={alert.status==='approved'} class:cancelled={alert.status==='cancelled'}>{alert.status==='approved'?'✅':'🚫'} {alert.status}</span>
        <span>{alert.sender_phone}</span>
        <span>Score: {alert.risk_score}</span>
        <span>RM {alert.transaction_amount?.toFixed(2)}</span>
      </div>
    {/each}
  {/if}
  {/if}

  <footer>Fakeout · TNG Digital FINHACK 2026</footer>
</main>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  :global(*){margin:0;padding:0;box-sizing:border-box}
  :global(body){font-family:'Inter',system-ui,sans-serif;background:#f5f5f7;color:#1d1d1f;min-height:100vh}
  main{max-width:1200px;margin:0 auto;padding:20px 28px 60px}
  header{padding:16px 0 12px;border-bottom:1px solid #d2d2d7}
  h1{font-size:1.4rem;font-weight:700;letter-spacing:-.02em}
  .tabs{display:flex;gap:0;border-bottom:1px solid #d2d2d7;margin-bottom:24px}
  .tabs button{padding:12px 20px;background:none;border:none;font-size:.85rem;font-weight:600;color:#86868b;cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;display:flex;align-items:center;gap:6px}
  .tabs button:hover{color:#1d1d1f}
  .tabs button.active{color:#0071e3;border-bottom-color:#0071e3}
  .tab-badge{background:#c62828;color:#fff;font-size:.65rem;font-weight:700;padding:1px 7px;border-radius:10px;min-width:18px;text-align:center}

  .wa-layout{display:grid;grid-template-columns:420px 1fr;gap:24px;align-items:start}
  .card{background:#fff;border:1px solid #e5e5ea;border-radius:12px;padding:16px;margin-bottom:16px}
  .card-title{font-size:.82rem;font-weight:700;margin-bottom:10px}
  .preset-grid{display:flex;flex-direction:column;gap:6px}
  .preset-btn{display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border:1px solid #e5e5ea;border-radius:8px;background:#fafafa;cursor:pointer;transition:all .12s;text-align:left}
  .preset-btn:hover:not(:disabled){background:#e8f4fd;border-color:#90caf9}
  .preset-btn:disabled{opacity:.4;cursor:not-allowed}
  .preset-label{font-size:.78rem;font-weight:500;color:#1d1d1f}
  .preset-cat{font-size:.65rem;color:#86868b;background:#f2f2f7;padding:2px 8px;border-radius:10px;flex-shrink:0}
  .injecting-bar{margin-top:10px;padding:8px 12px;border-radius:8px;background:#e8f4fd;color:#0071e3;font-size:.78rem;font-weight:600;text-align:center;animation:pulse 1.5s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}

  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}
  .stat{background:#fff;border:1px solid #e5e5ea;border-radius:12px;padding:20px;text-align:center}
  .stat-n{display:block;font-size:2rem;font-weight:700}
  .stat-l{font-size:.72rem;color:#86868b;text-transform:uppercase}
  .warn-bg{border-color:#ffcdd2}.warn-bg .stat-n{color:#c62828}
  .ok-bg{border-color:#a5d6a7}.ok-bg .stat-n{color:#2e7d32}
  .panel-label{font-size:.9rem;font-weight:700;margin-bottom:8px}
  .empty{background:#fff;border:1px solid #e5e5ea;border-radius:12px;padding:40px;text-align:center;color:#86868b;font-size:.85rem}
  .alert-row{display:flex;gap:16px;background:#fff;border:1px solid #e5e5ea;border-radius:12px;padding:20px;margin-bottom:12px}
  .alert-row.crit{border-color:#ef9a9a;background:#fffbfb}
  .a-score{width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:800;flex-shrink:0;background:#f2f2f7;color:#555}
  .a-score.crit{background:#fce4e4;color:#c62828}
  .a-body{flex:1}
  .a-top{display:flex;justify-content:space-between;margin-bottom:10px}
  .a-tag{font-size:.68rem;font-weight:700;text-transform:uppercase;padding:3px 10px;border-radius:6px;background:#fce4e4;color:#c62828}
  .a-timer{font-size:.78rem;color:#86868b}
  .a-detail{display:flex;justify-content:space-between;padding:4px 0;font-size:.8rem;border-bottom:1px solid #f2f2f7}
  .a-detail span:first-child{color:#86868b}
  .reason-text{color:#c62828;font-size:.78rem;max-width:260px;text-align:right}
  .a-actions{display:flex;gap:8px;margin-top:12px}
  .btn-blk,.btn-ok{flex:1;padding:8px;border:none;border-radius:8px;font-size:.78rem;font-weight:600;cursor:pointer}
  .btn-blk{background:#fce4e4;color:#c62828;border:1px solid #ef9a9a}
  .btn-blk:hover{background:#f8d7da}
  .btn-ok{background:#e8f5e9;color:#2e7d32;border:1px solid #a5d6a7}
  .btn-ok:hover{background:#c8e6c9}
  .resolved-row{display:flex;align-items:center;gap:16px;padding:10px 16px;background:#fff;border:1px solid #e5e5ea;border-radius:8px;margin-bottom:6px;font-size:.78rem}
  .r-status{font-weight:700;text-transform:uppercase;font-size:.68rem;min-width:100px}
  .r-status.approved{color:#2e7d32}
  .r-status.cancelled{color:#c62828}
  footer{text-align:center;padding:32px 0 16px;color:#86868b;font-size:.7rem}
  @media(max-width:900px){.wa-layout{grid-template-columns:1fr}.stats{grid-template-columns:1fr}}
</style>
