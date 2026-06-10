import { useState, useEffect } from 'react';
import { ArrowLeft, X } from 'lucide-react';

export default function SettingsPage({ onBack }) {
  const [criteriaText, setCriteriaText] = useState('');
  const [allCompanies, setAllCompanies] = useState([]);
  const [followed, setFollowed] = useState([]);
  const [newCompany, setNewCompany] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch('/api/criteria', { credentials: 'include' }).then(r => r.json()),
      fetch('/api/companies', { credentials: 'include' }).then(r => r.json()),
    ]).then(([criteria, companies]) => {
      setCriteriaText(criteria.criteria_text || '');
      setAllCompanies(companies.all || []);
      setFollowed(companies.followed || []);
      setLoading(false);
    });
  }, []);

  const toggleCompany = (company) => {
    setFollowed(f => f.includes(company) ? f.filter(c => c !== company) : [...f, company]);
  };

  const addCompany = () => {
    const name = newCompany.trim();
    if (!name || followed.includes(name)) return;
    setFollowed(f => [...f, name]);
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
        body: JSON.stringify({ criteria_text: criteriaText }),
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

  const extraCompanies = followed.filter(c => !allCompanies.includes(c));

  return (
    <div className="content settings-page">
      <div className="page-head">
        <button className="btn btn-ghost back-btn" onClick={onBack}>
          <span className="ic"><ArrowLeft size={14} /></span>
          Back to feed
        </button>
        <h1>Settings</h1>
      </div>

      <section className="settings-section">
        <h2>Ranking criteria</h2>
        <p className="settings-hint">Describe what "top", "next best", and "skip" jobs look like to you.</p>
        <textarea
          value={criteriaText}
          onChange={e => setCriteriaText(e.target.value)}
          rows={14}
          placeholder="Describe the roles you're looking for..."
        />
      </section>

      <section className="settings-section">
        <h2>Companies you follow</h2>
        <p className="settings-hint">Only jobs from these companies will be ranked and included in your digest.</p>

        {extraCompanies.length > 0 && (
          <div className="company-chips">
            {extraCompanies.map(c => (
              <span className="chip" key={c}>
                {c}
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

        <div className="company-list">
          {allCompanies.map(c => (
            <label className="company-item" key={c}>
              <input
                type="checkbox"
                checked={followed.includes(c)}
                onChange={() => toggleCompany(c)}
              />
              {c}
            </label>
          ))}
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
