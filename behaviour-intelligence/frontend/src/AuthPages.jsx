import React, { useState } from 'react';
import { login, signup, validateSignup, ROLES } from './auth.js';

function AuthLayout({ title, subtitle, children, navigate }) {
  return (
    <div className="auth-page">
      <a href="/" className="auth-brand" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
        <span className="home-logo-mark">⚡</span> Electricity Demand Intelligence System
      </a>
      <div className="auth-card">
        <h1 className="auth-title">{title}</h1>
        <p className="auth-subtitle">{subtitle}</p>
        {children}
      </div>
    </div>
  );
}

function Field({ label, error, children }) {
  return (
    <label className={`auth-field ${error ? 'auth-field-error' : ''}`}>
      <span className="auth-label">{label}</span>
      {children}
      {error && <span className="auth-error-text">{error}</span>}
    </label>
  );
}

export function LoginPage({ navigate, notice, onAuthenticated }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setBusy(true);
    const res = await login(email.trim(), password);
    setBusy(false);
    if (res.error) setError(res.error);
    else onAuthenticated(res.user);
  };

  return (
    <AuthLayout title="Log in" subtitle="Open the demand intelligence dashboard." navigate={navigate}>
      {notice && !error && <div className="auth-notice">{notice}</div>}
      {error && <div className="auth-alert" role="alert">{error}</div>}
      <form onSubmit={submit} noValidate>
        <Field label="Email">
          <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@ceb.lk" />
        </Field>
        <Field label="Password">
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <button type="submit" className="home-btn home-btn-primary auth-submit" disabled={busy}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p className="auth-switch">
        No account yet?{' '}
        <a href="/signup" onClick={(e) => { e.preventDefault(); navigate('/signup'); }}>Sign up</a>
      </p>
      <p className="auth-demo">Demo account: <strong>demo@ceb.lk</strong> / <strong>Demo@2026</strong></p>
    </AuthLayout>
  );
}

const EMPTY = { name: '', email: '', organisation: '', role: '', password: '', confirm_password: '' };

export function SignupPage({ navigate, onAuthenticated }) {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const found = validateSignup(form);
    setErrors(found);
    setServerError('');
    if (Object.keys(found).length) return;
    setBusy(true);
    const res = await signup({ ...form, name: form.name.trim(), email: form.email.trim(), organisation: form.organisation.trim() });
    setBusy(false);
    if (res.error) setServerError(res.error);
    else onAuthenticated(res.user);
  };

  return (
    <AuthLayout title="Create an account" subtitle="For grid planners, engineers, analysts and researchers." navigate={navigate}>
      {serverError && <div className="auth-alert" role="alert">{serverError}</div>}
      {Object.keys(errors).length > 0 && !serverError && (
        <div className="auth-alert" role="alert">Please fix the highlighted fields.</div>
      )}
      <form onSubmit={submit} noValidate>
        <Field label="Full name" error={errors.name}>
          <input value={form.name} onChange={set('name')} autoComplete="name" />
        </Field>
        <Field label="Email" error={errors.email}>
          <input type="email" value={form.email} onChange={set('email')} autoComplete="email" placeholder="name@ceb.lk" />
        </Field>
        <div className="auth-row">
          <Field label="Organisation" error={errors.organisation}>
            <input value={form.organisation} onChange={set('organisation')} placeholder="e.g. Ceylon Electricity Board" />
          </Field>
          <Field label="Role" error={errors.role}>
            <select value={form.role} onChange={set('role')}>
              <option value="">Choose a role…</option>
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </Field>
        </div>
        <div className="auth-row">
          <Field label="Password" error={errors.password}>
            <input type="password" value={form.password} onChange={set('password')} autoComplete="new-password" />
          </Field>
          <Field label="Confirm password" error={errors.confirm_password}>
            <input type="password" value={form.confirm_password} onChange={set('confirm_password')} autoComplete="new-password" />
          </Field>
        </div>
        <p className="auth-hint">At least 8 characters, with a letter and a number.</p>
        <button type="submit" className="home-btn home-btn-primary auth-submit" disabled={busy}>
          {busy ? 'Creating account…' : 'Sign up'}
        </button>
      </form>
      <p className="auth-switch">
        Already have an account?{' '}
        <a href="/login" onClick={(e) => { e.preventDefault(); navigate('/login'); }}>Log in</a>
      </p>
    </AuthLayout>
  );
}
