/**
 * HelloFin API Client
 * Communicates with the FastAPI backend for caregiver operations.
 */

const BASE_URL = 'http://127.0.0.1:8000';

export async function detectBackend() {
  return BASE_URL;
}

async function request(path, options = {}) {
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `API error ${res.status}`);
    }
    return res.json();
  } catch (err) {
    console.error(`[API ERROR] ${path}:`, err);
    throw err;
  }
}

/** Fetch all pending caregiver alerts */
export async function fetchAlerts() {
  return request('/caregiver/alerts');
}

/** Approve a held transaction */
export async function approveTransaction(txnId) {
  return request(`/caregiver/approve/${txnId}`, { method: 'POST' });
}

/** Cancel a held transaction */
export async function cancelTransaction(txnId) {
  return request(`/caregiver/cancel/${txnId}`, { method: 'POST' });
}

/** Score risk for a transcript */
export async function scoreRisk(payload) {
  return request('/risk/score', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/** Health check */
export async function healthCheck() {
  return request('/health');
}
