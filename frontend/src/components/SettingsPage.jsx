import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

export default function SettingsPage() {
  const [topDescription, setTopDescription] = useState('');
  const [nextBestDescription, setNextBestDescription] = useState('');
  const [followed, setFollowed] = useState([]);
  const [untracked, setUntracked] = useState([]);
  const [trackedNames, setTrackedNames] = useState([]);
  const [newCompany, setNewCompany] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch('/api/criteria', { credentials: 'include' }).then(r => r.json()),
      fetch('/api/companies', { credentials: 'include' }).then(r => r.json()),
    ]).then(([criteria, companies]) => {
      setTopDescription(criteria.top_description || '');
      setNextBestDescription(criteria.next_best_description || '');
      setFollowed(companies.followed || []);
      setUntracked(companies.untracked || []);
      setTrackedNames(companies.tracked || []);
      setLoading(false);
    });
  }, []);

  const addCompany = () => {
    const name = newCompany.trim();
    if (!name || followed.includes(name)) return;
    setFollowed(f => [...f, name]);
    if (!trackedNames.includes(name) && !untracked.includes(name)) {
      setUntracked(u => [...u, name]);
    }
    setNewCompany('');
  };

  const removeCompany = (company) => {
    setFollowed(f => f.filter(c => c !== company));
  };

  const handleSave = () => {
    setSaving(true);
    Promise.all([
      fetch('/api/criteria', {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ top_description: topDescription, next_best_description: nextBestDescription }),
      }),
      fetch('/api/companies', {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ companies: followed }),
      }),
    ]).then(() => {
      setSaving(false);
      setSavedAt(new Date());
    });
  };

  if (loading) return null;

  return (
    <div className="content settings-page">
      <div className="page-head">
        <h1><em>Settings</em></h1>
      </div>

      <section className="settings-section">
        <h2>Ranking criteria</h2>
        <p className="settings-hint">Describe what your "top" and "next best" jobs look like. Anything that doesn't match either will be skipped.</p>
        <h3>Top</h3>
        <textarea
          value={topDescription}
          onChange={e => setTopDescription(e.target.value)}
          rows={7}
          placeholder="Describe the roles that are the best fit for you..."
        />
        <h3>Next best</h3>
        <textarea
          value={nextBestDescription}
          onChange={e => setNextBestDescription(e.target.value)}
          rows={7}
          placeholder="Describe the roles that are a good but not ideal fit..."
        />
      </section>

      <section className="settings-section">
        <h2>Companies you follow</h2>
        <p className="settings-hint">Only jobs from these companies will be ranked and included in your digest.</p>

        {followed.length > 0 && (
          <div className="company-chips">
            {followed.map(c => (
              <span className={`chip${untracked.includes(c) ? ' chip-pending' : ''}`} key={c}>
                {c}
                {untracked.includes(c) && <span className="chip-pending-label">pending</span>}
                <button onClick={() => removeCompany(c)} aria-label={`Remove ${c}`}><X size={12} /></button>
              </span>
            ))}
          </div>
        )}

        <div className="company-add">
          <input
            type="text"
            value={newCompany}
            onChange={e => setNewCompany(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addCompany()}
            placeholder="Add a company by name..."
          />
          <button className="btn btn-secondary" onClick={addCompany}>Add</button>
        </div>
      </section>

      <div className="settings-actions">
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save changes'}
        </button>
        {savedAt && <span className="settings-saved">Saved</span>}
      </div>
    </div>
  );
}
