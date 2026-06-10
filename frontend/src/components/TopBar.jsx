import { ChevronLeft, ChevronRight, Calendar, LogOut } from 'lucide-react';

export default function TopBar({ dates, dateIdx, setDateIdx, user, onLogout }) {
  const d = dates[dateIdx];
  return (
    <header className="topbar">
      <a className="tb-brand" href="#">
        <svg className="mark" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="28" stroke="#14130F" strokeWidth="3" fill="none"/>
          <circle cx="32" cy="32" r="9" fill="#1F6B47"/>
        </svg>
        <span className="word">apt<span className="dot">.</span></span>
      </a>
      <div className="tb-right">
        <div className="scrubber">
          <button onClick={() => setDateIdx(Math.min(dates.length - 1, dateIdx + 1))} aria-label="Previous day" disabled={!dates.length || dateIdx === dates.length - 1}>
            <ChevronLeft size={15} />
          </button>
          <span className="label">
            <span className="ic"><Calendar size={14} /></span>
            {d ? (
              <>
                <span>{d.label}</span>
                <span className="day">· {d.day}</span>
              </>
            ) : (
              <span>—</span>
            )}
          </span>
          <button onClick={() => setDateIdx(Math.max(0, dateIdx - 1))} aria-label="Next day" disabled={dateIdx === 0}>
            <ChevronRight size={15} />
          </button>
        </div>
        {user && (
          <button className="btn btn-ghost" onClick={onLogout} title={user.email}>
            <span className="ic"><LogOut size={14} /></span>
            Sign out
          </button>
        )}
      </div>
    </header>
  );
}
