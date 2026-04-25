<script lang="ts">
  import { onMount } from 'svelte';

  type Alert = {
    id: string;
    user: string;
    initials: string;
    relationship: string;
    amount: number;
    riskScore: number;
    riskLevel: string;
    reason: string;
    status: 'Pending' | 'Approved' | 'Cancelled';
    time: string;
    secondsLeft: number;
    avatarClass: string;
  };

  let alerts = $state<Alert[]>([
    {
      id: '1',
      user: 'Wong Jun Hao',
      initials: 'WJ',
      relationship: 'Family Member',
      amount: 1880,
      riskScore: 97,
      riskLevel: 'Critical',
      reason: 'Detected scam phrases: “urgent”, “don’t tell family”, “transfer now”.',
      status: 'Pending',
      time: 'Just now',
      secondsLeft: 3600,
      avatarClass: 'avatar-blue'
    },
    {
      id: '2',
      user: 'Lim Mei Ling',
      initials: 'LM',
      relationship: 'Mother',
      amount: 850,
      riskScore: 94,
      riskLevel: 'Critical',
      reason: 'Urgent WhatsApp voice note detected. Payment app opened within 2 minutes.',
      status: 'Pending',
      time: '2 min ago',
      secondsLeft: 3480,
      avatarClass: 'avatar-teal'
    },
    {
      id: '3',
      user: 'Tan Siew Yee',
      initials: 'TS',
      relationship: 'Parent',
      amount: 1200,
      riskScore: 91,
      riskLevel: 'Critical',
      reason: 'Detected phrases: “transfer now” and “don’t tell anyone”.',
      status: 'Pending',
      time: '8 min ago',
      secondsLeft: 3120,
      avatarClass: 'avatar-purple'
    },
    {
      id: '4',
      user: 'Tan Kok Wai',
      initials: 'TK',
      relationship: 'Grandfather',
      amount: 420,
      riskScore: 88,
      riskLevel: 'High',
      reason: 'Unknown caller and unusual transfer amount detected.',
      status: 'Pending',
      time: '5 min ago',
      secondsLeft: 3300,
      avatarClass: 'avatar-amber'
    }
  ]);

  let scanInput = $state('');
  let lastUpdated = $state(new Date().toLocaleTimeString());
  let showPopup = $state(true);

  let sortedAlerts = $derived(
    [...alerts].sort((a, b) => {
      if (a.status === 'Pending' && b.status !== 'Pending') return -1;
      if (a.status !== 'Pending' && b.status === 'Pending') return 1;
      return b.riskScore - a.riskScore;
    })
  );

  let pendingCount = $derived(alerts.filter((a) => a.status === 'Pending').length);

  let protectedAmount = $derived(
    alerts.filter((a) => a.status === 'Pending').reduce((sum, a) => sum + a.amount, 0)
  );

  let highestRiskAlert = $derived(sortedAlerts.find((a) => a.status === 'Pending'));

  function approve(id: string) {
    alerts = alerts.map((a) => (a.id === id ? { ...a, status: 'Approved' } : a));
    lastUpdated = new Date().toLocaleTimeString();
  }

  function cancel(id: string) {
    alerts = alerts.map((a) => (a.id === id ? { ...a, status: 'Cancelled' } : a));
    lastUpdated = new Date().toLocaleTimeString();
  }

  function addDemoAlert() {
    const newAlert: Alert = {
      id: crypto.randomUUID(),
      user: 'Chong Mei Xin',
      initials: 'CM',
      relationship: 'Family Member',
      amount: 2650,
      riskScore: 99,
      riskLevel: 'Critical',
      reason: 'Voice note matched mule-account scam script and payment app opened immediately.',
      status: 'Pending',
      time: 'Just now',
      secondsLeft: 3600,
      avatarClass: 'avatar-red'
    };

    alerts = [newAlert, ...alerts];
    showPopup = true;
    lastUpdated = new Date().toLocaleTimeString();
  }

  function demoAnalyzeWebsite() {
    if (!scanInput.trim()) {
      scanInput = 'suspicious-payment-link.my';
    }

    addDemoAlert();
  }

  function formatCountdown(seconds: number) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  onMount(() => {
    const timer = setInterval(() => {
      alerts = alerts.map((a) => {
        if (a.status !== 'Pending') return a;

        if (a.secondsLeft <= 1) {
          return { ...a, secondsLeft: 0, status: 'Cancelled' };
        }

        return { ...a, secondsLeft: a.secondsLeft - 1 };
      });
    }, 1000);

    return () => clearInterval(timer);
  });
