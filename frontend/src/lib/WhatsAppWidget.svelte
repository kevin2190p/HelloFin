<script>
  import { onMount, onDestroy } from 'svelte';
  export let demoMode = false;

  let messages = [];
  let chatBottom;
  let pollInterval;

  function riskClass(s) { return s >= 80 ? 'crit' : s >= 50 ? 'warn' : 'safe'; }
  function scrollBottom() { setTimeout(() => chatBottom?.scrollIntoView({ behavior: 'smooth' }), 60); }

  const DEMO_SCRIPT = [
    { from:'them', type:'text', delay:800, text:'Selamat petang. Saya dari Jabatan Kastam Diraja Malaysia. Bungkusan anda telah ditahan di KLIA.' },
    { from:'me', type:'text', delay:4000, text:'Hah? Saya tak pesan apa-apa pun...' },
    { from:'them', type:'text', delay:7000, text:'Kes jenayah serius telah dibuka. Transfer RM 4,800 ke akaun selamat kami sekarang: Maybank 5621-4489-0012. Jangan beritahu sesiapa!' },
    { from:'them', type:'voice', delay:11000, duration:22, text:'Hello this is Inspector Rajan from PDRM. We have a warrant for your arrest. Transfer five thousand ringgit to the safe account immediately. Do not tell your family.' },
  ];

  async function pollMessages() {
    try {
      const res = await fetch('http://localhost:8000/chat/messages');
      if (!res.ok) return;
      messages = await res.json();
      scrollBottom();
    } catch (_) {}
  }

  function runDemo() {
    messages = [];
    DEMO_SCRIPT.forEach(step => {
      setTimeout(() => {
        const msg = { id: Math.random().toString(36).slice(2), from: step.from, type: step.type, text: step.text, duration: step.duration||0, time: new Date().toLocaleTimeString('en-MY',{hour:'2-digit',minute:'2-digit'}), scanning: step.from==='them', risk_score:null, risk_level:null, llm_label:null };
        messages = [...messages, msg];
        scrollBottom();
        if (step.from === 'them') {
          setTimeout(() => {
            const score = step.type==='voice' ? 97 : step.text.includes('Transfer') ? 95 : 72;
            messages = messages.map(m => m.id===msg.id ? {...m, scanning:false, risk_score:score, risk_level:score>=80?'HIGH':'MEDIUM', llm_label:score>=80?'Macau Scam':'Suspicious'} : m);
            scrollBottom();
          }, 2200);
        }
      }, step.delay);
    });
  }

  onMount(() => { if (demoMode) runDemo(); else { pollMessages(); pollInterval = setInterval(pollMessages, 3000); } });
  onDestroy(() => { if (pollInterval) clearInterval(pollInterval); });
</script>

