import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';

const DAYS = [
  { key: 'today', label: 'Today',      day: 'Wed · Mar 12' },
  { key: 'yest',  label: 'Yesterday',  day: 'Tue · Mar 11' },
  { key: '2d',    label: '2 days ago', day: 'Mon · Mar 10' },
  { key: '3d',    label: '3 days ago', day: 'Sun · Mar 9'  },
];

export default function TopBar({ dateIdx, setDateIdx }) {
  const d = DAYS[dateIdx];
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
          <button onClick={() => setDateIdx(Math.min(DAYS.length - 1, dateIdx + 1))} aria-label="Previous day">
            <ChevronLeft size={15} />
          </button>
          <span className="label">
            <span className="ic"><Calendar size={14} /></span>
            <span>{d.label}</span>
            <span className="day">· {d.day}</span>
          </span>
          <button onClick={() => setDateIdx(Math.max(0, dateIdx - 1))} aria-label="Next day" disabled={dateIdx === 0}>
            <ChevronRight size={15} />
          </button>
        </div>
      </div>
    </header>
  );
}
