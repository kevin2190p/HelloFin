<script>
  import { onMount, onDestroy } from "svelte";
  import {
    startPolling,
    handleApprove,
    handleCancel,
    formatTime,
  } from "./lib/caregiverDashboard.js";
  import { healthCheck, scoreRisk } from "./lib/api.js";
  import WhatsAppWidget from "./lib/WhatsAppWidget.svelte";

  let alerts = [],
    error = null,
    stopPolling,
    backendOnline = false,
    now = Date.now(),
    actionLoading = {},
    actionResult = {};

  let activeTab = "monitor"; // Default to monitor based on images
  let ticker;

  // --- Scenario Simulation Logic ---
  let selectedScenario = null;
  let chatMessages = [];
  let isTyping = false;
  let currentContact = { name: "Unknown", avatar: "" };

  const SCENARIOS = [
    {
      id: "insta",
      name: "Instagram Verification",
      type: "Phishing",
      avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Instagram",
      contact: "Instagram Support",
      flow: [
        {
          from: "them",
          text: "02172269 is your verification code. Enter this code in the Instagram app to verify your account. For your security, do not share this code. Instagram will never ask you to share this code by phone call or email.",
          risk_score: 30,
        },
        { from: "me", text: "Hmm I didn't request any code... who is this?" },
        {
          from: "them",
          text: "This is Instagram support. Your account has been flagged for suspicious activity. Please share the code now or your account will be permanently disabled within 1 hour.",
          risk_score: 82,
        },
        {
          from: "me",
          text: "Wait, Instagram wouldn't message me on WhatsApp right? This is suspicious...",
        },
      ],
    },
    {
      id: "macau",
      name: "Sgt. Michael – Macau Scam",
      type: "Police Scam",
      avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Michael",
      contact: "Sgt. Michael (PDRM)",
      flow: [
        {
          from: "them",
          text: "Saya Sarjan Michael dari IPD Bukit Aman. Nama anda telah dikaitkan dengan kes pengubahan wang haram bernilai RM200,000.",
          risk_score: 45,
        },
        {
          from: "me",
          text: "Hah? Biar betul? Saya tak pernah buat macam tu pun.",
        },
        {
          from: "them",
          text: "Waran tangkap telah dikeluarkan. Jangan beritahu sesiapa atau akaun bank anda akan dibekukan serta-merta untuk siasatan.",
          risk_score: 92,
        },
        {
          from: "me",
          text: "Tolong jangan bekukan akaun saya, itu duit simpanan saya!",
        },
      ],
    },
    {
      id: "friend",
      name: "Fake Friend – Phone Rosak",
      type: "Emergency Scam",
      avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Friend",
      contact: "Old Friend",
      flow: [
        {
          from: "them",
          text: "Wei, ni aku. Phone lama aku pecah/rosak, ni no baru aku. Save no ni jap.",
          risk_score: 25,
        },
        { from: "me", text: "Oh ye ke? Sape ni? Ali ke?" },
        {
          from: "them",
          text: "Haah Ali la ni. Weh, aku tgh kat bengkel ni, urgent gila nak bayar tapi bank app aku takleh masuk kat phone ni. Boleh pinjam RM500 tak? Malam nanti aku bayar balik.",
          risk_score: 75,
        },
      ],
    },
    {
      id: "voice",
      name: "Deepfake Voice – Help Me",
      type: "Family Scam",
      avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Family",
      contact: "Family Member",
      flow: [
        {
          from: "them",
          type: "voice",
          text: "Mak, tolong mak! Orang tangkap saya!",
          transcript: "Mak, tolong mak! Orang tangkap saya! Saya kena culik!",
          duration: 12,
          risk_score: 88,
        },
        { from: "me", text: "Ya Allah! Sape ni? Adik ke?" },
        {
          from: "them",
          text: "Jangan call polis! Kalau mak call polis, kitorang bunuh dia. Transfer RM10k sekarang ke akaun ni kalau nak dia selamat.",
          risk_score: 98,
        },
      ],
    },
    {
      id: "lhdn",
      name: "Bank Negara / LHDN",
      type: "Authority Scam",
      avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Tax",
      contact: "Official LHDN",
      flow: [
        {
          from: "them",
          text: "Notis Peringatan Akhir: Anda mempunyai tunggakan cukai berjumlah RM5,430.20 yang belum dijelaskan bagi tahun taksiran 2023.",
          risk_score: 35,
        },
        { from: "me", text: "Tapi saya dah bayar semua cukai saya." },
        {
          from: "them",
          text: "Sila klik pautan ini untuk pengesahan bayaran atau tindakan undang-undang akan diambil dalam masa 24 jam: http://lhdn-portal-safe.com/verify",
          risk_score: 85,
        },
      ],
    },
    {
      id: "parcel",
      name: "COD Parcel Scam",
      type: "Parcel Scam",
      avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Parcel",
      contact: "NinjaVan Delivery",
      flow: [
        {
          from: "them",
          text: "Hello, saya runner NinjaVan. Ada barang COD RM180 untuk alamat ni. Tuan/puan ada kat rumah?",
          risk_score: 20,
        },
        { from: "me", text: "Barang apa ya? Saya tak rasa ada order apa-apa." },
        {
          from: "them",
          text: "Kat sini tulis barang dari 'Overseas Gadget'. Kalau tak bayar sekarang, kitorang kena return. Bagus bayar je, ramai orang beli benda ni.",
          risk_score: 55,
        },
      ],
    },
    {
      id: "job",
      name: "Fake Job – WFH RM8K",
      type: "Job Scam",
      avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Job",
      contact: "HR Manager",
      flow: [
        {
          from: "them",
          text: "Tahniah! Resume anda telah terpilih untuk jawatan Data Entry (WFH). Gaji RM300-RM500 sehari. Berminat?",
          risk_score: 30,
        },
        { from: "me", text: "Ya, berminat. Macam mana nak mula?" },
        {
          from: "them",
          text: "Anda cuma perlu beli inventory dulu untuk start task. Masukkan RM200 ke akaun company untuk aktifkan portal kerja anda.",
          risk_score: 70,
        },
      ],
    },
  ];

  async function runScenario(scenario) {
    selectedScenario = scenario;
    currentContact = { name: scenario.contact, avatar: scenario.avatar };
    chatMessages = [];

    for (const step of scenario.flow) {
      if (step.from === "them") {
        isTyping = true;
        await new Promise((r) => setTimeout(r, 1000));

        let newMsg = {
          id: Date.now(),
          from: "them",
          text: step.text,
          type: step.type || "text",
          transcript: step.transcript,
          duration: step.duration,
          time: new Date()
            .toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              hour12: true,
            })
            .toLowerCase(),
          scanning: true,
        };
        chatMessages = [...chatMessages, newMsg];

        // Simulate AI Analysis
        await new Promise((r) => setTimeout(r, 1500));

        // Real-time API call for scanning (Optional, here we use preset scores for demo but could call backend)
        const scanResult = await scoreRisk({ transcript: step.text }).catch(
          () => null,
        );
        const finalScore = scanResult ? scanResult.risk_score : step.risk_score;

        chatMessages = chatMessages.map((m) =>
          m.id === newMsg.id
            ? { ...m, scanning: false, risk_score: finalScore }
            : m,
        );
        isTyping = false;
      } else {
        await new Promise((r) => setTimeout(r, 800));
        chatMessages = [
          ...chatMessages,
          {
            id: Date.now(),
            from: "me",
            text: step.text,
            time: new Date()
              .toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                hour12: true,
              })
              .toLowerCase(),
          },
        ];
      }
      await new Promise((r) => setTimeout(r, 1000));
    }
  }

  // --- Caregiver Dashboard Logic ---
  onMount(() => {
    stopPolling = startPolling((d, e) => {
      if (d) alerts = d;
      error = e;
    });
    ticker = setInterval(() => {
      now = Date.now();
    }, 1000);
    healthCheck()
      .then(() => (backendOnline = true))
      .catch(() => (backendOnline = false));
  });
  onDestroy(() => {
    if (stopPolling) stopPolling();
    if (ticker) clearInterval(ticker);
  });

  function countdown(ts) {
    if (!ts) return "—";
    const d = Math.max(0, Math.floor(((ts + 600) * 1000 - now) / 1000));
    return d <= 0
      ? "EXPIRED"
      : `${Math.floor(d / 60)}:${(d % 60).toString().padStart(2, "0")}`;
  }

  $: pendingAlerts = alerts.filter(
    (a) => a.status === "held" || a.status === "pending",
  );
  $: resolvedAlerts = alerts.filter(
    (a) =>
      a.status === "approved" ||
      a.status === "cancelled" ||
      a.status === "cleared",
  );