<div class="wa">
  <div class="wa-hdr">
    <div class="back-btn">←</div>
    <div class="av"><span class="av-icon">👤</span></div>
    <div class="contact"><div class="name">Unknown (+60163569782)</div><div class="sub">{demoMode ? 'Demo Mode' : 'online'}</div></div>
    <div class="hdr-icons"><span>📹</span><span>📞</span><span>⋮</span></div>
  </div>

  <div class="wa-chat" id="wa-chat">
    <div class="date-chip">Today</div>

    {#each messages as msg (msg.id)}
      <div class="msg-row" class:me={msg.from==='me'} class:them={msg.from==='them'}>
        <div class="bubble" class:me={msg.from==='me'} class:them={msg.from==='them'}>
          {#if msg.type === 'voice'}
            <div class="voice">
              <div class="v-play">▶</div>
              <div class="v-wave">
                {#each Array(25) as _, i}
                  <div class="v-bar" style="height:{4+Math.abs(Math.sin(i*0.7))*14}px"></div>
                {/each}
              </div>
              <div class="v-dur">{Math.floor(msg.duration/60)}:{(msg.duration%60).toString().padStart(2,'0')}</div>
            </div>
            <div class="meta"><span class="time">{msg.time}</span></div>
          {:else}
            <p class="text">{msg.text}</p>
            <div class="meta">
              <span class="time">{msg.time}</span>
              {#if msg.from==='me'}<span class="ticks">✓✓</span>{/if}
            </div>
          {/if}

          {#if msg.scanning}
            <div class="scan-bar"><div class="scan-dots"><span></span><span></span><span></span></div><span class="scan-txt">AI Scanning…</span></div>
          {/if}

          {#if msg.risk_score !== null && !msg.scanning}
            <div class="risk-badge {riskClass(msg.risk_score)}">
              <span class="r-icon">{msg.risk_score>=80?'🚨':msg.risk_score>=50?'⚠️':'✅'}</span>
              <strong>{msg.risk_score}/100</strong>
              <span class="r-label">{msg.risk_level}</span>
            </div>
          {/if}
        </div>
      </div>
    {/each}

    {#if messages.length===0}
      <div class="empty-chat">
        <p>Monitoring <strong>+60163569782</strong></p>
        <p class="empty-sub">{demoMode?'Demo starting…':'Waiting for messages…'}</p>
      </div>
    {/if}
    <div bind:this={chatBottom}></div>
  </div>

  <div class="wa-input">
    <span class="inp-emoji">😊</span>
    <div class="inp-field">Message</div>
    <span class="inp-clip">📎</span>
    <span class="inp-cam">📷</span>
    <div class="inp-mic">🎤</div>
  </div>
</div>

{#if demoMode}<button class="replay" on:click={runDemo}>↺ Replay</button>{/if}

<style>
  .wa{width:100%;max-width:420px;height:600px;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;background:#efeae2;box-shadow:0 4px 24px rgba(0,0,0,.12);border:1px solid #d1d1d1;font-family:-apple-system,'Segoe UI',sans-serif}

  /* Header - WhatsApp teal */
  .wa-hdr{background:#008069;padding:8px 12px;display:flex;align-items:center;gap:10px;flex-shrink:0}
  .back-btn{color:#fff;font-size:1.2rem;cursor:pointer}
  .av{width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0}
  .contact{flex:1}.name{font-size:.88rem;font-weight:500;color:#fff}.sub{font-size:.7rem;color:rgba(255,255,255,.7)}
  .hdr-icons{display:flex;gap:16px;color:rgba(255,255,255,.9);font-size:1rem}

  /* Chat area - WhatsApp wallpaper beige */
  .wa-chat{flex:1;overflow-y:auto;padding:8px 12px;background:#efeae2;
    background-image:url("data:image/svg+xml,%3Csvg width='300' height='300' xmlns='http://www.w3.org/2000/svg'%3E%3Cdefs%3E%3Cpattern id='p' width='40' height='40' patternUnits='userSpaceOnUse'%3E%3Cpath d='M20 0L20 40M0 20L40 20' stroke='%23d6cfc4' stroke-width='0.3'/%3E%3C/pattern%3E%3C/defs%3E%3Crect fill='url(%23p)' width='300' height='300'/%3E%3C/svg%3E");
    display:flex;flex-direction:column;gap:3px}
  .wa-chat::-webkit-scrollbar{width:4px}
  .wa-chat::-webkit-scrollbar-thumb{background:rgba(0,0,0,.15);border-radius:2px}

  .date-chip{text-align:center;font-size:.68rem;color:#54656f;background:rgba(255,255,255,.85);border-radius:8px;padding:3px 10px;margin:6px auto 8px;width:fit-content;box-shadow:0 1px 1px rgba(0,0,0,.06)}

  .msg-row{display:flex;margin-bottom:2px;animation:msgIn .2s ease-out}
  @keyframes msgIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
  .msg-row.me{justify-content:flex-end}
  .msg-row.them{justify-content:flex-start}

  /* Bubbles - exact WA colors */
  .bubble{max-width:80%;border-radius:8px;padding:6px 8px 4px;position:relative;box-shadow:0 1px 1px rgba(0,0,0,.08)}
  .bubble.me{background:#d9fdd3;border-top-right-radius:2px;color:#111b21}
  .bubble.them{background:#fff;border-top-left-radius:2px;color:#111b21}

  .text{font-size:.88rem;line-height:1.4;margin:0 0 2px;word-break:break-word}
  .meta{display:flex;justify-content:flex-end;align-items:center;gap:3px;margin-top:1px}
  .time{font-size:.65rem;color:#667781}
  .ticks{font-size:.6rem;color:#53bdeb}

  /* Voice note */
  .voice{display:flex;align-items:center;gap:8px;padding:4px 0;min-width:200px}
  .v-play{width:28px;height:28px;border-radius:50%;background:#00a884;color:#fff;display:flex;align-items:center;justify-content:center;font-size:.7rem;cursor:pointer;flex-shrink:0}
  .v-wave{display:flex;align-items:center;gap:1.5px;height:24px;flex:1}
  .v-bar{width:2.5px;background:#8696a0;border-radius:2px}
  .v-dur{font-size:.68rem;color:#667781;flex-shrink:0}

  /* Scan bar */
  .scan-bar{display:flex;align-items:center;gap:6px;margin-top:4px;padding:4px 8px;border-radius:6px;background:rgba(0,113,227,.08);border:1px solid rgba(0,113,227,.2)}
  .scan-dots{display:flex;gap:3px}
  .scan-dots span{width:4px;height:4px;border-radius:50%;background:#0071e3;animation:sp .8s ease-in-out infinite}
  .scan-dots span:nth-child(2){animation-delay:.15s}
  .scan-dots span:nth-child(3){animation-delay:.3s}
  @keyframes sp{0%,100%{opacity:.3;transform:scale(.7)}50%{opacity:1;transform:scale(1)}}
  .scan-txt{font-size:.65rem;color:#0071e3;font-weight:600}

  /* Risk badge */
  .risk-badge{display:flex;align-items:center;gap:6px;margin-top:4px;padding:4px 8px;border-radius:6px;font-size:.72rem;animation:bIn .3s ease-out}
  @keyframes bIn{from{opacity:0;transform:scale(.9)}to{opacity:1;transform:scale(1)}}
  .risk-badge.crit{background:#fce4e4;border:1px solid #ef9a9a;color:#c62828}
  .risk-badge.warn{background:#fff8e1;border:1px solid #ffe082;color:#e65100}
  .risk-badge.safe{background:#e8f5e9;border:1px solid #a5d6a7;color:#2e7d32}
  .r-icon{font-size:.9rem}
  .r-label{font-size:.62rem;text-transform:uppercase;letter-spacing:.04em;opacity:.8}

  .empty-chat{text-align:center;padding:40px 20px;color:#667781;font-size:.82rem}
  .empty-chat strong{color:#c62828}
  .empty-sub{font-size:.7rem;margin-top:6px;color:#8696a0}

  /* Input bar */
  .wa-input{background:#f0f2f5;padding:6px 8px;display:flex;align-items:center;gap:6px;flex-shrink:0}
  .inp-emoji,.inp-clip,.inp-cam{font-size:1.1rem;color:#54656f;cursor:pointer}
  .inp-field{flex:1;background:#fff;border-radius:20px;padding:8px 14px;font-size:.85rem;color:#667781;border:none}
  .inp-mic{width:36px;height:36px;border-radius:50%;background:#00a884;display:flex;align-items:center;justify-content:center;font-size:.9rem;cursor:pointer}

  .replay{display:block;margin:8px auto 0;background:#e8f5e9;color:#2e7d32;border:1px solid #a5d6a7;border-radius:16px;padding:6px 18px;font-size:.75rem;font-weight:600;cursor:pointer}
  .replay:hover{background:#c8e6c9}
</style>
