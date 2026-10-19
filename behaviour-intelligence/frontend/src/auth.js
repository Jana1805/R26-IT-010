// Login helpers: talks to /api/auth/* and keeps the session token (never the
// password) in localStorage, so every tab of the app shares one login. The
// server still checks the token's signature and expiry on /api/auth/me.
import axios from 'axios';

export const API_URL = 'http://127.0.0.1:8001';
export const TOKEN_KEY = 'edis_token';

export const ROLES = ['Grid Planner', 'Analyst', 'Engineer', 'Researcher'];

function readStorage(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function writeStorage(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch { /* storage blocked: session only lives in memory */ }
}

export const getToken = () => readStorage(TOKEN_KEY);
export const setToken = (token) => writeStorage(TOKEN_KEY, token);
export const clearToken = () => writeStorage(TOKEN_KEY, null);

function errorMessage(err, fallback) {
  return err.response?.data?.detail || (err.response ? fallback : 'Cannot reach the server on port 8001. Is the backend running?');
}

// Login is required unless the backend says AUTH_ENABLED=false.
export async function fetchAuthConfig() {
  try {
    const res = await axios.get(`${API_URL}/api/auth/config`, { timeout: 5000 });
    return { authEnabled: res.data.auth_enabled !== false, reachable: true };
  } catch {
    return { authEnabled: true, reachable: false };
  }
}

export async function fetchMe() {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await axios.get(`${API_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
    return res.data.user;
  } catch (err) {
    if (err.response?.status === 401) clearToken();
    return null;
  }
}

export async function login(email, password) {
  try {
    const res = await axios.post(`${API_URL}/api/auth/login`, { email, password });
    setToken(res.data.token);
    return { user: res.data.user };
  } catch (err) {
    return { error: errorMessage(err, 'Login failed. Please try again.') };
  }
}

export async function signup(fields) {
  try {
    const res = await axios.post(`${API_URL}/api/auth/signup`, fields);
    setToken(res.data.token);
    return { user: res.data.user };
  } catch (err) {
    return { error: errorMessage(err, 'Sign up failed. Please try again.') };
  }
}

export async function logout() {
  const token = getToken();
  clearToken();
  if (!token) return;
  try {
    await axios.post(`${API_URL}/api/auth/logout`, null, { headers: { Authorization: `Bearer ${token}` } });
  } catch { /* token already cleared locally */ }
}

// Same rules as the backend (backend/app/core/auth.py), so most mistakes are
// shown before the form is sent.
export function validateSignup(f) {
  const errors = {};
  if (f.name.trim().length < 2) errors.name = 'Please enter your full name.';
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.email.trim())) errors.email = 'Please enter a valid email address, for example name@ceb.lk.';
  if (f.organisation.trim().length < 2) errors.organisation = 'Please enter your organisation.';
  if (!ROLES.includes(f.role)) errors.role = 'Please choose your role.';
  if (f.password.length < 8 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)) {
    errors.password = 'Use at least 8 characters with a letter and a number.';
  }
  if (f.confirm_password !== f.password) errors.confirm_password = 'The two passwords do not match.';
  return errors;
}
