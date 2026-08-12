import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import API from '../api/projects';
import Footer from '../components/Footer';
import gradionLogo from '../assets/gradion-logo.png';

export default function Auth() {
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState('');

  const validate = () => {
    const e = {};
    if (!name.trim() || name.trim().length < 2) e.name = 'Name must be at least 2 characters';
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
      e.email = 'Enter a valid email address';
    return e;
  };

  const handleSubmit = async (ev) => {
    ev.preventDefault();
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;

    setLoading(true);
    setServerError('');
    try {
      const user = await API.signIn(name.trim(), email.trim().toLowerCase());
      signIn({ name: user.name, email: user.email });
      navigate('/');
    } catch (err) {
      setServerError(err?.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg-3)' }}>
      <div className="center-page" style={{ flex: 1 }}>
        <div className="auth-card">
          <div className="auth-card-brand">
            <img src={gradionLogo} alt="Gradion" style={{ height: 28 }} />
          </div>
          <h2>Book Illustration Studio</h2>
          <p className="lede">Enter your details to start or resume an illustration project.</p>

          <form onSubmit={handleSubmit} noValidate>
            <div className="gd-field">
              <label htmlFor="auth-name">
                Full name <span className="req">*</span>
              </label>
              <input
                id="auth-name"
                type="text"
                placeholder="Mira Hassan"
                value={name}
                onChange={e => setName(e.target.value)}
                autoComplete="name"
                autoFocus
              />
              {errors.name && <div className="field-err">{errors.name}</div>}
            </div>

            <div className="gd-field">
              <label htmlFor="auth-email">
                Email <span className="req">*</span>
              </label>
              <input
                id="auth-email"
                type="email"
                placeholder="mira@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                autoComplete="email"
              />
              {errors.email && <div className="field-err">{errors.email}</div>}
            </div>

            {serverError && (
              <div className="field-err" style={{ marginTop: 12 }}>{serverError}</div>
            )}

            <button
              type="submit"
              className="gd-btn gd-btn-primary"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="gd-spinner gd-spinner-sm" />
                  Signing in…
                </>
              ) : (
                'Continue →'
              )}
            </button>
          </form>

          <p className="note">
            No password — enter an existing email to resume your projects,
            or a new email to create an account.
          </p>
        </div>
      </div>
      <Footer />
    </div>
  );
}