</script>

<main>
  <header>
    <div class="logo">
      <svg class="logo-wave" viewBox="0 0 48 28" width="42" height="26">
        <defs
          ><linearGradient id="wg" x1="0" y1="0" x2="1" y2="0"
            ><stop offset="0%" stop-color="#3b82f6" /><stop
              offset="50%"
              stop-color="#06b6d4"
            /><stop offset="100%" stop-color="#14b8a6" /></linearGradient
          ></defs
        >
        <path
          d="M2 18c4-10 10-16 16-12s8 8 14 6 10-8 14-4"
          stroke="url(#wg)"
          stroke-width="3.5"
          fill="none"
          stroke-linecap="round"
        />
        <circle cx="36" cy="5" r="4" fill="#F59E0B" opacity=".85" />
      </svg>
      <span class="logo-text">Fake<span class="logo-accent">out</span></span>
    </div>
  </header>

  <div class="nav-tabs">
    <button
      class:active={activeTab === "monitor"}
      on:click={() => (activeTab = "monitor")}
    >
      <span class="tab-icon">✅</span> WhatsApp Monitor
    </button>
    <button
      class:active={activeTab === "dashboard"}
      on:click={() => (activeTab = "dashboard")}
    >
      <span class="tab-icon">🔔</span> Alert Dashboard
      {#if pendingAlerts.length > 0}<span class="tab-badge"
          >{pendingAlerts.length}</span
        >{/if}
    </button>
  </div>

  {#if activeTab === "monitor"}
    <div class="monitor-layout">
      <!-- Chat Side -->
      <div class="chat-container">
        <WhatsAppWidget
          messages={chatMessages}
          contactName={currentContact.name}
          avatarUrl={currentContact.avatar}
        />
      </div>

      <!-- Scenarios Side -->
      <div class="scenarios-container card glass">
        <div class="card-title">Real-World Scam Scenario</div>
        <div class="card-sub">
          Select a scenario to simulate the scam conversation
        </div>

        <div class="scenario-list">
          {#each SCENARIOS as s}
            <button
              class="scenario-btn"
              class:active={selectedScenario?.id === s.id}
              on:click={() => runScenario(s)}
            >
              <img src={s.avatar} alt="" class="scenario-av" />
              <div class="scenario-info">
                <div class="scenario-name">{s.name}</div>
                <div class="scenario-type">{s.type}</div>
              </div>
              <div class="scenario-arrow">▶</div>
            </button>
          {/each}
        </div>
      </div>
    </div>
  {:else}
    <!-- Alert Dashboard (Original Logic) -->
    <div class="stats">
      <div class="stat-card">
        <div class="stat-icon">📡</div>
        <span
          class="stat-n"
          style="font-size: 1rem; color: {backendOnline
            ? '#10B981'
            : '#EF4444'}"
        >
          {backendOnline ? "LIVE" : "OFFLINE"}
        </span>
        <span class="stat-l">Backend</span>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🕒</div>
        <span class="stat-n" style="font-size: 0.9rem"
          >{new Date(now).toLocaleTimeString()}</span
        >
        <span class="stat-l">Clock</span>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <span class="stat-n">{alerts.length}</span><span class="stat-l"
          >Total</span
        >
      </div>
    </div>

    {#if pendingAlerts.length === 0 && resolvedAlerts.length === 0}
      <div class="empty">Waiting for live messages to scan... 📡</div>
    {/if}

    {#if pendingAlerts.length > 0}
      <div class="section-title">🚨 Pending Review</div>
      {#each pendingAlerts as a (a.txn_id)}
        <div class="alert-card">
          <div class="a-score-ring"><span>{a.risk_score}</span></div>
          <div class="a-body">
            <div class="a-top">
              <span class="a-tag">CRITICAL</span><span class="a-timer"
                >⏱ {countdown(a.timestamp)}</span
              >
            </div>
            <div class="a-row">
              <span>From</span><span>{a.sender_phone}</span>
            </div>
            <div class="a-row">
              <span>Amount</span><span
                >RM {a.transaction_amount?.toLocaleString("en-MY", {
                  minimumFractionDigits: 2,
                })}</span
              >
            </div>
            <div class="a-row">
              <span>Reason</span><span class="a-reason">{a.reason}</span>
            </div>
            {#if a.gemini_reason}
              <div class="a-row ai-logic-row">
                <span>AI LOGIC</span><span class="a-reason ai-logic-txt"
                  >{a.gemini_reason}</span
                >
              </div>
            {/if}
            <div class="a-actions">
              <button class="btn-block" on:click={() => handleCancel(a.txn_id)}
                >🚫 Block & Cancel</button
              >
              <button
                class="btn-approve"
                on:click={() => handleApprove(a.txn_id)}>✅ Approve</button
              >
            </div>
          </div>
        </div>
      {/each}
    {/if}

    {#if resolvedAlerts.length > 0}
      <div class="section-title" style="margin-top:24px">
        📋 Recently Scanned
      </div>
      {#each resolvedAlerts as a (a.txn_id)}
        <div class="alert-card card-safe">
          <div class="a-score-ring"><span>{a.risk_score}</span></div>
          <div class="a-body">
            <div class="a-top">
              <span class="a-tag">{a.status.toUpperCase()}</span>
              <span class="a-timer"
                >{new Date(a.timestamp * 1000).toLocaleTimeString()}</span
              >
            </div>
            <div class="a-row">
              <span>Sender</span><span>{a.sender_phone}</span>
            </div>
            <div class="a-row">
              <span>Reason</span><span class="a-reason">{a.reason}</span>
            </div>
            {#if a.gemini_reason}
              <div class="a-row ai-logic-row">
                <span>AI LOGIC</span><span class="a-reason ai-logic-txt"
                  >{a.gemini_reason}</span
                >
              </div>
            {/if}
          </div>
        </div>
      {/each}
    {/if}
  {/if}

  <footer>Fakeout · TNG Digital FINHACK 2026</footer>
</main>

<style>
  @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap");

  :global(*) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }
  :global(body) {
    font-family: "Inter", sans-serif;
    background: #0b141a;
    color: #e5e7eb;
    min-height: 100vh;
  }

  main {
    max-width: 1080px;
    margin: 0 auto;
    padding: 20px 24px;
  }

  header {
    padding: 10px 0 20px;
    display: flex;
    align-items: center;
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .logo-text {
    font-family: "Space Grotesk", sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .logo-accent {
    background: linear-gradient(135deg, #14b8a6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  /* Tabs */
  .nav-tabs {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
  }
  .nav-tabs button {
    flex: 1;
    padding: 14px;
    border: none;
    border-radius: 12px;
    background: rgba(30, 42, 50, 0.6);
    color: #9ca3af;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }
  .nav-tabs button.active {
    background: rgba(20, 184, 166, 0.1);
    color: #14b8a6;
    border-color: rgba(20, 184, 166, 0.3);
  }
  .tab-badge {
    background: #dc2626;
    color: #fff;
    font-size: 0.65rem;
    padding: 2px 6px;
    border-radius: 10px;
    margin-left: 4px;
  }

  /* Monitor Layout */
  .monitor-layout {
    display: grid;
    grid-template-columns: 420px 1fr;
    gap: 24px;
    align-items: start;
  }
  .scenarios-container {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .scenario-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 560px;
    overflow-y: auto;
    padding-right: 4px;
  }
  .scenario-list::-webkit-scrollbar {
    width: 4px;
  }
  .scenario-list::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
  }

  .scenario-btn {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
  }
  .scenario-btn:hover {
    background: rgba(20, 184, 166, 0.05);
    border-color: rgba(20, 184, 166, 0.2);
    transform: translateX(4px);
  }
  .scenario-btn.active {
    background: rgba(20, 184, 166, 0.1);
    border-color: #14b8a6;
  }
  .scenario-av {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.1);
  }
  .scenario-info {
    flex: 1;
  }
  .scenario-name {
    font-size: 0.9rem;
    font-weight: 600;
    color: #e5e7eb;
    margin-bottom: 2px;
  }
  .scenario-type {
    font-size: 0.72rem;
    color: #9ca3af;
  }
  .scenario-arrow {
    font-size: 0.7rem;
    color: #4b5563;
  }

  /* Dashboard Styles */
  .card {
    background: rgba(30, 42, 50, 0.4);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.06);
  }
  .card-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e5e7eb;
  }
  .card-sub {
    font-size: 0.8rem;
    color: #9ca3af;
    margin-bottom: 8px;
  }
  .stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: rgba(30, 42, 50, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
  }
  .stat-n {
    display: block;
    font-size: 1.8rem;
    font-weight: 800;
    font-family: "Space Grotesk", sans-serif;
  }
  .stat-l {
    font-size: 0.65rem;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .alert-card {
    display: flex;
    gap: 16px;
    background: rgba(30, 42, 50, 0.5);
    border: 1px solid rgba(220, 38, 38, 0.2);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
  }
  .a-score-ring {
    width: 52px;
    height: 52px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(220, 38, 38, 0.1);
    border: 2px solid rgba(220, 38, 38, 0.3);
    flex-shrink: 0;
  }
  .a-score-ring span {
    font-weight: 800;
    color: #f87171;
    font-family: "Space Grotesk", sans-serif;
  }
  .a-body {
    flex: 1;
  }
  .a-top {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
  }
  .a-tag {
    font-size: 0.65rem;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(220, 38, 38, 0.15);
    color: #f87171;
  }
  .a-timer {
    font-size: 0.75rem;
    color: #9ca3af;
  }
  .a-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 0.8rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  }
  .a-row span:first-child {
    color: #9ca3af;
  }
  .a-reason {
    color: #f59e0b;
    text-align: right;
    max-width: 300px;
  }
  .ai-logic-row {
    border-top: 1px dashed rgba(16, 185, 129, 0.2);
    margin-top: 6px;
    padding-top: 8px;
    border-bottom: none;
  }
  .ai-logic-txt {
    color: #10b981;
    font-weight: 500;
  }

  .a-actions {
    display: flex;
    gap: 8px;
    margin-top: 14px;
  }
  .btn-block,
  .btn-approve {
    flex: 1;
    padding: 10px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.75rem;
    cursor: pointer;
    transition: 0.2s;
    border: 1px solid transparent;
  }
  .btn-block {
    background: rgba(220, 38, 38, 0.1);
    color: #f87171;
    border-color: rgba(220, 38, 38, 0.3);
  }
  .btn-approve {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
    border-color: rgba(16, 185, 129, 0.3);
  }

  footer {
    text-align: center;
    padding: 40px 0;
    color: #4b5563;
    font-size: 0.7rem;
  }
</style>
