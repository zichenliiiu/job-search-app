import { useState } from 'react';
import { Star, TrendingUp } from 'lucide-react';
import TopBar from './components/TopBar';
import PageHeader from './components/PageHeader';
import SummaryRow from './components/SummaryRow';
import Section from './components/Section';

// Placeholder until API is wired up
const PLACEHOLDER = {
  topPicks: [],
  nextBest: [],
  syncedAt: '',
};

export default function App() {
  const [dateIdx, setDateIdx] = useState(0);
  const [tracked, setTracked] = useState(new Set());
  const [feed, setFeed] = useState(PLACEHOLDER);

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
        <TopBar dateIdx={dateIdx} setDateIdx={setDateIdx} />
        <div className="content">
          <PageHeader topCount={feed.topPicks.length} syncedAt={feed.syncedAt} />
          <SummaryRow topCount={feed.topPicks.length} nextCount={feed.nextBest.length} />
          <Section kind="top"  icon={Star}        title="Top picks" jobs={feed.topPicks} tracked={tracked} onTrack={toggleTrack} />
          <Section kind="next" icon={TrendingUp}  title="Next best" jobs={feed.nextBest} tracked={tracked} onTrack={toggleTrack} />
        </div>
      </main>
    </div>
  );
}
