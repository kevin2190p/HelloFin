<script>
  import { onMount, onDestroy } from 'svelte';
  import { startPolling, handleApprove, handleCancel, formatTime } from './lib/caregiverDashboard.js';
  import { healthCheck } from './lib/api.js';
  import WhatsAppWidget from './lib/WhatsAppWidget.svelte';

  let alerts=[], error=null, stopPolling, backendOnline=false, now=Date.now(), actionLoading={}, actionResult={};
  let activeTab='whatsapp', chatMessages=[], injecting=false, currentContact='Unknown', currentAvatar='';

  const P = [
    { label:'📸 Instagram Verification', cat:'Phishing', name:'Instagram Support', avatar:'https://randomuser.me/api/portraits/women/44.jpg', parts:[
      {from:'them',text:'02172269 is your verification code. Enter this code in the Instagram app to verify your account. For your security, do not share this code. Instagram will never ask you to share this code by phone call or email.',score:30},
      {from:'me',text:'Hmm I didn\'t request any code... who is this?'},
      {from:'them',text:'This is Instagram support. Your account has been flagged for suspicious activity. Please share the code now or your account will be permanently disabled within 1 hour.',score:62},
      {from:'me',text:'Wait, Instagram wouldn\'t message me on WhatsApp right? This is suspicious...'},
    ]},
    { label:'👮 Sgt. Michael – Macau Scam', cat:'Police Scam', name:'Sergeant Michael', avatar:'https://randomuser.me/api/portraits/men/32.jpg', parts:[
      {from:'them',text:'Hello, this is Sergeant Michael from Bukit Aman. I\'m calling about an urgent matter.',score:45},
      {from:'me',text:'Hello? What matter?'},
      {from:'them',type:'voice',duration:18,transcript:'Your identity is involved in a money laundering case under investigation by PDRM. We have records showing RM4.2 million in criminal proceeds linked to your bank account.',score:95},
      {from:'me',text:'What?! That\'s impossible, I\'m just a student...'},
      {from:'them',text:'You must cooperate fully, or a warrant for your arrest will be issued within 24 hours. Do not tell anyone about this call, as the investigation is confidential.',score:97},
      {from:'me',text:'Ok ok, what do I need to do?'},
      {from:'them',text:'I need you to transfer funds to the safe account I\'m about to send for investigation purposes. Once the case is cleared, your money will be returned immediately. This is your only chance to avoid being arrested.',score:98},
    ]},
    { label:'📱 Fake Friend – Phone Rosak', cat:'Emergency Scam', name:'Ahmad Razif', avatar:'https://randomuser.me/api/portraits/men/75.jpg', parts:[
      {from:'them',text:'Hey, it\'s me. I\'m using a friend\'s phone because mine rosak and my wallet got stolen.',score:45},
      {from:'me',text:'Eh who is this? Which friend?'},
      {from:'them',type:'voice',duration:12,transcript:'It\'s me la bro! I need a favour urgently, can you lend me RM5,000? I\'m stuck at a shop and need to pay for repairs before they close.',score:72},
      {from:'me',text:'RM5,000?? That\'s a lot leh...'},
      {from:'them',text:'I\'ll definitely pay you back by the end of this month. Please don\'t call my number – my phone is dead. Just trust me on this, I wouldn\'t ask if it wasn\'t serious.',score:82},
    ]},
    { label:'🎙️ Deepfake Voice – Help Me', cat:'Family Scam', name:'Anak (Son)', avatar:'https://randomuser.me/api/portraits/men/85.jpg', parts:[
      {from:'them',type:'voice',duration:8,transcript:'Ma, it\'s me. I\'m in bad trouble. I left my wallet at work and I can\'t get home.',score:68},
      {from:'me',text:'Hello?? What happened to you?!'},
      {from:'them',text:'Please transfer RM1,500 to this account number I\'m sending. Don\'t call my phone, I\'m using a borrowed phone and my boss is right next to me.',score:85},
      {from:'me',text:'Ok wait let me check...'},
      {from:'them',type:'voice',duration:15,transcript:'Just send it quickly ma. I promise I\'ll explain everything later. Don\'t call my number, just transfer now please.',score:88},
    ]},
    { label:'🏦 Bank Negara / LHDN', cat:'Authority Scam', name:'Officer Tan Wei Ming', avatar:'https://randomuser.me/api/portraits/men/22.jpg', parts:[
      {from:'them',text:'This is a call from Bank Negara Malaysia. Your identity card has been flagged for fraudulent activities involving illicit funds totalling RM706,000.',score:85},
      {from:'me',text:'What? I don\'t have that kind of money!'},
      {from:'them',type:'voice',duration:22,transcript:'I am now transferring you to the police fraud department at PDRM. Do not hang up. You are under investigation for money laundering.',score:97},
      {from:'me',text:'Ok ok I\'m listening...'},
      {from:'them',text:'You are required to transfer your savings into the corporate accounts we provide for investigation. Failure to comply will result in immediate legal action, including freezing of all your bank accounts and a warrant for your arrest.',score:99},
    ]},
    { label:'📦 COD Parcel Scam', cat:'Parcel Scam', name:'Pos Laju Delivery', avatar:'https://randomuser.me/api/portraits/women/68.jpg', parts:[
      {from:'them',text:'[Pos Laju Courier]\nYth. Customer,\nThere are 2 unpaid packages under your name with total value RM60. Your package delivery has been FAILED due to incomplete payment.',score:55},
      {from:'me',text:'Huh? I didn\'t order anything recently...'},
      {from:'them',text:'Click the link below to complete payment now:\nhttps://pos-laju-pay.xyz/claim\nIf payment is not made within 30 minutes, the package will be returned to sender and a penalty fee of RM25 will be charged.',score:82},
    ]},
    { label:'💼 Fake Job – WFH RM8K', cat:'Job Scam', name:'Jenny Lim (HR)', avatar:'https://randomuser.me/api/portraits/women/33.jpg', parts:[
      {from:'them',text:'Job Offer: RM8,000 - RM15,000/month! Work from home, flexible hours. No experience needed.',score:42},
      {from:'me',text:'Sounds too good to be true... what\'s the catch?'},
      {from:'them',type:'voice',duration:20,transcript:'Simple tasks only. Like and share social media posts, leave product reviews. Daily commission paid directly to your TNG eWallet. Our company is partnered with Shopee, Lazada, and TikTok.',score:68},
      {from:'me',text:'What do I need to do to start?'},
      {from:'them',text:'We have over 200 members already earning. To start, just click the link below, register, and pay a small registration fee of RM50 + Free RM20 credited to your account as a starter bonus!',score:85},
    ]},
    { label:'📈 Investment – 10% Returns', cat:'Investment Scam', name:'FYCMAX Admin', avatar:'https://randomuser.me/api/portraits/men/45.jpg', parts:[
      {from:'them',text:'🚀 URGENT INVESTMENT ALERT 🚀\nOur special "Growth Investment" scheme is now open for new members! Guaranteed returns are paid every 30 minutes.',score:55},
      {from:'me',text:'Every 30 minutes? That doesn\'t sound real...'},
      {from:'them',text:'For every RM1,000 invested, you receive RM100 profit in just half an hour.\n✅ 0% risk\n✅ No hidden fees\n✅ Withdraw anytime',score:78},
      {from:'me',text:'How do I know this is legit?'},
      {from:'them',text:'Our members have earned over RM23,000 in just their first week! This offer will close at midnight tonight. Click here to view our profit screenshots and join our VIP group now.',score:88},
    ]},
    { label:'📮 Customs – Prohibited Items', cat:'Customs Scam', name:'Kastam Officer Azlan', avatar:'https://randomuser.me/api/portraits/men/52.jpg', parts:[
      {from:'them',text:'This is an automated message from Pos Malaysia & Customs Department. A parcel under your name containing prohibited items and an undeclared amount of cash has been detained at our warehouse.',score:72},
      {from:'me',text:'What?? I never sent any parcel with cash!'},
      {from:'them',type:'voice',duration:25,transcript:'To avoid legal charges and court summons, please contact our investigation officer immediately. Your cooperation is required within 2 hours before we escalate this matter to Bank Negara Malaysia and PDRM for further action.',score:92},
    ]},
  ];

  async function runPreset(p) {
    if (injecting) return;
    injecting=true; chatMessages=[]; currentContact=p.name; currentAvatar=p.avatar;
    for (let i=0;i<p.parts.length;i++) {
      const part=p.parts[i];
      const t=new Date().toLocaleTimeString('en-MY',{hour:'2-digit',minute:'2-digit'});
      const id=Date.now().toString(36)+Math.random().toString(36).slice(2,6);
      if (part.from==='them') {
        chatMessages=[...chatMessages,{id,from:'them',type:part.type||'text',text:part.text||'',transcript:part.transcript||'',duration:part.duration||0,time:t,scanning:true,risk_score:null}];
        await sleep(1800);
        chatMessages=chatMessages.map(m=>m.id===id?{...m,scanning:false,risk_score:part.score}:m);
        if (part.score>=80) alerts=[...alerts,{txn_id:id,sender_phone:currentContact,risk_score:part.score,status:'held',timestamp:Math.floor(Date.now()/1000),transaction_amount:Math.floor(Math.random()*8000)+1000,reason:p.cat+' — flagged by AI engine'}];
      } else {
        chatMessages=[...chatMessages,{id,from:'me',type:'text',text:part.text,time:t,scanning:false,risk_score:null}];
      }
      await sleep(1200);
    }
    injecting=false;
  }
  function sleep(ms){return new Promise(r=>setTimeout(r,ms))}

  let ticker;
  onMount(()=>{
    stopPolling=startPolling((d,e)=>{if(d.length)alerts=[...alerts,...d.filter(x=>!alerts.find(a=>a.txn_id===x.txn_id))];error=e;});
    ticker=setInterval(()=>{now=Date.now()},1000);
    healthCheck().then(()=>backendOnline=true).catch(()=>backendOnline=false);
  });
  onDestroy(()=>{if(stopPolling)stopPolling();if(ticker)clearInterval(ticker)});

  function countdown(ts){if(!ts)return'—';const d=Math.max(0,Math.floor(((ts+600)*1000-now)/1000));return d<=0?'EXPIRED':`${Math.floor(d/60)}:${(d%60).toString().padStart(2,'0')}`}
  function onApprove(id){alerts=alerts.map(a=>a.txn_id===id?{...a,status:'approved'}:a)}
  function onCancel(id){alerts=alerts.map(a=>a.txn_id===id?{...a,status:'cancelled'}:a)}
  $: pendingAlerts=alerts.filter(a=>a.status==='held'||a.status==='pending');
  $: resolvedAlerts=alerts.filter(a=>a.status==='approved'||a.status==='cancelled');
