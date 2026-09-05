/**
 * auth.js — Client-side authentication interacting with Flask backend.
 * Uses JWT tokens for session management.
 */

const SESSION_KEY = 'hcp_session';
const TOKEN_KEY = 'hcp_token';
const API_BASE_AUTH = window.API_BASE || window.CROSSWISE_API_URL || localStorage.getItem('crosswise_api_url') || (
  ['localhost', '127.0.0.1', '0.0.0.0', ''].includes(window.location.hostname)
    ? `${window.location.protocol}//${window.location.hostname || '127.0.0.1'}:5000`
    : 'https://api.yourdomain.com'
);

/** Returns the current logged-in user object, or null. */
function getCurrentUser() {
  const session = sessionStorage.getItem(SESSION_KEY);
  if (!session) return null;
  try {
    return JSON.parse(session);
  } catch {
    return null;
  }
}

/** Returns whether the user is logged in. */
function isLoggedIn() {
  return getCurrentUser() !== null && sessionStorage.getItem(TOKEN_KEY) !== null;
}

/** Get the JWT access token */
function getAuthToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

/**
 * Registers a new user via the backend API.
 * Returns { ok: true, user } or { ok: false, error: string }.
 * @param {string} name
 * @param {string} email
 * @param {string} password
 */
async function registerUser(name, email, password) {
  try {
    const response = await fetch(`${API_BASE_AUTH}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { ok: false, error: data.error || 'Registration failed' };
    }

    // Auto-login after register
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(data.user));
    sessionStorage.setItem(TOKEN_KEY, data.access_token);

    return { ok: true, user: data.user };
  } catch (error) {
    console.error('Register error:', error);
    return { ok: false, error: 'Network error connecting to backend.' };
  }
}

/**
 * Logs in a user via the backend API.
 * Returns { ok: true, user } or { ok: false, error: string }.
 * @param {string} email
 * @param {string} password
 */
async function loginUser(email, password) {
  try {
    const response = await fetch(`${API_BASE_AUTH}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { ok: false, error: data.error || 'Invalid credentials' };
    }

    sessionStorage.setItem(SESSION_KEY, JSON.stringify(data.user));
    sessionStorage.setItem(TOKEN_KEY, data.access_token);
    
    return { ok: true, user: data.user };
  } catch (error) {
    console.error('Login error:', error);
    return { ok: false, error: 'Network error connecting to backend.' };
  }
}

/** Logs out the current user and redirects to landing. */
function logoutUser() {
  sessionStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  window.location.href = 'index.html';
}

/**
 * Guards a page that requires login.
 * If not logged in, redirects to login.html.
 * @param {string} [redirectTo='login.html']
 */
function requireAuth(redirectTo = 'login.html') {
  if (!isLoggedIn()) {
    window.location.href = redirectTo;
  }
}

/**
 * Guards a page that requires admin privileges.
 * If not admin, redirects to home.
 * @param {string} [redirectTo='index.html']
 */
function requireAdmin(redirectTo = 'index.html') {
  requireAuth(); // Ensure logged in first
  const user = getCurrentUser();
  if (!user || !user.is_admin) {
    window.location.href = redirectTo;
  }
}


/**
 * Wrapper for fetch that automatically injects the JWT token
 * and handles 401 Unauthorized responses.
 */
async function apiFetch(url, options = {}) {
  const token = getAuthToken();
  const headers = { ...options.headers };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  // Only set application/json if body is string and content-type isn't explicitly disabled/set
  if (options.body && typeof options.body === 'string' && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 401) {
    // Token expired or invalid
    logoutUser();
    throw new Error("Session expired. Please log in again.");
  }
  
  // If response has no content (like 204), return empty object
  const text = await response.text();
  if (!text) return {};
  
  try {
    const data = JSON.parse(text);
    if (!response.ok) throw new Error(data.error || `HTTP error ${response.status}`);
    return data;
  } catch (err) {
    if (!response.ok) throw new Error(`HTTP error ${response.status}`);
    return text; // Return raw text if not JSON (e.g. some endpoints)
  }
}
