<script>
  import { onMount, onDestroy } from "svelte";
  import WhatsAppWidget from "./lib/WhatsAppWidget.svelte";
  import {
    startPolling,
    handleApprove,
    handleCancel,
    formatTime,
  } from "./lib/caregiverDashboard.js";
  import { healthCheck } from "./lib/api.js";
  let alerts = [],
    error = null,
    stopPolling,
    now = Date.now(),
    actionLoading = {},
    actionResult = {};
  let activeTab = "dashboard";

  let ticker;
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

  <div class="stats">
    <div class="stat-card">
      <div class="stat-icon">📡</div>
      <span
        class="stat-n"
        style="font-size: 1rem; color: {backendOnline ? '#10B981' : '#EF4444'}"
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
    <div class="stat-card warn">
      <div class="stat-icon">🚨</div>
      <span class="stat-n">{pendingAlerts.length}</span><span class="stat-l"
        >Pending</span
      >
    </div>
  </div>
  {#if pendingAlerts.length === 0 && resolvedAlerts.length === 0}
    <div class="empty">Waiting for live Telegram messages... 📡</div>
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
    background: #121212;
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
  .tabs {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    background: #1e2a32;
    border-radius: 12px;
    padding: 4px;
  }
  .tabs button {
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
    gap: 6px;
  }
  .tabs button:hover {
    color: #e5e7eb;
  }
  .tabs button.active {
    background: rgba(20, 184, 166, 0.15);
    color: #14b8a6;
    border-color: rgba(20, 184, 166, 0.3);
  }
  .tab-badge {
    background: #dc2626;
    color: #fff;
    font-size: 0.65rem;
    padding: 2px 6px;
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

  .wa-layout {
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
    background: rgba(30, 42, 50, 0.6);
    backdrop-filter: blur(12px);
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
    background: rgba(30, 42, 50, 0.6);
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
    background: rgba(30, 42, 50, 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(220, 38, 38, 0.25);
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

  /* Dashboard Grid Layout */
  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-top: 24px;
  }

  /* Alert Blocks */
  .alert-block {
    background: rgba(30, 42, 50, 0.4);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    overflow: hidden;
  }

  .pending-block {
    border-color: rgba(220, 38, 38, 0.2);
    box-shadow: 0 0 20px rgba(220, 38, 38, 0.05);
  }

  .resolved-block {
    border-color: rgba(16, 185, 129, 0.2);
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.05);
  }

  .block-header {
    padding: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .block-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.1rem;
    font-weight: 700;
    color: #e5e7eb;
    margin-bottom: 4px;
  }

  .block-icon {
    font-size: 1.2rem;
  }

  .block-count {
    margin-left: auto;
    background: rgba(255, 255, 255, 0.1);
    color: #e5e7eb;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 12px;
    min-width: 24px;
    text-align: center;
  }

  .pending-block .block-count {
    background: rgba(220, 38, 38, 0.2);
    color: #f87171;
  }

  .resolved-block .block-count {
    background: rgba(16, 185, 129, 0.2);
    color: #10b981;
  }

  .block-subtitle {
    font-size: 0.75rem;
    color: #9ca3af;
  }

  .alerts-list {
    max-height: 600px;
    overflow-y: auto;
    padding: 16px;
  }

  .alerts-list::-webkit-scrollbar {
    width: 4px;
  }

  .alerts-list::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
  }

  .block-empty {
    padding: 40px 20px;
    text-align: center;
    color: #9ca3af;
    font-size: 0.9rem;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .dashboard-grid {
      grid-template-columns: 1fr;
      gap: 16px;
    }
  }
  .btn-block,
  .btn-approve,
  .btn-resolve {
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
  .btn-resolve {
    background: rgba(168, 85, 247, 0.12);
    color: #d8b4fe;
    border: 1px solid rgba(168, 85, 247, 0.3);
  }
  .btn-resolve:hover {
    background: rgba(168, 85, 247, 0.2);
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
  @media (max-width: 900px) {
    .wa-layout {
      grid-template-columns: 1fr;
    }
    .stats {
      grid-template-columns: 1fr;
    }
  }
</style>