</script>

<main>
  <header>
    <div class="logo">
      <svg class="logo-wave" viewBox="0 0 48 28" width="42" height="26">
        <defs><linearGradient id="wg" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#3b82f6"/><stop offset="50%" stop-color="#06b6d4"/><stop offset="100%" stop-color="#14b8a6"/></linearGradient></defs>
        <path d="M2 18c4-10 10-16 16-12s8 8 14 6 10-8 14-4" stroke="url(#wg)" stroke-width="3.5" fill="none" stroke-linecap="round"/>
        <circle cx="36" cy="5" r="4" fill="#F59E0B" opacity=".85"/>
      </svg>
      <span class="logo-text">Fake<span class="logo-accent">out</span></span>
    </div>
  </header>

  <nav class="tabs">
    <button class:active={activeTab==='whatsapp'} on:click={()=>activeTab='whatsapp'}>
      <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
      WhatsApp Monitor
    </button>
    <button class:active={activeTab==='dashboard'} on:click={()=>activeTab='dashboard'}>
      <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
      Alert Dashboard
      {#if pendingAlerts.length>0}<span class="tab-badge">{pendingAlerts.length}</span>{/if}
    </button>
  </nav>

  {#if activeTab==='whatsapp'}
  <div class="wa-layout">
    <div class="wa-left"><WhatsAppWidget messages={chatMessages} contactName={currentContact} avatarUrl={currentAvatar}/></div>
    <div class="wa-right">
      <div class="card glass">
        <div class="card-title">Real-World Scam Scenario</div>
        <div class="card-sub">Select a scenario to simulate the scam conversation</div>
        <div class="preset-grid">
          {#each P as p}
            <button class="preset-btn" on:click={()=>runPreset(p)} disabled={injecting}>
              <img src={p.avatar} alt="" class="preset-av"/>
              <div class="preset-info"><span class="preset-label">{p.label}</span><span class="preset-cat">{p.cat}</span></div>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="#9CA3AF"><path d="M8 5v14l11-7z"/></svg>
            </button>
          {/each}
        </div>
        {#if injecting}<div class="injecting-bar"><div class="inject-pulse"></div>Scenario playing…</div>{/if}
      </div>
    </div>
  </div>
  {/if}

  {#if activeTab==='dashboard'}
  <div class="stats">
    <div class="stat-card"><div class="stat-icon">📊</div><span class="stat-n">{alerts.length}</span><span class="stat-l">Total Alerts</span></div>
    <div class="stat-card warn"><div class="stat-icon">🚨</div><span class="stat-n">{pendingAlerts.length}</span><span class="stat-l">Pending</span></div>
    <div class="stat-card ok"><div class="stat-icon">✅</div><span class="stat-n">{resolvedAlerts.length}</span><span class="stat-l">Resolved</span></div>
  </div>
  {#if pendingAlerts.length===0 && resolvedAlerts.length===0}
    <div class="empty">Run a scam scenario in WhatsApp Monitor to see detections here.</div>
  {/if}
  {#if pendingAlerts.length>0}
    <div class="section-title">🚨 Pending Review</div>
    {#each pendingAlerts as a (a.txn_id)}
      <div class="alert-card">
        <div class="a-score-ring"><span>{a.risk_score}</span></div>
        <div class="a-body">
          <div class="a-top"><span class="a-tag">CRITICAL</span><span class="a-timer">⏱ {countdown(a.timestamp)}</span></div>
          <div class="a-row"><span>From</span><span>{a.sender_phone}</span></div>
          <div class="a-row"><span>Amount</span><span>RM {a.transaction_amount?.toLocaleString('en-MY',{minimumFractionDigits:2})}</span></div>
          <div class="a-row"><span>Reason</span><span class="a-reason">{a.reason}</span></div>
          
          {#if a.transcript}
            <div class="a-voice-scrutiny">
              <div class="a-scrutiny-header">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>
                AI Voice Transcript
              </div>
              <p class="a-transcript">"{a.transcript}"</p>
              
              {#if a.translation}
                <div class="a-translation-box">
                  <div class="a-scrutiny-header" style="color: #A855F7">
                    <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/></svg>
                    English Translation
                  </div>
                  <p class="a-transcript">"{a.translation}"</p>
                </div>
              {/if}
            </div>
          {/if}
          <div class="a-actions">
            <button class="btn-block" on:click={()=>onCancel(a.txn_id)}>🚫 Block & Cancel</button>
            <button class="btn-approve" on:click={()=>onApprove(a.txn_id)}>✅ Approve</button>
          </div>
        </div>
      </div>
    {/each}
  {/if}
  {#if resolvedAlerts.length>0}
    <div class="section-title" style="margin-top:24px">📋 Resolved</div>
    {#each resolvedAlerts as a (a.txn_id)}
      <div class="resolved-row">
        <span class="r-stat" class:approved={a.status==='approved'} class:cancelled={a.status==='cancelled'}>{a.status==='approved'?'✅':'🚫'} {a.status}</span>
        <span>{a.sender_phone}</span><span>Score: {a.risk_score}</span><span>RM {a.transaction_amount?.toFixed(2)}</span>
      </div>
    {/each}
  {/if}
  {/if}

  <footer>Fakeout · TNG Digital FINHACK 2026</footer>
</main>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');
  :global(*){margin:0;padding:0;box-sizing:border-box}
  :global(body){font-family:'Inter',system-ui,sans-serif;background:#121212;color:#E5E7EB;min-height:100vh}
  main{max-width:1240px;margin:0 auto;padding:20px 28px 60px}

  /* Logo */
  header{padding:20px 0 16px;display:flex;align-items:center}
  .logo{display:flex;align-items:center;gap:12px}
  .logo-wave{filter:drop-shadow(0 2px 8px rgba(20,184,166,.3))}
  .logo-text{font-family:'Space Grotesk',sans-serif;font-size:1.6rem;font-weight:700;color:#E5E7EB;letter-spacing:-.03em}
  .logo-accent{background:linear-gradient(135deg,#14B8A6,#06b6d4);-webkit-background-clip:text;-webkit-text-fill-color:transparent}

  /* Tabs */
  .tabs{display:flex;gap:4px;margin-bottom:24px;background:#1E2A32;border-radius:12px;padding:4px}
  .tabs button{flex:1;padding:10px 16px;background:none;border:none;font-size:.82rem;font-weight:600;color:#9CA3AF;cursor:pointer;border-radius:8px;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px}
  .tabs button:hover{color:#E5E7EB}
  .tabs button.active{background:rgba(20,184,166,.15);color:#14B8A6;box-shadow:0 0 12px rgba(20,184,166,.1)}
  .tab-badge{background:#DC2626;color:#fff;font-size:.62rem;font-weight:700;padding:1px 7px;border-radius:10px;min-width:18px;text-align:center;animation:badgePulse 2s ease-in-out infinite}
  @keyframes badgePulse{0%,100%{box-shadow:0 0 0 0 rgba(220,38,38,.4)}50%{box-shadow:0 0 0 6px rgba(220,38,38,0)}}

  .wa-layout{display:grid;grid-template-columns:420px 1fr;gap:24px;align-items:start}

  /* Glass card */
  .card{background:rgba(30,42,50,.6);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:20px}
  .glass{box-shadow:0 8px 32px rgba(0,0,0,.3)}
  .card-title{font-size:.9rem;font-weight:700;color:#E5E7EB;margin-bottom:4px}
  .card-sub{font-size:.72rem;color:#9CA3AF;margin-bottom:14px}

  .preset-grid{display:flex;flex-direction:column;gap:6px}
  .preset-btn{display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid rgba(255,255,255,.06);border-radius:12px;background:rgba(255,255,255,.03);cursor:pointer;transition:all .15s;text-align:left}
  .preset-btn:hover:not(:disabled){background:rgba(20,184,166,.08);border-color:rgba(20,184,166,.2);transform:translateY(-1px);box-shadow:0 4px 16px rgba(0,0,0,.2)}
  .preset-btn:disabled{opacity:.35;cursor:not-allowed}
  .preset-av{width:36px;height:36px;border-radius:50%;object-fit:cover;flex-shrink:0;border:2px solid rgba(255,255,255,.1)}
  .preset-info{flex:1;display:flex;flex-direction:column;gap:2px}
  .preset-label{font-size:.78rem;font-weight:500;color:#E5E7EB}
  .preset-cat{font-size:.62rem;color:#9CA3AF}
  .injecting-bar{margin-top:12px;padding:10px 14px;border-radius:10px;background:rgba(20,184,166,.08);border:1px solid rgba(20,184,166,.2);color:#14B8A6;font-size:.78rem;font-weight:600;display:flex;align-items:center;gap:8px}
  .inject-pulse{width:8px;height:8px;border-radius:50%;background:#14B8A6;animation:pulseDot 1.5s ease-in-out infinite}
  @keyframes pulseDot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}

  /* Dashboard */
  .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}
  .stat-card{background:rgba(30,42,50,.6);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:20px;text-align:center;position:relative;overflow:hidden}
  .stat-card::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#14B8A6,#06b6d4)}
  .stat-card.warn::after{background:linear-gradient(90deg,#DC2626,#F59E0B)}
  .stat-card.ok::after{background:linear-gradient(90deg,#10B981,#14B8A6)}
  .stat-icon{font-size:1.4rem;margin-bottom:4px}
  .stat-n{display:block;font-size:2.2rem;font-weight:800;font-family:'Space Grotesk',sans-serif}
  .stat-l{font-size:.7rem;color:#9CA3AF;text-transform:uppercase;letter-spacing:.06em}
  .stat-card.warn .stat-n{color:#DC2626}
  .stat-card.ok .stat-n{color:#10B981}

  .section-title{font-size:.9rem;font-weight:700;margin-bottom:10px;color:#E5E7EB}
  .empty{background:rgba(30,42,50,.6);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:48px;text-align:center;color:#9CA3AF;font-size:.85rem}

  .alert-card{display:flex;gap:16px;background:rgba(30,42,50,.6);backdrop-filter:blur(12px);border:1px solid rgba(220,38,38,.25);border-radius:16px;padding:20px;margin-bottom:12px;box-shadow:0 0 20px rgba(220,38,38,.05)}
  .a-score-ring{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;background:rgba(220,38,38,.12);border:2px solid rgba(220,38,38,.4)}
  .a-score-ring span{font-size:1.2rem;font-weight:800;color:#f87171;font-family:'Space Grotesk',sans-serif}
  .a-body{flex:1}
  .a-top{display:flex;justify-content:space-between;margin-bottom:10px}
  .a-tag{font-size:.68rem;font-weight:700;text-transform:uppercase;padding:3px 10px;border-radius:6px;background:rgba(220,38,38,.15);color:#f87171;letter-spacing:.04em}
  .a-timer{font-size:.78rem;color:#9CA3AF}
  .a-row{display:flex;justify-content:space-between;padding:4px 0;font-size:.8rem;border-bottom:1px solid rgba(255,255,255,.04)}
  .a-row span:first-child{color:#9CA3AF}
  .a-reason{color:#F59E0B;font-size:.78rem;max-width:260px;text-align:right}
  .a-actions{display:flex;gap:8px;margin-top:14px}
  .btn-block,.btn-approve{flex:1;padding:10px;border:none;border-radius:10px;font-size:.78rem;font-weight:600;cursor:pointer;transition:all .15s}
  .btn-block{background:rgba(220,38,38,.12);color:#f87171;border:1px solid rgba(220,38,38,.3)}
  .btn-block:hover{background:rgba(220,38,38,.2)}
  .btn-approve{background:rgba(20,184,166,.12);color:#14B8A6;border:1px solid rgba(20,184,166,.3)}
  .btn-approve:hover{background:rgba(20,184,166,.2)}
  .resolved-row{display:flex;align-items:center;gap:16px;padding:12px 16px;background:rgba(30,42,50,.4);border:1px solid rgba(255,255,255,.04);border-radius:10px;margin-bottom:6px;font-size:.78rem;color:#9CA3AF}
  .r-stat{font-weight:700;text-transform:uppercase;font-size:.68rem;min-width:100px}
  .r-stat.approved{color:#10B981}.r-stat.cancelled{color:#DC2626}

  /* Voice Scrutiny Styles */
  .a-voice-scrutiny {
    margin-top: 14px;
    padding: 12px;
    background: rgba(0, 0, 0, 0.25);
    border-radius: 10px;
    border: 1px solid rgba(59, 130, 246, 0.2);
  }
  .a-scrutiny-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.65rem;
    font-weight: 800;
    text-transform: uppercase;
    color: #3B82F6;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }
  .a-transcript {
    font-size: 0.8rem;
    color: #E5E7EB;
    line-height: 1.4;
    font-style: italic;
  }
  .a-translation-box {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
  }

  footer{text-align:center;padding:32px 0 16px;color:#9CA3AF;font-size:.7rem}
  @media(max-width:900px){.wa-layout{grid-template-columns:1fr}.stats{grid-template-columns:1fr}}
</style>
