import { createContext, useState, useEffect, useContext } from 'react';
import {
  BrowserRouter, Routes, Route, Navigate, Outlet,
  useLocation, useNavigate, useParams, useOutletContext,
} from 'react-router-dom';
import { Star, TrendingUp } from 'lucide-react';
import TopBar from './components/TopBar';
import LoginPage from './components/LoginPage';
import SettingsPage from './components/SettingsPage';
import PageHeader from './components/PageHeader';
import SummaryRow from './components/SummaryRow';
import Section from './components/Section';

export const AuthContext = createContext(null);

function RequireAuth() {
  const { user, authLoading } = useContext(AuthContext);
  const location = useLocation();
  if (authLoading) return null;
  if (!user) {
    const returnTo = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/?return_to=${returnTo}`} replace />;
  }
  return <Outlet />;
}

function PublicOnlyRoute() {
  const { user, authLoading } = useContext(AuthContext);
  if (authLoading) return null;
  if (user) return <Navigate to="/app/feed" replace />;
  return <Outlet />;
}

function CatchAll() {
  const { user, authLoading } = useContext(AuthContext);
  if (authLoading) return null;
  return <Navigate to={user ? '/app/feed' : '/'} replace />;
}

function AppLayout() {
  const { user, setUser } = useContext(AuthContext);
  const [dates, setDates] = useState([]);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!user) return;
    fetch('/api/dates', { credentials: 'include' })
      .then(r => r.json())
      .then(data => setDates(data));
  }, [user]);

  const handleLogout = () => {
    fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
      .then(() => { setUser(null); navigate('/'); });
  };

  const isSettings = location.pathname.startsWith('/app/settings');

  return (
    <div className="app">
      <main className="main">
        <TopBar dates={dates} user={user} onLogout={handleLogout} isSettings={isSettings} />
        <Outlet context={{ dates }} />
      </main>
    </div>
  );
}

function FeedRoute() {
  const { dates } = useOutletContext();
  const { date: dateParam } = useParams();
  const [feed, setFeed] = useState({ topPicks: [], nextBest: [], syncedAt: '' });
  const [loading, setLoading] = useState(true);

  const currentEntry = dateParam ? dates.find(d => d.date === dateParam) : dates[0];

  useEffect(() => {
    if (!dates.length) return;
    const target = currentEntry || dates[0];
    if (!target) return;
    setLoading(true);
    fetch(`/api/feed?date=${target.date}`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => { setFeed(data); setLoading(false); });
  }, [dates, currentEntry?.date]);

  if (!dates.length) return null;

  return (
    <div className="content">
      <PageHeader topCount={feed.topPicks.length} syncedAt={feed.syncedAt} />
      <SummaryRow topCount={feed.topPicks.length} nextCount={feed.nextBest.length} />
      {!loading && (
        <>
          <Section kind="top"  icon={Star}       title="Top picks"  jobs={feed.topPicks} />
          <Section kind="next" icon={TrendingUp} title="Next best"  jobs={feed.nextBest} />
        </>
      )}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => { setUser(data); setAuthLoading(false); });
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, authLoading }}>
      <BrowserRouter>
        <Routes>
          <Route element={<PublicOnlyRoute />}>
            <Route path="/" element={<LoginPage />} />
          </Route>
          <Route element={<RequireAuth />}>
            <Route path="/app" element={<AppLayout />}>
              <Route index element={<Navigate to="/app/feed" replace />} />
              <Route path="feed" element={<FeedRoute />} />
              <Route path="feed/:date" element={<FeedRoute />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<CatchAll />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}
