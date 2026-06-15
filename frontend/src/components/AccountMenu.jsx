import { useState, useEffect, useRef } from 'react';
import { Settings, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

function getInitials(name, email) {
  if (name) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0][0].toUpperCase();
  }
  return email ? email[0].toUpperCase() : '?';
}

export default function AccountMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();
  const initials = getInitials(user.name, user.email);

  useEffect(() => {
    if (!open) return;
    const onMouseDown = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKeyDown = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const handleSettings = () => {
    setOpen(false);
    navigate('/app/settings');
  };

  const handleLogout = () => {
    setOpen(false);
    onLogout();
  };

  return (
    <div className="account-menu" ref={ref}>
      <button
        className={`avatar-btn${open ? ' open' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-label="Account menu"
        aria-expanded={open}
      >
        {initials}
      </button>
      {open && (
        <div className="account-dropdown">
          <div className="acct-header">
            <div className="avatar-sm">{initials}</div>
            <div className="acct-info">
              <span className="acct-name">{user.name || user.email}</span>
              <span className="acct-email">{user.email}</span>
            </div>
          </div>
          <div className="acct-item" role="button" tabIndex={0} onClick={handleSettings} onKeyDown={e => e.key === 'Enter' && handleSettings()}>
            <Settings size={16} />
            <span>Settings</span>
          </div>
          <div className="acct-divider" />
          <div className="acct-item acct-item-logout" role="button" tabIndex={0} onClick={handleLogout} onKeyDown={e => e.key === 'Enter' && handleLogout()}>
            <LogOut size={16} />
            <span>Log out</span>
          </div>
        </div>
      )}
    </div>
  );
}
