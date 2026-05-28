import { useState, useEffect } from 'react';
import { Star, TrendingUp } from 'lucide-react';
import TopBar from './components/TopBar';
import PageHeader from './components/PageHeader';
import SummaryRow from './components/SummaryRow';
import Section from './components/Section';

export default function App() {
  const [dates, setDates] = useState([]);
  const [dateIdx, setDateIdx] = useState(0);
  const [tracked, setTracked] = useState(new Set());
  const [feed, setFeed] = useState({ topPicks: [], nextBest: [], syncedAt: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/dates')
      .then(r => r.json())
      .then(data => {
        setDates(data);
      });
  }, []);

  useEffect(() => {
    if (!dates.length) return;
    setLoading(true);
    fetch(`/api/feed?date=${dates[dateIdx].date}`)
      .then(r => r.json())
      .then(data => {
        setFeed(data);
        setLoading(false);
      });
  }, [dateIdx, dates]);

  const toggleTrack = (id) => {
    setTracked(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  return (
    <div className="app">
      <main className="main">
        <TopBar dates={dates} dateIdx={dateIdx} setDateIdx={setDateIdx} />
        <div className="content">
          <PageHeader topCount={feed.topPicks.length} syncedAt={feed.syncedAt} />
          <SummaryRow topCount={feed.topPicks.length} nextCount={feed.nextBest.length} />
          {!loading && (
            <>
              <Section kind="top"  icon={Star}        title="Top picks" jobs={feed.topPicks} tracked={tracked} onTrack={toggleTrack} />
              <Section kind="next" icon={TrendingUp}  title="Next best" jobs={feed.nextBest} tracked={tracked} onTrack={toggleTrack} />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
