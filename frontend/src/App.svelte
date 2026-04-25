<script>
  import { onMount, onDestroy } from "svelte";
  import WhatsAppWidget from "./lib/WhatsAppWidget.svelte";
  import {
    startPolling,
    handleApprove,
    handleCancel,
    formatTime,
  } from "./lib/caregiverDashboard.js";
  import { fetchChatMessages, injectChatMessage } from "./lib/api.js";

  const DEMO_SCENARIOS = [
    {
      id: "instagram_verification",
      name: "Instagram Verification",
      category: "Phishing Scam",
      icon: "📸",
      senderName: "Instagram Support",
      senderPhone: "60170000001",
      scammerMessages: [
        "02172269 is your verification code. Enter this code in the Instagram app to verify your account. For your security, do not share this code.",
        "This is Instagram support. Your account has been flagged for suspicious activity. Please share the code now or your account will be permanently disabled within 1 hour.",
      ],
      userReplies: [
        "Hmm I did not request any code... who is this?",
        "Wait, Instagram wouldn't message me on WhatsApp right? This is suspicious...",
      ],
    },
    {
      id: "macau_police",
      name: "Sgt. Michael - Macau Scam",
      category: "Police Scam",
      icon: "👮",
      senderName: "Sgt. Michael",
      senderPhone: "60170000002",
      scammerMessages: [
        "This is PDRM Bukit Aman. You are under investigation for money laundering. Do not hang up.",
        "Transfer all funds to a safe account now or we issue an arrest warrant immediately.",
      ],
      userReplies: [
        "Can I verify this with the official hotline first?",
        "I will not transfer anything without written notice.",
      ],
    },
    {
      id: "fake_friend",
      name: "Fake Friend - Phone Rosak",
      category: "Emergency Scam",
      icon: "📱",
      senderName: "Best Friend",
      senderPhone: "60170000003",
      scammerMessages: [
        "Hey, I'm using a friend's phone because mine rosak. Emergency now, please transfer RM2500 immediately.",
      ],
      userReplies: ["I will call your usual number to confirm."],
    },
    {
      id: "deepfake_voice",
      name: "Deepfake Voice - Help Me",
      category: "Family Scam",
      icon: "🎙️",
      senderName: "Family Member",
      senderPhone: "60170000004",
      scammerMessages: [
        "Emergency! Accident at hospital. Do not call my number now. Please send money first.",
      ],
      userReplies: ["I am contacting family first before sending anything."],
    },
    {
      id: "bank_negara",
      name: "Bank Negara / LHDN",
      category: "Authority Scam",
      icon: "🏦",
      senderName: "Bank Negara Desk",
      senderPhone: "60170000005",
      scammerMessages: [
        "Bank Negara and LHDN flagged unauthorised transaction. Your account will be blocked unless you verify OTP immediately.",
      ],
      userReplies: ["I will check directly with the bank app."],
    },
    {
      id: "parcel_customs",
      name: "Customs - Prohibited Items",
      category: "Parcel Scam",
      icon: "📦",
      senderName: "Customs Officer",
      senderPhone: "60170000006",
      scammerMessages: [
        "Your parcel is detained by customs due to prohibited items. Pay processing fee to release your goods today.",
      ],
      userReplies: ["Please provide official tracking and case number."],
    },
    {
      id: "fake_job",
      name: "Fake Job - WFH RM8K",
      category: "Job Scam",
      icon: "💼",
      senderName: "Job Recruiter",
      senderPhone: "60170000007",
      scammerMessages: [
        "Work from home part-time job, guaranteed return RM8K monthly. Start now with a small service fee.",
      ],
      userReplies: ["No advance fee jobs please."],
    },
    {
      id: "investment",
      name: "Investment - 10% Returns",
      category: "Investment Scam",
      icon: "📈",
      senderName: "Investment Agent",
      senderPhone: "60170000008",
      scammerMessages: [
        "Guaranteed return above 10% with crypto/forex strategy. Limited slot, deposit immediately to secure profit.",
      ],
      userReplies: ["Too risky. I need licensed investment proof."],
    },
  ];

  let alerts = [],
    error = null,
    stopPolling,
    now = Date.now(),
    actionLoading = {},
    actionResult = {};
  let activeTab = "dashboard";
  let monitorMessages = [];
  let monitorReplies = [];
  let monitorLoading = false;
  let monitorError = null;
  let selectedScenarioId = DEMO_SCENARIOS[0].id;

  let ticker, monitorPoller;

  function normalizeMonitorMessage(m) {
    return {
      ...m,
      from: "them",
      transcript: m.type === "voice" ? m.text : null,
    };
  }

  function localTimeNow() {
    return new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    }).toLowerCase();
  }

  async function refreshMonitorMessages() {
    try {
      const data = await fetchChatMessages(60);
      monitorMessages = data.map(normalizeMonitorMessage);
      monitorError = null;
    } catch (e) {
      monitorError = e?.message || "Failed to load monitor messages";
    }
  }

  async function runScenarioDemo(scenario) {
    monitorLoading = true;
    monitorError = null;
    try {
      monitorReplies = monitorReplies.filter((m) => m.sender_phone !== scenario.senderPhone);

      for (let i = 0; i < scenario.scammerMessages.length; i += 1) {
        await injectChatMessage({
          sender_phone: scenario.senderPhone,
          push_name: scenario.senderName,
          message_type: "text",
          text: scenario.scammerMessages[i],
        });

        const reply = scenario.userReplies[i];
        if (reply) {
          monitorReplies = [
            ...monitorReplies,
            {
              id: `local-${scenario.id}-${Date.now()}-${i}`,
              from: "me",
              type: "text",
              text: reply,
              time: localTimeNow(),
              scanning: false,
              risk_score: null,
              sender_phone: scenario.senderPhone,
            },
          ];
        }
      }

      await refreshMonitorMessages();
    } catch (e) {
      monitorError = e?.message || "Failed to inject demo";
    } finally {
      monitorLoading = false;
    }
  }

  $: selectedScenario =
    DEMO_SCENARIOS.find((s) => s.id === selectedScenarioId) || DEMO_SCENARIOS[0];

  $: scenarioBackendMessages = monitorMessages.filter(
    (m) => m.sender_phone === selectedScenario.senderPhone,
  );

  $: scenarioLocalReplies = monitorReplies.filter(
    (m) => m.sender_phone === selectedScenario.senderPhone,
  );

  $: displayedMonitorMessages = [...scenarioBackendMessages, ...scenarioLocalReplies];

  onMount(() => {
    stopPolling = startPolling((d, e) => {
      if (d) alerts = d;
      error = e;
    });
    refreshMonitorMessages();
    ticker = setInterval(() => {
      now = Date.now();
    }, 1000);
    monitorPoller = setInterval(() => {
      if (activeTab === "monitor") refreshMonitorMessages();
    }, 2500);
  });
  onDestroy(() => {
    if (stopPolling) stopPolling();
    if (ticker) clearInterval(ticker);
    if (monitorPoller) clearInterval(monitorPoller);
  });

  function countdown(ts) {
    if (!ts) return "—";
    const d = Math.max(0, Math.floor(((ts + 600) * 1000 - now) / 1000));
    return d <= 0
      ? "EXPIRED"
      : `${Math.floor(d / 60)}:${(d % 60).toString().padStart(2, "0")}`;
  }
  function onApprove(id) {
    alerts = alerts.map((a) =>
      a.txn_id === id ? { ...a, status: "approved" } : a,
    );
  }
  function onCancel(id) {
    alerts = alerts.map((a) =>
      a.txn_id === id ? { ...a, status: "cancelled" } : a,
    );
  }
  function onResolve(id) {
    alerts = alerts.map((a) =>
      a.txn_id === id ? { ...a, status: "cleared" } : a,
    );
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

  <div class="mode-tabs">
    <button
      class="mode-tab"
      class:active={activeTab === "monitor"}
      on:click={() => (activeTab = "monitor")}
    >
      ✅ WhatsApp Monitor
    </button>
    <button
      class="mode-tab"
      class:active={activeTab === "dashboard"}
      on:click={() => (activeTab = "dashboard")}
    >
      🔔 Alert Dashboard
    </button>
  </div>

  {#if activeTab === "monitor"}
    <div class="monitor-layout">
      <section class="monitor-phone">
        <WhatsAppWidget messages={displayedMonitorMessages} contactName={selectedScenario.senderName} />
      </section>

      <section class="monitor-scenarios">
        <div class="scenario-head">
          <div>
            <h3>Real-World Scam Scenario</h3>
            <p>Select a scenario, then run it in the monitor conversation.</p>
          </div>
          <button
            class="run-scenario-btn"
            type="button"
            disabled={monitorLoading}
            on:click={() => runScenarioDemo(selectedScenario)}
          >
            {monitorLoading ? "Running..." : "Run Selected Scenario"}
          </button>
        </div>

        <div class="scenario-list">
          {#each DEMO_SCENARIOS as scenario}
            <button
              class="scenario-row"
              class:active={selectedScenarioId === scenario.id}
              type="button"
              disabled={monitorLoading}
              on:click={() => {
                selectedScenarioId = scenario.id;
                monitorError = null;
              }}
            >
              <span class="scenario-icon">{scenario.icon}</span>
              <span class="scenario-info">
                <strong>{scenario.name}</strong>
                <small>{scenario.category}</small>
              </span>
              <span class="scenario-arrow">▶</span>
            </button>
          {/each}
        </div>

        {#if monitorError}
          <div class="monitor-error">{monitorError}</div>
        {/if}
        {#if monitorLoading}
          <div class="monitor-loading">Injecting scenario into detection pipeline...</div>
        {/if}
      </section>
    </div>
  {/if}

  {#if activeTab === "dashboard"}
    <div class="stats">
      <div class="stat-card">
        <div class="stat-icon">🕒</div>
        <span class="stat-n" style="font-size: 0.9rem">{new Date(now).toLocaleTimeString()}</span>
        <span class="stat-l">Clock</span>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <span class="stat-n">{alerts.length}</span><span class="stat-l">Total</span>
      </div>
      <div class="stat-card warn">
        <div class="stat-icon">🚨</div>
        <span class="stat-n">{pendingAlerts.length}</span><span class="stat-l">Pending</span>
      </div>
      <div class="stat-card">
        <div class="stat-icon">✅</div>
        <span class="stat-n">{resolvedAlerts.length}</span><span class="stat-l">Resolved</span>
      </div>
    </div>

    {#if pendingAlerts.length === 0 && resolvedAlerts.length === 0}
      <div class="empty">Run a scam scenario in WhatsApp Monitor to see detections here.</div>
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

            {#if a.transcript}
              <div class="a-voice-scrutiny">
                <div class="a-scrutiny-header">
                  <svg
                    viewBox="0 0 24 24"
                    width="12"
                    height="12"
                    fill="currentColor"
                    ><path
                      d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"
                    /><path
                      d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"
                    /></svg
                  >
                  AI Voice Transcript
                </div>
                <p class="a-transcript">"{a.transcript}"</p>

                {#if a.translation}
                  <div class="a-translation-box">
                    <div class="a-scrutiny-header" style="color: #A855F7">
                      <svg
                        viewBox="0 0 24 24"
                        width="12"
                        height="12"
                        fill="currentColor"
                        ><path
                          d="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"
                        /></svg
                      >
                      English Translation
                    </div>
                    <p class="a-transcript">"{a.translation}"</p>
                  </div>
                {/if}
              </div>
            {/if}
            <div class="a-actions">
              <button class="btn-block" on:click={() => onCancel(a.txn_id)}
                >🚫 Block & Cancel</button
              >
              <button class="btn-resolve" on:click={() => onResolve(a.txn_id)}
                >📋 Resolve</button
              >
              <button class="btn-approve" on:click={() => onApprove(a.txn_id)}
                >✅ Approve</button
              >
            </div>
          </div>
        </div>
      {/each}
    {/if}
    {#if resolvedAlerts.length > 0}
      <div class="section-title" style="margin-top:24px">📋 Recently Scanned</div>
      {#each resolvedAlerts as a (a.txn_id)}
        <div
          class="alert-card"
          class:card-safe={a.status === "cleared" || a.status === "approved"}
        >
          <div
            class="a-score-ring"
            style="border-color:{a.risk_score >= 80
              ? '#DC2626'
              : a.risk_score >= 50
                ? '#F59E0B'
                : '#10B981'}"
          >
            {a.risk_score}
          </div>
          <div class="a-body">
            <div class="a-top">
              <span class="a-tag">
                {#if a.status === "cleared"}✅ SAFE
                {:else if a.status === "approved"}✅ APPROVED
                {:else}🚫 CANCELLED{/if}
              </span>
              <span class="a-timer">{countdown(a.timestamp)}</span>
            </div>
            <div class="a-row">
              <span>Sender</span><span>{a.sender_phone}</span>
            </div>
            <div class="a-row">
              <span>Reason</span><span class="a-reason">{a.reason}</span>
            </div>

            {#if a.transcript}
              <div class="a-voice-scrutiny">
                <div class="a-scrutiny-header">
                  <svg
                    viewBox="0 0 24 24"
                    width="12"
                    height="12"
                    fill="currentColor"
                    ><path
                      d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"
                    /><path
                      d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"
                    /></svg
                  >
                  AI Voice Transcript
                </div>
                <p class="a-transcript">"{a.transcript}"</p>

                {#if a.translation}
                  <div class="a-translation-box">
                    <div class="a-scrutiny-header" style="color: #A855F7">
                      <svg
                        viewBox="0 0 24 24"
                        width="12"
                        height="12"
                        fill="currentColor"
                        ><path
                          d="M12.87 15.07l-2.54-2.51.03-.03c1.74-1.94 2.98-4.17 3.71-6.53H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"
                        /></svg
                      >
                      English Translation
                    </div>
                    <p class="a-transcript">"{a.translation}"</p>
                  </div>
                {/if}
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
    font-family: "Inter", system-ui, sans-serif;
    background:
      radial-gradient(circle at 20% -10%, rgba(20, 184, 166, 0.14), transparent 36%),
      radial-gradient(circle at 80% -20%, rgba(6, 182, 212, 0.14), transparent 40%),
      #0b0f14;
    color: #e5e7eb;
    min-height: 100vh;
  }
  main {
    max-width: 1240px;
    margin: 0 auto;
    padding: 20px 28px 60px;
  }

  /* Logo */
  header {
    padding: 20px 0 16px;
    display: flex;
    align-items: center;
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .logo-wave {
    filter: drop-shadow(0 2px 8px rgba(20, 184, 166, 0.3));
  }
  .logo-text {
    font-family: "Space Grotesk", sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #e5e7eb;
    letter-spacing: -0.03em;
  }
  .logo-accent {
    background: linear-gradient(135deg, #14b8a6, #06b6d4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  /* Tabs */
  .mode-tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 24px;
    background: rgba(30, 42, 50, 0.75);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 14px;
    padding: 4px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.28);
  }
  .mode-tab {
    flex: 1;
    padding: 10px 16px;
    background: none;
    border: none;
    font-size: 0.82rem;
    font-weight: 600;
    color: #9ca3af;
    cursor: pointer;
    border-radius: 8px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .mode-tab:hover {
    color: #e5e7eb;
  }
  .mode-tab.active {
    background: rgba(20, 184, 166, 0.15);
    color: #14b8a6;
    box-shadow: 0 0 12px rgba(20, 184, 166, 0.1);
  }
  .tab-badge {
    background: #dc2626;
    color: #fff;
    font-size: 0.62rem;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 10px;
    min-width: 18px;
    text-align: center;
    animation: badgePulse 2s ease-in-out infinite;
  }
  @keyframes badgePulse {
    0%,
    100% {
      box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4);
    }
    50% {
      box-shadow: 0 0 0 6px rgba(220, 38, 38, 0);
    }
  }

  .monitor-layout {
    display: grid;
    grid-template-columns: 420px 1fr;
    gap: 24px;
    align-items: start;
    margin-bottom: 10px;
  }

  .monitor-scenarios {
    background: rgba(18, 28, 37, 0.78);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 18px;
    overflow: hidden;
    box-shadow: 0 14px 36px rgba(0, 0, 0, 0.28);
  }
  .monitor-phone {
    width: 100%;
  }

  .monitor-scenarios {
    padding: 18px;
  }
  .monitor-scenarios h3 {
    font-size: 1.35rem;
    margin-bottom: 6px;
  }
  .monitor-scenarios > p {
    color: #95a6b6;
    margin-bottom: 14px;
    font-size: 0.9rem;
  }
  .scenario-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }
  .run-scenario-btn {
    border: 1px solid rgba(20, 184, 166, 0.4);
    background: rgba(20, 184, 166, 0.18);
    color: #63e8d8;
    border-radius: 10px;
    padding: 9px 12px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
  }
  .run-scenario-btn:disabled {
    opacity: 0.6;
    cursor: wait;
  }
  .scenario-list {
    display: grid;
    gap: 10px;
  }
  .scenario-row {
    display: flex;
    align-items: center;
    gap: 12px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: rgba(30, 42, 50, 0.68);
    color: #dde6ee;
    font-size: 0.9rem;
    text-align: left;
    padding: 12px;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .scenario-row:hover,
  .scenario-row.active {
    transform: translateY(-1px);
    border-color: rgba(20, 184, 166, 0.35);
    background: rgba(34, 53, 66, 0.78);
  }
  .scenario-icon {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: rgba(255, 255, 255, 0.08);
    font-size: 1rem;
    flex-shrink: 0;
  }
  .scenario-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex: 1;
  }
  .scenario-info strong {
    font-size: 0.95rem;
    color: #e5edf5;
  }
  .scenario-info small {
    color: #9fb0bf;
    font-size: 0.74rem;
  }
  .scenario-arrow {
    color: #9fb0bf;
    font-size: 0.78rem;
  }
  .monitor-loading {
    margin-top: 12px;
    padding: 10px;
    border-radius: 9px;
    border: 1px solid rgba(20, 184, 166, 0.35);
    background: rgba(20, 184, 166, 0.14);
    color: #9ff8ec;
    font-size: 0.8rem;
  }

  .section-card,
  .section-card-head,
  .section-card h4,
  .section-card p,
  .run-demo-btn,
  .keyword-grid,
  .keyword-chip,
  .keyword-chip small,
  .keyword-reasons,
  .keyword-reasons p {
    display: none;
  }

  .section-card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }
  .section-card h4 {
    font-size: 1rem;
    margin-bottom: 4px;
  }
  .section-card p {
    font-size: 0.82rem;
    color: #9fb0bf;
  }
  .run-demo-btn {
    border: 1px solid rgba(20, 184, 166, 0.4);
    background: rgba(20, 184, 166, 0.18);
    color: #63e8d8;
    border-radius: 9px;
    padding: 8px 10px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
  }
  .run-demo-btn:disabled {
    opacity: 0.6;
    cursor: wait;
  }
  .keyword-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
  }
  .keyword-chip {
    border: 1px solid rgba(148, 163, 184, 0.22);
    background: rgba(30, 42, 50, 0.8);
    color: #e5edf5;
    border-radius: 999px;
    padding: 7px 10px;
    font-size: 0.75rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .keyword-chip small {
    color: #14b8a6;
    font-weight: 700;
  }
  .keyword-chip:hover {
    border-color: rgba(20, 184, 166, 0.35);
    background: rgba(20, 184, 166, 0.12);
  }
  .keyword-chip:disabled {
    opacity: 0.6;
    cursor: wait;
  }
  .keyword-reasons {
    display: grid;
    gap: 7px;
    max-height: 220px;
    overflow-y: auto;
    padding-right: 3px;
  }
  .keyword-reasons p {
    font-size: 0.75rem;
    color: #adbdcb;
    line-height: 1.35;
  }
  .monitor-error {
    margin-top: 12px;
    padding: 10px;
    border-radius: 9px;
    border: 1px solid rgba(220, 38, 38, 0.35);
    background: rgba(220, 38, 38, 0.12);
    color: #fecaca;
    font-size: 0.8rem;
  }

  /* Glass card */
  .card {
    background: rgba(30, 42, 50, 0.6);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 20px;
  }
  .glass {
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  }
  .card-title {
    font-size: 0.9rem;
    font-weight: 700;
    color: #e5e7eb;
    margin-bottom: 4px;
  }
  .card-sub {
    font-size: 0.72rem;
    color: #9ca3af;
    margin-bottom: 14px;
  }

  .preset-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .preset-btn {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.03);
    cursor: pointer;
    transition: all 0.15s;
    text-align: left;
  }
  .preset-btn:hover:not(:disabled) {
    background: rgba(20, 184, 166, 0.08);
    border-color: rgba(20, 184, 166, 0.2);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  }
  .preset-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
  .preset-av {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    border: 2px solid rgba(255, 255, 255, 0.1);
  }
  .preset-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .preset-label {
    font-size: 0.78rem;
    font-weight: 500;
    color: #e5e7eb;
  }
  .preset-cat {
    font-size: 0.62rem;
    color: #9ca3af;
  }
  .injecting-bar {
    margin-top: 12px;
    padding: 10px 14px;
    border-radius: 10px;
    background: rgba(20, 184, 166, 0.08);
    border: 1px solid rgba(20, 184, 166, 0.2);
    color: #14b8a6;
    font-size: 0.78rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .inject-pulse {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #14b8a6;
    animation: pulseDot 1.5s ease-in-out infinite;
  }
  @keyframes pulseDot {
    0%,
    100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.4;
      transform: scale(0.7);
    }
  }

  /* Dashboard */
  .stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  .stat-card {
    background: rgba(23, 34, 44, 0.68);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .stat-card::after {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #14b8a6, #06b6d4);
  }
  .stat-card.warn::after {
    background: linear-gradient(90deg, #dc2626, #f59e0b);
  }
  .stat-card.ok::after {
    background: linear-gradient(90deg, #10b981, #14b8a6);
  }
  .stat-icon {
    font-size: 1.4rem;
    margin-bottom: 4px;
  }
  .stat-n {
    display: block;
    font-size: 2.2rem;
    font-weight: 800;
    font-family: "Space Grotesk", sans-serif;
  }
  .stat-l {
    font-size: 0.7rem;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .stat-card.warn .stat-n {
    color: #dc2626;
  }
  .stat-card.ok .stat-n {
    color: #10b981;
  }

  .section-title {
    font-size: 0.9rem;
    font-weight: 700;
    margin-bottom: 10px;
    color: #e5e7eb;
  }
  .empty {
    background: rgba(22, 34, 46, 0.65);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 48px;
    text-align: center;
    color: #9ca3af;
    font-size: 0.85rem;
  }

  .alert-card {
    display: flex;
    gap: 16px;
    background: rgba(23, 34, 44, 0.72);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(220, 38, 38, 0.25);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
    box-shadow: 0 0 20px rgba(220, 38, 38, 0.05);
  }
  .a-score-ring {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    background: rgba(220, 38, 38, 0.12);
    border: 2px solid rgba(220, 38, 38, 0.4);
  }
  .a-score-ring span {
    font-size: 1.2rem;
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
    margin-bottom: 10px;
  }
  .a-tag {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 6px;
    background: rgba(220, 38, 38, 0.15);
    color: #f87171;
    letter-spacing: 0.04em;
  }
  .a-timer {
    font-size: 0.78rem;
    color: #9ca3af;
  }
  .a-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 0.8rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }
  .a-row span:first-child {
    color: #9ca3af;
  }
  .a-reason {
    color: #f59e0b;
    font-size: 0.78rem;
    max-width: 260px;
    text-align: right;
  }
  .a-actions {
    display: flex;
    gap: 8px;
    margin-top: 14px;
  }
  .btn-block,
  .btn-approve,
  .btn-resolve {
    flex: 1;
    padding: 10px;
    border: none;
    border-radius: 10px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-block {
    background: rgba(220, 38, 38, 0.12);
    color: #f87171;
    border: 1px solid rgba(220, 38, 38, 0.3);
  }
  .btn-block:hover {
    background: rgba(220, 38, 38, 0.2);
  }
  .btn-resolve {
    background: rgba(168, 85, 247, 0.12);
    color: #d8b4fe;
    border: 1px solid rgba(168, 85, 247, 0.3);
  }
  .btn-resolve:hover {
    background: rgba(168, 85, 247, 0.2);
  }
  .btn-approve {
    background: rgba(20, 184, 166, 0.12);
    color: #14b8a6;
    border: 1px solid rgba(20, 184, 166, 0.3);
  }
  .btn-approve:hover {
    background: rgba(20, 184, 166, 0.2);
  }
  .resolved-row {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 16px;
    background: rgba(30, 42, 50, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 10px;
    margin-bottom: 6px;
    font-size: 0.78rem;
    color: #9ca3af;
  }
  .r-stat {
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.68rem;
    min-width: 100px;
  }
  .r-stat.approved {
    color: #10b981;
  }
  .r-stat.cancelled {
    color: #dc2626;
  }

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
    color: #3b82f6;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }
  .a-transcript {
    font-size: 0.8rem;
    color: #e5e7eb;
    line-height: 1.4;
    font-style: italic;
  }
  .a-translation-box {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
  }

  footer {
    text-align: center;
    padding: 32px 0 16px;
    color: #9ca3af;
    font-size: 0.7rem;
  }
  @media (max-width: 900px) {
    .monitor-layout {
      grid-template-columns: 1fr;
    }
    .stats {
      grid-template-columns: 1fr;
    }
    .scenario-head {
      flex-direction: column;
    }
    .run-scenario-btn {
      width: 100%;
    }
    .scenario-row {
      padding: 10px;
    }
  }
</style>
