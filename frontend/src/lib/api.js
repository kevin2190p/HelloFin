/**
 * Fakeout API Client
 * Communicates with the FastAPI backend for caregiver operations.
 *
 * The backend may run on port 8000 (canonical) or 8080 (when 8000 is busy).
 * On the first call we probe both and cache the working URL. Override with
 * `?api=http://host:port` in the URL or with VITE_API_BASE_URL at build time.
 */

const QUERY_OVERRIDE = (() => {
  if (typeof window === 'undefined') return null;
  const params = new URLSearchParams(window.location.search);
  return params.get('api');
})();

const ENV_OVERRIDE =
  (typeof import.meta !== 'undefined' &&
    import.meta.env &&
    import.meta.env.VITE_API_BASE_URL) ||
  null;

const CANDIDATES = [
  QUERY_OVERRIDE,
  ENV_OVERRIDE,
  'http://127.0.0.1:8080',
  'http://127.0.0.1:8000',
  'http://localhost:8080',
  'http://localhost:8000',
].filter(Boolean);

let resolvedBase = null;
let resolving = null;

async function resolveBase() {
  if (resolvedBase) return resolvedBase;
  if (resolving) return resolving;
  resolving = (async () => {
    for (const candidate of CANDIDATES) {
      try {
        const res = await fetch(`${candidate}/health`, {
          method: 'GET',
          signal: AbortSignal.timeout ? AbortSignal.timeout(1500) : undefined,
        });
        if (res.ok) {
          resolvedBase = candidate;
          // eslint-disable-next-line no-console
          console.info(`[API] using backend at ${candidate}`);
          return candidate;
        }
      } catch (_e) {
        /* try next candidate */
      }
    }
    // Fallback: just use the first candidate even if probe failed,
    // so subsequent retries can hit it once it comes online.
    resolvedBase = CANDIDATES[0];
    return resolvedBase;
  })();
  try {
    return await resolving;
  } finally {
    resolving = null;
  }
}

export async function detectBackend() {
  return resolveBase();
}

async function request(path, options = {}) {
  const base = await resolveBase();
  try {
    const res = await fetch(`${base}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `API error ${res.status}`);
    }
    return res.json();
  } catch (err) {
    // Re-probe on hard network failure (backend may have switched ports).
    if (err && (err.name === 'TypeError' || err.message?.includes('Failed to fetch'))) {
      resolvedBase = null;
    }
    // eslint-disable-next-line no-console
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
