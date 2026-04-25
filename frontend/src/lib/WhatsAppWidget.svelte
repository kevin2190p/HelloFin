<script>
  export let messages = [];
  import { afterUpdate } from 'svelte';

  let chatEl;
  function riskClass(s) { return s >= 80 ? 'crit' : s >= 50 ? 'warn' : 'safe'; }
  afterUpdate(() => { if (chatEl) chatEl.scrollTop = chatEl.scrollHeight; });
</script>

<div class="wa">
  <!-- Header -->
  <div class="wa-hdr">
    <div class="back-btn">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="#fff"><path d="M12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2H7.83l5.58-5.59z"/></svg>
    </div>
    <div class="av"><svg viewBox="0 0 212 212" width="36" height="36"><path fill="#DFE5E7" d="M106.251.5C164.653.5 212 47.846 212 106.25S164.653 212 106.25 212C47.846 212 .5 164.654.5 106.25S47.846.5 106.251.5z"/><path fill="#FFF" d="M173.561 171.615a62.767 62.767 0 0 0-2.065-2.955 67.7 67.7 0 0 0-2.608-3.299 70.112 70.112 0 0 0-3.184-3.527 71.097 71.097 0 0 0-5.924-5.47 72.458 72.458 0 0 0-10.204-7.026L138.1 143.1a72.584 72.584 0 0 0-9.95-4.298c-.185-.068-.374-.122-.56-.187-.039-.014-.082-.03-.122-.044l-.356-.122c-.232-.083-.467-.157-.7-.235a38.605 38.605 0 0 0 9.752-25.964c0-21.393-17.407-38.8-38.8-38.8s-38.8 17.407-38.8 38.8a38.6 38.6 0 0 0 9.752 25.964c-.233.078-.468.152-.7.235l-.356.122c-.04.014-.082.03-.122.044-.186.065-.375.119-.56.187a72.584 72.584 0 0 0-9.95 4.298l-11.476 6.238a72.381 72.381 0 0 0-10.204 7.026 71.097 71.097 0 0 0-5.924 5.47 70.08 70.08 0 0 0-3.184 3.527 67.7 67.7 0 0 0-2.608 3.299 62.767 62.767 0 0 0-2.065 2.955A56.33 56.33 0 0 0 28 186.074c16.907 16.063 39.59 25.926 64.25 25.926 24.662 0 47.344-9.863 64.252-25.926a56.391 56.391 0 0 0-3.94-14.459z"/></svg></div>
    <div class="contact"><div class="name">Scammer</div><div class="sub">online</div></div>
    <div class="hdr-icons">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="rgba(255,255,255,.85)"><path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/></svg>
      <svg viewBox="0 0 24 24" width="20" height="20" fill="rgba(255,255,255,.85)"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="rgba(255,255,255,.85)"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>
    </div>
  </div>

  <!-- Chat -->
  <div class="wa-chat" bind:this={chatEl}>
    <div class="date-chip">Today</div>
    {#each messages as msg (msg.id)}
      <div class="msg-row" class:me={msg.from==='me'} class:them={msg.from==='them'}>
        <div class="bubble" class:me={msg.from==='me'} class:them={msg.from==='them'}>
          {#if msg.type === 'voice'}
            <div class="voice">
              <div class="v-play"><svg viewBox="0 0 24 24" width="14" height="14" fill="#fff"><path d="M8 5v14l11-7z"/></svg></div>
              <div class="v-wave">{#each Array(25) as _, i}<div class="v-bar" style="height:{4+Math.abs(Math.sin(i*0.7))*14}px"></div>{/each}</div>
              <div class="v-dur">{Math.floor((msg.duration||0)/60)}:{((msg.duration||0)%60).toString().padStart(2,'0')}</div>
            </div>
          {:else}
            <p class="text">{msg.text}</p>
          {/if}
          <div class="meta">
            <span class="time">{msg.time}</span>
            {#if msg.from==='me'}<span class="ticks"><svg viewBox="0 0 16 11" width="16" height="11" fill="#53bdeb"><path d="M11.07.66L5.87 7.75 3.26 5.08l-.93.94L5.87 9.7l6.13-8.1-.93-.94z"/><path d="M7.59.66L2.39 7.75-.22 5.08l-.93.94L2.39 9.7l6.13-8.1-.93-.94z"/></svg></span>{/if}
          </div>

          {#if msg.scanning}
            <div class="scan-bar"><div class="scan-dots"><span></span><span></span><span></span></div><span class="scan-txt">AI Scanning…</span></div>
          {/if}
          {#if msg.risk_score !== null && msg.risk_score !== undefined && !msg.scanning}
            <div class="risk-badge {riskClass(msg.risk_score)}">
              <span class="r-icon">{msg.risk_score>=80?'🚨':msg.risk_score>=50?'⚠️':'✅'}</span>
              <strong>{msg.risk_score}/100</strong>
              <span class="r-label">{msg.risk_score>=80?'HIGH':msg.risk_score>=50?'MEDIUM':'CLEARED'}</span>
            </div>
          {/if}
        </div>
      </div>
    {/each}
    {#if messages.length===0}
      <div class="empty-chat"><p>No messages yet</p></div>
    {/if}
  </div>

  <!-- Input bar -->
  <div class="wa-input">
    <svg viewBox="0 0 24 24" width="22" height="22" fill="#8696a0"><circle cx="9" cy="9" r="1.5"/><circle cx="15" cy="9" r="1.5"/><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm-5-6c.78 2.34 2.72 4 5 4s4.22-1.66 5-4H7z"/></svg>
    <div class="inp-field">Message</div>
    <svg viewBox="0 0 24 24" width="22" height="22" fill="#8696a0"><path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/></svg>
    <svg viewBox="0 0 24 24" width="22" height="22" fill="#8696a0"><circle cx="12" cy="12" r="3.2"/><path d="M9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z"/></svg>
    <div class="inp-mic"><svg viewBox="0 0 24 24" width="20" height="20" fill="#fff"><path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/></svg></div>
  </div>
</div>

<style>
  .wa{width:100%;max-width:420px;height:620px;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;background:#efeae2;box-shadow:0 4px 24px rgba(0,0,0,.12);border:1px solid #d1d1d1;font-family:-apple-system,'Segoe UI',sans-serif}
  .wa-hdr{background:#008069;padding:8px 12px;display:flex;align-items:center;gap:10px;flex-shrink:0}
  .back-btn{cursor:pointer;display:flex}
  .av{width:36px;height:36px;border-radius:50%;overflow:hidden;flex-shrink:0}
  .contact{flex:1}.name{font-size:.88rem;font-weight:500;color:#fff}.sub{font-size:.7rem;color:rgba(255,255,255,.7)}
  .hdr-icons{display:flex;gap:14px;align-items:center}

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

  .bubble{max-width:80%;border-radius:8px;padding:6px 8px 4px;position:relative;box-shadow:0 1px 1px rgba(0,0,0,.08)}
  .bubble.me{background:#d9fdd3;border-top-right-radius:2px;color:#111b21}
  .bubble.them{background:#fff;border-top-left-radius:2px;color:#111b21}

  .text{font-size:.88rem;line-height:1.4;margin:0 0 2px;word-break:break-word;white-space:pre-wrap}
  .meta{display:flex;justify-content:flex-end;align-items:center;gap:3px;margin-top:1px}
  .time{font-size:.65rem;color:#667781}
  .ticks{display:flex;align-items:center}

  .voice{display:flex;align-items:center;gap:8px;padding:4px 0;min-width:200px}
  .v-play{width:28px;height:28px;border-radius:50%;background:#00a884;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0}
  .v-wave{display:flex;align-items:center;gap:1.5px;height:24px;flex:1}
  .v-bar{width:2.5px;background:#8696a0;border-radius:2px}
  .v-dur{font-size:.68rem;color:#667781;flex-shrink:0}

  .scan-bar{display:flex;align-items:center;gap:6px;margin-top:4px;padding:4px 8px;border-radius:6px;background:rgba(0,113,227,.08);border:1px solid rgba(0,113,227,.2)}
  .scan-dots{display:flex;gap:3px}
  .scan-dots span{width:4px;height:4px;border-radius:50%;background:#0071e3;animation:sp .8s ease-in-out infinite}
  .scan-dots span:nth-child(2){animation-delay:.15s}
  .scan-dots span:nth-child(3){animation-delay:.3s}
  @keyframes sp{0%,100%{opacity:.3;transform:scale(.7)}50%{opacity:1;transform:scale(1)}}
  .scan-txt{font-size:.65rem;color:#0071e3;font-weight:600}

  .risk-badge{display:flex;align-items:center;gap:6px;margin-top:4px;padding:4px 8px;border-radius:6px;font-size:.72rem;animation:bIn .3s ease-out}
  @keyframes bIn{from{opacity:0;transform:scale(.9)}to{opacity:1;transform:scale(1)}}
  .risk-badge.crit{background:#fce4e4;border:1px solid #ef9a9a;color:#c62828}
  .risk-badge.warn{background:#fff8e1;border:1px solid #ffe082;color:#e65100}
  .risk-badge.safe{background:#e8f5e9;border:1px solid #a5d6a7;color:#2e7d32}
  .r-icon{font-size:.9rem}
  .r-label{font-size:.62rem;text-transform:uppercase;letter-spacing:.04em;opacity:.8}

  .empty-chat{text-align:center;padding:40px 20px;color:#667781;font-size:.82rem}

  .wa-input{background:#f0f2f5;padding:6px 8px;display:flex;align-items:center;gap:8px;flex-shrink:0}
  .inp-field{flex:1;background:#fff;border-radius:20px;padding:8px 14px;font-size:.85rem;color:#667781;border:none}
  .inp-mic{width:36px;height:36px;border-radius:50%;background:#00a884;display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0}
</style>
