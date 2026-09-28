// auth.js
const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

function saveTokens(access, refresh) {
  localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return null;

  const response = await fetch(`${API_BASE}/api/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    clearTokens(); // refresh token itself is dead — must log in again
    return null;
  }

  const data = await response.json();
  saveTokens(data.access, data.refresh); // simplejwt rotates refresh tokens if ROTATE_REFRESH_TOKENS is on
  return data.access;
}

// Wraps every authenticated fetch call — retries once after a silent refresh.
async function authedFetch(url, options = {}) {
  let token = getAccessToken();
  let response = await fetch(url, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` },
  });

  if (response.status === 401) {
    token = await refreshAccessToken();
    if (!token) {
      showLoginView(); // refresh genuinely failed, force real login
      throw new Error("Session expired");
    }
    response = await fetch(url, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${token}` },
    });
  }

  return response;
}