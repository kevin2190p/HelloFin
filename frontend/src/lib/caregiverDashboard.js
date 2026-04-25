/**
 * Caregiver Dashboard Logic
 * Auto-refresh, alert management, and notification helpers.
 */

import { fetchAlerts, approveTransaction, cancelTransaction } from './api.js';

const REFRESH_INTERVAL = 1500; // 1.5 seconds (Real-time)

/**
 * Start auto-refresh polling for caregiver alerts.
 * @param {Function} onUpdate - Callback with alerts array
 * @returns {Function} stop - Call to stop polling
 */
export function startPolling(onUpdate) {
  let active = true;

  async function poll() {
    if (!active) return;
    try {
      const alerts = await fetchAlerts();
      onUpdate(alerts, null);
    } catch (err) {
      onUpdate([], err.message);
    }
    if (active) setTimeout(poll, REFRESH_INTERVAL);
  }

  poll();
  return () => { active = false; };
}

/**
 * Handle approve action with optimistic UI update.
 */
export async function handleApprove(txnId) {
  return approveTransaction(txnId);
}

/**
 * Handle cancel action with optimistic UI update.
 */
export async function handleCancel(txnId) {
  return cancelTransaction(txnId);
}

/**
 * Format a UNIX timestamp to locale string.
 */
export function formatTime(ts) {
  if (!ts) return '—';
  return new Date(ts * 1000).toLocaleString('en-MY', {
    timeZone: 'Asia/Kuala_Lumpur',
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

/**
 * Get risk level color class.
 */
export function riskColor(score) {
  if (score >= 80) return 'critical';
  if (score >= 50) return 'warning';
  return 'safe';
}
