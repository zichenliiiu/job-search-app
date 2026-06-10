import { useState, useEffect } from 'react';
import { Star, TrendingUp } from 'lucide-react';
import TopBar from './components/TopBar';
import PageHeader from './components/PageHeader';
import SummaryRow from './components/SummaryRow';
import Section from './components/Section';
import LoginPage from './components/LoginPage';

export default function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [dates, setDates] = useState([]);
  const [dateIdx, setDateIdx] = useState(0);
  const [feed, setFeed] = useState({ topPicks: [], nextBest: [], syncedAt: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        setUser(data);
        setAuthLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!user) return;
    fetch('/api/dates', { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        setDates(data);
      });
  }, [user]);

  useEffect(() => {
    if (!user || !dates.length) return;
    setLoading(true);
    fetch(`/api/feed?date=${dates[dateIdx].date}`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        setFeed(data);
        setLoading(false);
      });
  }, [user, dateIdx, dates]);

  const handleLogout = () => {
    fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
      .then(() => setUser(null));
  };

  if (authLoading) return null;
  if (!user) return <LoginPage />;

  return (
    <div className="app">
      <main className="main">
        <TopBar dates={dates} dateIdx={dateIdx} setDateIdx={setDateIdx} user={user} onLogout={handleLogout} />
        <div className="content">
          <PageHeader topCount={feed.topPicks.length} syncedAt={feed.syncedAt} />
          <SummaryRow topCount={feed.topPicks.length} nextCount={feed.nextBest.length} />
          {!loading && (
            <>
              <Section kind="top"  icon={Star}        title="Top picks" jobs={feed.topPicks} />
              <Section kind="next" icon={TrendingUp}  title="Next best" jobs={feed.nextBest} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