</script>

<main class="page">
  <div class="bg-orb orb-one"></div>
  <div class="bg-orb orb-two"></div>
  <div class="bg-orb orb-three"></div>

  {#if showPopup && highestRiskAlert}
    <div class="whatsapp-popup">
      <div class="popup-header">
        <div class="avatar mini {highestRiskAlert.avatarClass}">
          {highestRiskAlert.initials}
        </div>

        <div>
          <strong>Caregiver Alert</strong>
          <p>Suspicious transfer detected</p>
        </div>

        <button class="close-btn" onclick={() => (showPopup = false)}>×</button>
      </div>

      <div class="popup-message">
        <strong>{highestRiskAlert.user}</strong> may be under scam pressure.
        <br />
        RM {highestRiskAlert.amount} is currently held safely.
      </div>
    </div>
  {/if}

  <header class="topbar">
    <a href="#home" class="brand">
      <div class="wave-logo">
        <svg viewBox="0 0 64 64" aria-hidden="true">
          <path d="M8 36C16 20 27 48 36 30C44 14 50 18 56 26" />
          <path d="M8 46C17 30 27 58 38 40C46 26 51 30 56 36" />
        </svg>
      </div>

      <div>
        <strong>FAKEOUT</strong>
        <span>Scam Protection</span>
      </div>
    </a>

    <nav class="nav-links">
      <a href="#home">Home</a>
      <a href="#categories">Categories</a>
      <a href="#analyze">Website Analyze</a>
      <a href="#ip">Locate IP</a>
      <a href="#dns">DNS Tool</a>
      <a href="#alerts">Live Alerts</a>
    </nav>

    <button class="login-btn">Caregiver Login</button>
  </header>

  <section id="home" class="hero">
    <p class="trust-pill">FinHack Scam Track · Live Protection Mode</p>

    <h1>Verify scam risk before money leaves.</h1>

    <p class="hero-subtitle">
      FAKEOUT detects suspicious voice notes, payment pressure, risky links, and unusual transfer
      behaviour — then holds funds safely until a caregiver verifies.
    </p>

    <div id="analyze" class="scanner-card glass">
      <div class="scanner-tabs">
        <button class="active">Website</button>
        <button>WhatsApp</button>
        <button>Transfer</button>
        <button>Phone</button>
      </div>

      <div class="scanner-input">
        <input bind:value={scanInput} placeholder="Enter website, phone number, or payment note..." />
        <button onclick={demoAnalyzeWebsite}>Check Now</button>
      </div>

      <p class="scanner-note">
        Demo mode: checking creates a new high-risk alert and caregiver notification.
      </p>
    </div>

    <div class="hero-stats">
      <div class="glass">
        <strong>10M+</strong>
        <span>Scam patterns simulated</span>
      </div>

      <div class="glass">
        <strong>{pendingCount}</strong>
        <span>Pending alerts</span>
      </div>

      <div class="glass">
        <strong>RM {protectedAmount}</strong>
        <span>Held safely</span>
      </div>
    </div>
  </section>

  <section id="categories" class="section">
    <div class="section-heading">
      <p>Browse by category</p>
      <h2>Scam protection modules</h2>
      <span>Choose what you want to verify first.</span>
    </div>

    <div class="category-grid">
      <a href="#analyze" class="category-card glass">
        <strong>🌐 Website Analyze</strong>
        <span>Detect phishing, fake shops, and scam payment links.</span>
      </a>

      <a href="#alerts" class="category-card glass">
        <strong>💸 Transfer Trap</strong>
        <span>Hold suspicious transfers and auto-cancel if unverified.</span>
      </a>

      <a href="#voice" class="category-card glass">
        <strong>🎙️ Voice Scam Scan</strong>
        <span>Flag urgent language from WhatsApp voice notes.</span>
      </a>

      <a href="#ip" class="category-card glass">
        <strong>📍 Locate IP</strong>
        <span>Show suspicious login or sender location signals.</span>
      </a>

      <a href="#dns" class="category-card glass">
        <strong>🧭 DNS Tool</strong>
        <span>Check domain age, SSL, DNS records, and reputation.</span>
      </a>

      <a href="#caregiver" class="category-card glass">
        <strong>👨‍👩‍👧 Caregiver Mode</strong>
        <span>Notify trusted family before money is released.</span>
      </a>
    </div>
  </section>

  <section class="section tools-section">
    <div id="ip" class="tool-card glass">
      <p>Locate IP</p>
      <h3>Suspicious sender location</h3>
      <div class="tool-result">
        <span>Detected region</span>
        <strong>Kuala Lumpur / Unknown VPN</strong>
      </div>
      <button>Run IP Trace Demo</button>
    </div>

    <div id="dns" class="tool-card glass">
      <p>DNS Tool</p>
      <h3>Domain trust analysis</h3>
      <div class="tool-result">
        <span>Domain age</span>
        <strong>3 days old · High risk</strong>
      </div>
      <button>Check DNS Demo</button>
    </div>

    <div id="voice" class="tool-card glass">
      <p>Voice Scam Scan</p>
      <h3>Urgency phrase detection</h3>
      <div class="tool-result">
        <span>Matched script</span>
        <strong>“Don’t tell family” · Critical</strong>
      </div>
      <button>Analyze Voice Demo</button>
    </div>
  </section>

  <section class="section">
    <div class="section-heading">
      <p>Live security stats</p>
      <h2>Protection overview</h2>
    </div>

    <div class="stats">
      <div class="stat-card glass">
        <strong>{pendingCount}</strong>
        <span>Pending Alerts</span>
      </div>

      <div class="stat-card glass">
        <strong>RM {protectedAmount}</strong>
        <span>Money Held Safely</span>
      </div>

      <div class="stat-card glass">
        <strong>60 min</strong>
        <span>Auto-Cancel Window</span>
      </div>

      <div class="stat-card glass">
        <strong>{highestRiskAlert?.riskScore ?? 0}%</strong>
        <span>Highest Risk Score</span>
      </div>
    </div>
  </section>

  <section id="alerts" class="section">
    <div class="section-heading row-heading">
      <div>
        <p>Real-time transfer security analysis</p>
        <h2>Caregiver alert queue</h2>
        <span>Highest-risk cases are automatically sorted to the top.</span>
      </div>

      <button class="simulate-btn" onclick={addDemoAlert}>
        <span class="button-pulse"></span>
        Simulate New Alert
      </button>
    </div>

    <div class="analysis-list">
      {#each sortedAlerts as alert}
        <article class="analysis-card glass" class:resolved={alert.status !== 'Pending'}>
          <div class="site-score">
            <div class="avatar {alert.avatarClass}">
              {alert.initials}
            </div>

            <div>
              <h3>{alert.user}</h3>
              <p>{alert.relationship} · {alert.time}</p>
            </div>
          </div>

          <div class="analysis-info">
            <span>Protected transfer</span>
            <strong>RM {alert.amount}</strong>
          </div>

          <div class="analysis-info">
            <span>Auto-cancel</span>
            <strong>{formatCountdown(alert.secondsLeft)}</strong>
          </div>

          <div class="analysis-reason">
            <span>{alert.riskLevel}</span>
            <p>{alert.reason}</p>
          </div>

          <div class="analysis-actions">
            {#if alert.status === 'Pending'}
              <button class="approve" onclick={() => approve(alert.id)}>Approve</button>
              <button class="cancel" onclick={() => cancel(alert.id)}>Cancel</button>
            {:else}
              <strong>{alert.status}</strong>
            {/if}
          </div>
        </article>
      {/each}
    </div>
  </section>

  <section id="caregiver" class="final-cta">
    <h2>Start protecting transfers before scammers win.</h2>
    <p>
      FAKEOUT combines website checks, WhatsApp voice analysis, caregiver alerts, and safe transfer
      holds into one protection flow.
    </p>

    <button onclick={addDemoAlert}>Check Risk Now</button>
  </section>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family:
      Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #121212;
    color: #e5e7eb;
  }

  :global(html) {
    scroll-behavior: smooth;
  }

  .page {
    position: relative;
    min-height: 100vh;
    overflow: hidden;
    background:
      radial-gradient(circle at 18% 10%, rgba(20, 184, 166, 0.2), transparent 30%),
      radial-gradient(circle at 88% 14%, rgba(245, 158, 11, 0.15), transparent 24%),
      radial-gradient(circle at 50% 100%, rgba(220, 38, 38, 0.16), transparent 34%),
      linear-gradient(180deg, #121212 0%, #101820 55%, #121212 100%);
  }

  .bg-orb {
    position: fixed;
    border-radius: 999px;
    filter: blur(80px);
    opacity: 0.35;
    pointer-events: none;
    z-index: 0;
    animation: float 8s ease-in-out infinite alternate;
  }

  .orb-one {
    width: 320px;
    height: 320px;
    background: #14b8a6;
    top: -90px;
    left: -80px;
  }

  .orb-two {
    width: 280px;
    height: 280px;
    background: #f59e0b;
    right: -70px;
    top: 220px;
    animation-delay: 1.4s;
  }

  .orb-three {
    width: 300px;
    height: 300px;
    background: #dc2626;
    bottom: -100px;
    left: 35%;
    animation-delay: 2.4s;
  }

  .glass {
    background: rgba(30, 42, 50, 0.62);
    border: 1px solid rgba(229, 231, 235, 0.1);
    box-shadow:
      0 24px 70px rgba(0, 0, 0, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(22px);
  }

  .topbar {
    position: sticky;
    top: 14px;
    z-index: 20;
    max-width: 1180px;
    margin: 0 auto;
    transform: translateY(14px);
    padding: 14px 16px;
    border-radius: 999px;
    background: rgba(30, 42, 50, 0.72);
    border: 1px solid rgba(20, 184, 166, 0.22);
    box-shadow: 0 18px 45px rgba(0, 0, 0, 0.35);
    backdrop-filter: blur(22px);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
  }

  a {
    color: inherit;
    text-decoration: none;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 11px;
  }

  .wave-logo {
    width: 46px;
    height: 46px;
    border-radius: 16px;
    display: grid;
    place-items: center;
    background: linear-gradient(135deg, #14b8a6, #10b981);
    box-shadow: 0 16px 35px rgba(20, 184, 166, 0.28);
  }

  .wave-logo svg {
    width: 34px;
    height: 34px;
    fill: none;
    stroke: #121212;
    stroke-width: 5;
    stroke-linecap: round;
  }

  .brand strong {
    display: block;
    font-size: 16px;
    color: #e5e7eb;
  }

  .brand span {
    display: block;
    font-size: 12px;
    color: #9ca3af;
    font-weight: 700;
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: 18px;
    color: #9ca3af;
    font-size: 14px;
    font-weight: 800;
  }

  .nav-links a:hover {
    color: #14b8a6;
  }

  .login-btn {
    border: 0;
    border-radius: 999px;
    padding: 11px 15px;
    background: #14b8a6;
    color: #121212;
    font-weight: 900;
  }

  .hero {
    position: relative;
    z-index: 1;
    max-width: 1050px;
    margin: 0 auto;
    padding: 128px 24px 54px;
    text-align: center;
  }

  .trust-pill {
    display: inline-flex;
    margin: 0 0 18px;
    padding: 9px 14px;
    border-radius: 999px;
    background: rgba(20, 184, 166, 0.13);
    border: 1px solid rgba(20, 184, 166, 0.32);
    color: #14b8a6;
    font-weight: 900;
  }

  .hero h1 {
    max-width: 850px;
    margin: 0 auto;
    font-size: clamp(44px, 7vw, 78px);
    line-height: 0.96;
    letter-spacing: -0.07em;
    color: #e5e7eb;
  }

  .hero-subtitle {
    max-width: 780px;
    margin: 22px auto 30px;
    color: #9ca3af;
    font-size: 19px;
    line-height: 1.7;
  }

  .scanner-card {
    max-width: 850px;
    margin: 0 auto;
    padding: 18px;
    border-radius: 30px;
  }

  .scanner-tabs {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  .scanner-tabs button {
    border: 0;
    border-radius: 999px;
    padding: 9px 14px;
    background: rgba(18, 18, 18, 0.7);
    color: #9ca3af;
    font-weight: 900;
  }

  .scanner-tabs .active {
    background: #14b8a6;
    color: #121212;
  }

  .scanner-input {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 10px;
  }

  .scanner-input input {
    border: 1px solid rgba(20, 184, 166, 0.24);
    border-radius: 999px;
    padding: 16px 18px;
    font-size: 16px;
    outline: none;
    background: rgba(18, 18, 18, 0.82);
    color: #e5e7eb;
  }

  .scanner-input input::placeholder {
    color: #9ca3af;
  }

  .scanner-input button,
  .simulate-btn,
  .final-cta button,
  .tool-card button {
    border: 0;
    border-radius: 999px;
    padding: 14px 18px;
    background: linear-gradient(135deg, #14b8a6, #10b981);
    color: #121212;
    font-weight: 950;
    cursor: pointer;
  }

  .scanner-note {
    margin: 12px 0 0;
    color: #9ca3af;
    font-weight: 700;
  }

  .hero-stats {
    margin: 32px auto 0;
    max-width: 720px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }

  .hero-stats div {
    padding: 18px;
    border-radius: 24px;
  }

  .hero-stats strong {
    display: block;
    font-size: 28px;
    color: #14b8a6;
  }

  .hero-stats span {
    color: #9ca3af;
    font-weight: 750;
  }

  .section {
    position: relative;
    z-index: 1;
    max-width: 1180px;
    margin: 0 auto;
    padding: 42px 24px;
  }

  .section-heading {
    margin-bottom: 18px;
  }

  .section-heading p {
    margin: 0 0 5px;
    color: #14b8a6;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 12px;
  }

  .section-heading h2 {
    margin: 0;
    font-size: 38px;
    letter-spacing: -0.05em;
    color: #e5e7eb;
  }

  .section-heading span {
    display: block;
    margin-top: 6px;
    color: #9ca3af;
    font-weight: 750;
  }

  .row-heading {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    align-items: end;
  }

  .category-grid,
  .stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }

  .category-card,
  .stat-card,
  .tool-card {
    border-radius: 28px;
    padding: 22px;
  }

  .category-card:hover,
  .stat-card:hover,
  .tool-card:hover,
  .analysis-card:hover {
    border-color: rgba(20, 184, 166, 0.42);
  }

  .category-card strong {
    display: block;
    margin-bottom: 10px;
    font-size: 18px;
    color: #e5e7eb;
  }

  .category-card span {
    color: #9ca3af;
    line-height: 1.5;
    font-weight: 700;
  }

  .tools-section {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 18px;
  }

  .tool-card p {
    margin: 0 0 8px;
    color: #14b8a6;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 12px;
  }

  .tool-card h3 {
    margin: 0 0 18px;
    font-size: 25px;
    color: #e5e7eb;
  }

  .tool-result {
    padding: 15px;
    border-radius: 20px;
    background: rgba(18, 18, 18, 0.7);
    margin-bottom: 16px;
  }

  .tool-result span {
    display: block;
    color: #9ca3af;
    font-weight: 800;
  }

  .tool-result strong {
    display: block;
    margin-top: 6px;
    color: #e5e7eb;
  }

  .stat-card strong {
    display: block;
    font-size: 34px;
    color: #14b8a6;
  }

  .stat-card span {
    color: #9ca3af;
    font-weight: 800;
  }

  .analysis-list {
    display: grid;
    gap: 14px;
  }

  .analysis-card {
    display: grid;
    grid-template-columns: 1.45fr 0.85fr 0.75fr 1.5fr auto;
    align-items: center;
    gap: 16px;
    border-radius: 28px;
    padding: 18px;
    animation: cardIn 0.35s ease both;
  }

  .resolved {
    opacity: 0.65;
  }

  .site-score {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .avatar {
    width: 58px;
    height: 58px;
    border-radius: 22px;
    display: grid;
    place-items: center;
    font-weight: 950;
    color: white;
    box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.18);
  }

  .avatar.mini {
    width: 42px;
    height: 42px;
    border-radius: 16px;
    font-size: 13px;
  }

  .avatar-blue {
    background: linear-gradient(135deg, #2563eb, #06b6d4);
  }

  .avatar-teal {
    background: linear-gradient(135deg, #14b8a6, #10b981);
  }

  .avatar-purple {
    background: linear-gradient(135deg, #8b5cf6, #ec4899);
  }

  .avatar-amber {
    background: linear-gradient(135deg, #f59e0b, #ef4444);
  }

  .avatar-red {
    background: linear-gradient(135deg, #dc2626, #f59e0b);
  }

  .site-score h3 {
    margin: 0;
    font-size: 20px;
    color: #e5e7eb;
  }

  .site-score p {
    margin: 4px 0 0;
    color: #9ca3af;
    font-weight: 750;
  }

  .analysis-info span,
  .analysis-reason span {
    display: block;
    color: #9ca3af;
    font-size: 12px;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .analysis-info strong {
    display: block;
    margin-top: 6px;
    font-size: 18px;
    color: #e5e7eb;
  }

  .analysis-reason span {
    color: #f59e0b;
  }

  .analysis-reason p {
    margin: 6px 0 0;
    color: #e5e7eb;
    line-height: 1.45;
    font-weight: 700;
  }

  .analysis-actions {
    display: flex;
    gap: 8px;
  }

  .analysis-actions button {
    border: 0;
    border-radius: 999px;
    padding: 11px 14px;
    font-weight: 950;
    cursor: pointer;
  }

  .approve {
    background: #14b8a6;
    color: #121212;
  }

  .cancel {
    background: #dc2626;
    color: white;
  }

  .final-cta {
    position: relative;
    z-index: 1;
    max-width: 1180px;
    margin: 36px auto 0;
    padding: 50px 24px 70px;
    text-align: center;
  }

  .final-cta h2 {
    margin: 0;
    font-size: 46px;
    letter-spacing: -0.05em;
    color: #e5e7eb;
  }

  .final-cta p {
    max-width: 680px;
    margin: 16px auto 24px;
    color: #9ca3af;
    font-size: 18px;
    line-height: 1.6;
  }

  .button-pulse {
    display: inline-block;
    width: 10px;
    height: 10px;
    background: #121212;
    border-radius: 999px;
    animation: pulseDark 1.3s infinite;
    margin-right: 8px;
  }

  .whatsapp-popup {
    position: fixed;
    right: 24px;
    bottom: 24px;
    z-index: 30;
    width: 345px;
    padding: 16px;
    border-radius: 26px;
    background: rgba(30, 42, 50, 0.82);
    border: 1px solid rgba(20, 184, 166, 0.35);
    box-shadow: 0 24px 70px rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(24px);
    animation: popupIn 0.35s ease both;
  }

  .popup-header {
    display: flex;
    gap: 10px;
    align-items: flex-start;
  }

  .popup-header strong {
    color: #e5e7eb;
  }

  .popup-header p {
    margin: 4px 0 0;
    color: #10b981;
  }

  .close-btn {
    margin-left: auto;
    background: transparent;
    color: #9ca3af;
    font-size: 24px;
    padding: 0 4px;
    border: 0;
    cursor: pointer;
  }

  .popup-message {
    margin-top: 12px;
    padding: 13px;
    border-radius: 18px;
    background: rgba(16, 185, 129, 0.12);
    color: #e5e7eb;
    line-height: 1.55;
  }

  @keyframes pulseDark {
    0% {
      box-shadow: 0 0 0 0 rgba(18, 18, 18, 0.75);
    }
    70% {
      box-shadow: 0 0 0 10px rgba(18, 18, 18, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(18, 18, 18, 0);
    }
  }

  @keyframes float {
    from {
      transform: translateY(0) translateX(0);
    }
    to {
      transform: translateY(30px) translateX(20px);
    }
  }

  @keyframes cardIn {
    from {
      opacity: 0;
      transform: translateY(14px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes popupIn {
    from {
      opacity: 0;
      transform: translateY(22px) scale(0.95);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @media (max-width: 1000px) {
    .nav-links {
      display: none;
    }

    .category-grid,
    .tools-section,
    .stats {
      grid-template-columns: 1fr 1fr;
    }

    .analysis-card {
      grid-template-columns: 1fr;
      align-items: start;
    }

    .analysis-actions {
      justify-content: flex-start;
    }
  }

  @media (max-width: 680px) {
    .topbar {
      border-radius: 24px;
      align-items: flex-start;
      flex-direction: column;
    }

    .hero {
      padding-top: 95px;
    }

    .scanner-input {
      grid-template-columns: 1fr;
    }

    .hero-stats,
    .category-grid,
    .tools-section,
    .stats {
      grid-template-columns: 1fr;
    }

    .row-heading {
      flex-direction: column;
      align-items: flex-start;
    }

    .whatsapp-popup {
      left: 16px;
      right: 16px;
      bottom: 16px;
      width: auto;
    }
  }
</style>




