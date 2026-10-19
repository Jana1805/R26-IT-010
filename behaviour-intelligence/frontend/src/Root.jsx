// Top-level page switch: "/" home, "/login", "/signup", "/dashboard".
// The dashboard itself (App.jsx) is rendered unchanged inside a thin frame
// that shows the logged-in user and a Logout button.
import React, { useState, useEffect, useCallback } from 'react';
import App from './App.jsx';
import Home from './Home.jsx';
import { LoginPage, SignupPage } from './AuthPages.jsx';
import { fetchAuthConfig, fetchMe, logout, TOKEN_KEY } from './auth.js';
import OTHER_COMPONENTS from './components.config.js';
import './home.css';

const KNOWN_PATHS = ['/', '/login', '/signup', '/dashboard'];
const XAI_ORIGIN = new URL(OTHER_COMPONENTS.find((c) => c.key === 'xai').url).origin;

// Madushani's "Back to Dashboard" links point to http://localhost:3000 (the
// home page). Coming back from the XAI app should land on the dashboard.
function startPath() {
  const path = normalise(window.location.pathname);
  let fromXai = false;
  try { fromXai = !!document.referrer && new URL(document.referrer).origin === XAI_ORIGIN; } catch { /* no referrer */ }
  if (path === '/' && fromXai) {
    window.history.replaceState(null, '', '/dashboard');
    return '/dashboard';
  }
  return path;
}

// Same link clicked inside the BI iframe would load BI inside itself: send the
// whole window back to the dashboard instead.
function framedInsideBi() {
  try { return window.top !== window.self && window.top.location.origin === window.location.origin; } catch { return false; }
}

function normalise(path) {
  const p = path.replace(/\/+$/, '') || '/';
  return KNOWN_PATHS.includes(p) ? p : '/';
}

function DashboardFrame({ user, authEnabled, onLogout, navigate }) {
  return (
    <div className="auth-frame">
      <div className="auth-topbar">
        <a href="/" className="auth-topbar-home" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
          ← Home
        </a>
        <div className="auth-topbar-user">
          {authEnabled && user ? (
            <>
              <span className="auth-topbar-name">{user.name}</span>
              <span className="auth-topbar-role">{user.role}</span>
              <button className="auth-topbar-logout" onClick={onLogout}>Logout</button>
            </>
          ) : (
            <span className="auth-topbar-role">Login switched off (AUTH_ENABLED=false)</span>
          )}
        </div>
      </div>
      <App />
    </div>
  );
}

export default function Root() {
  const [framed] = useState(framedInsideBi);
  const [path, setPath] = useState(startPath);
  const [authEnabled, setAuthEnabled] = useState(null);   // null = still checking
  const [user, setUser] = useState(null);
  const [notice, setNotice] = useState('');

  const navigate = useCallback((to, { replace = false } = {}) => {
    const target = normalise(to);
    if (replace) window.history.replaceState(null, '', target);
    else window.history.pushState(null, '', target);
    setPath(target);
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    const onPop = () => setPath(normalise(window.location.pathname));
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    if (framed) { window.top.location.href = '/dashboard'; return; }
    (async () => {
      const cfg = await fetchAuthConfig();
      if (cfg.authEnabled) setUser(await fetchMe());
      setAuthEnabled(cfg.authEnabled);
    })();
  }, [framed]);

  // One login for all tabs: react when another tab logs in or out.
  useEffect(() => {
    if (!authEnabled) return undefined;
    const onStorage = async (e) => {
      if (e.key !== TOKEN_KEY) return;
      if (!e.newValue) {
        setUser(null);
        setNotice('You have been logged out.');
        if (normalise(window.location.pathname) === '/dashboard') navigate('/login', { replace: true });
      } else {
        setUser(await fetchMe());
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [authEnabled, navigate]);

  // Re-check the session when the tab becomes active again; an expired or
  // invalid token is cleared by fetchMe (401) and the user goes to login.
  useEffect(() => {
    if (!authEnabled || !user) return undefined;
    const onVisible = async () => {
      if (document.visibilityState !== 'visible') return;
      const me = await fetchMe();
      if (!me) {
        setUser(null);
        setNotice('Your session has ended. Please log in again.');
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [authEnabled, user]);

  // Protected route: the dashboard needs a logged-in user unless login is off.
  useEffect(() => {
    if (authEnabled === null) return;
    if (path === '/dashboard' && authEnabled && !user) {
      setNotice((n) => n || 'Please log in to open the dashboard.');
      navigate('/login', { replace: true });
    }
    if ((path === '/login' || path === '/signup') && (user || !authEnabled)) {
      navigate('/dashboard', { replace: true });
    }
  }, [path, authEnabled, user, navigate]);

  const handleAuthenticated = (u) => {
    setUser(u);
    setNotice('');
    navigate('/dashboard');
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setNotice('You have been logged out.');
    navigate('/login');
  };

  if (framed) return null;

  if (authEnabled === null) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading…</p>
      </div>
    );
  }

  if (path === '/dashboard' && (user || !authEnabled)) {
    return <DashboardFrame user={user} authEnabled={authEnabled} onLogout={handleLogout} navigate={navigate} />;
  }
  if (path === '/login') {
    return <LoginPage navigate={navigate} notice={notice} onAuthenticated={handleAuthenticated} />;
  }
  if (path === '/signup') {
    return <SignupPage navigate={navigate} onAuthenticated={handleAuthenticated} />;
  }
  if (path === '/dashboard') return null; // redirecting to /login
  return <Home navigate={navigate} authEnabled={authEnabled} user={user} onLogout={handleLogout} />;
}
