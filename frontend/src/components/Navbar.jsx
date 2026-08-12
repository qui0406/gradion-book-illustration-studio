import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import gradionLogo from '../assets/gradion-logo.png';

export default function Navbar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '?';

  const handleSignOut = () => {
    signOut();
    navigate('/auth');
  };

  return (
    <nav className="gd-nav">
      <div className="gd-nav-inner">
        <span
          className="gd-nav-brand"
          onClick={() => navigate('/')}
          role="link"
          tabIndex={0}
          onKeyDown={e => e.key === 'Enter' && navigate('/')}
        >
          <img src={gradionLogo} alt="Gradion" style={{ height: 22, display: 'block' }} />
        </span>

        <div className="gd-nav-links">
          <span
            className={`gd-nav-link ${location.pathname === '/' ? 'active' : ''}`}
            onClick={() => navigate('/')}
            role="link"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && navigate('/')}
          >
            Projects
          </span>
        </div>

        <div className="gd-nav-user">
          <div className="gd-nav-avatar" title={user?.name}>{initials}</div>
          <span>{user?.name}</span>
          <button className="gd-nav-signout" onClick={handleSignOut}>
            Sign Out
          </button>
        </div>
      </div>
    </nav>
  );
}
