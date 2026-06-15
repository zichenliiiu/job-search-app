import { Link, useNavigate, useMatch } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Calendar, ArrowLeft } from 'lucide-react';
import AccountMenu from './AccountMenu';

export default function TopBar({ dates, user, onLogout, isSettings }) {
  const navigate = useNavigate();
  const feedDateMatch = useMatch('/app/feed/:date');
  const dateParam = feedDateMatch?.params?.date ?? null;

  const currentEntry = dateParam ? dates.find(d => d.date === dateParam) : dates[0];
  const currentIdx = currentEntry ? dates.indexOf(currentEntry) : 0;

  const goPrev = () => {
    const nextIdx = currentIdx + 1;
    if (nextIdx < dates.length) navigate(`/app/feed/${dates[nextIdx].date}`);
  };

  const goNext = () => {
    const prevIdx = currentIdx - 1;
    if (prevIdx >= 0) navigate(`/app/feed/${dates[prevIdx].date}`);
  };

  return (
    <header className="topbar">
      {isSettings ? (
        <div className="tb-settings-left">
          <button className="btn btn-ghost back-btn" onClick={() => navigate('/app/feed')}>
            <span className="ic"><ArrowLeft size={17} className="accent-icon" /></span>
            Back to feed
          </button>
          <div className="tb-divider" />
          <span className="tb-context-label">Settings</span>
        </div>
      ) : (
        <Link className="tb-brand" to="/app/feed">
          <svg className="mark" viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" stroke="#14130F" strokeWidth="3" fill="none"/>
            <circle cx="32" cy="32" r="9" fill="#1F6B47"/>
          </svg>
          <span className="word">apt<span className="dot">.</span></span>
        </Link>
      )}

      <div className="tb-right">
        {!isSettings && (
          <div className="scrubber">
            <button
              onClick={goPrev}
              aria-label="Previous day"
              disabled={!dates.length || currentIdx === dates.length - 1}
            >
              <ChevronLeft size={15} />
            </button>
            <span className="label">
              <span className="ic"><Calendar size={14} /></span>
              {currentEntry ? (
                <>
                  <span>{currentEntry.label}</span>
                  <span className="day">· {currentEntry.day}</span>
                </>
              ) : (
                <span>—</span>
              )}
            </span>
            <button
              onClick={goNext}
              aria-label="Next day"
              disabled={currentIdx === 0}
            >
              <ChevronRight size={15} />
            </button>
          </div>
        )}
        {user && <AccountMenu user={user} onLogout={onLogout} />}
      </div>
    </header>
  );
}
