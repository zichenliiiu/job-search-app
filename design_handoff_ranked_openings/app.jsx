// Ranked Openings — Apt design system, restyled from reference screenshot.

const { useState, useMemo } = React;

// ────────────────────────────────────────────────────────────
// Top bar — brand + date scrubber
// ────────────────────────────────────────────────────────────
const DAYS = [
  { key: "today",   label: "Today",        day: "Wed · Mar 12" },
  { key: "yest",    label: "Yesterday",    day: "Tue · Mar 11" },
  { key: "2d",      label: "2 days ago",   day: "Mon · Mar 10" },
  { key: "3d",      label: "3 days ago",   day: "Sun · Mar 9"  },
];

function TopBar({ dateIdx, setDateIdx }) {
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
            <IconChevronLeft size={15} />
          </button>
          <span className="label">
            <span className="ic"><IconCalendar size={14} /></span>
            <span>{d.label}</span>
            <span className="day">· {d.day}</span>
          </span>
          <button onClick={() => setDateIdx(Math.max(0, dateIdx - 1))} aria-label="Next day" disabled={dateIdx === 0}>
            <IconChevronRight size={15} />
          </button>
        </div>
      </div>
    </header>
  );
}

// ────────────────────────────────────────────────────────────
// Summary / legend row
// ────────────────────────────────────────────────────────────
function PageHeader({ topCount, nextCount }) {
  return (
    <div className="page-head">
      <h1>
        <em>{topCount}</em> openings worth a look today.
      </h1>
      <div className="sub">Wed · Mar 12 · Updated 14 min ago</div>
    </div>
  );
}

function SummaryRow({ topCount, nextCount }) {
  return (
    <div className="summary">
      <span className="legend">
        <span className="swatch top" />
        <span className="num">{topCount}</span>
        <span className="lbl">top picks</span>
      </span>
      <span className="legend">
        <span className="swatch next" />
        <span className="num">{nextCount}</span>
        <span className="lbl">next best</span>
      </span>
      <div className="updated">{topCount + nextCount} openings</div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Job card
// ────────────────────────────────────────────────────────────
function JobCard({ job, kind, tracked, onTrack }) {
  return (
    <article className={"jcard " + kind}>
      <div className="jc-body">
        <div className="jc-main">
          <div className="jc-co">{job.co}</div>
          <div className="jc-role">{job.role}</div>

          <div className="jc-meta">
            <span className="item">
              <span className="ic"><IconMapPin size={13} /></span>
              <span>{job.loc}</span>
            </span>
            {job.remote && <span className="remote-pill">{job.remote}</span>}
            <span className="item">
              <span className="ic num" style={{ fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1 }}>$</span>
              <span className="num">{job.salary}</span>
            </span>
            <span className="item muted">
              <span className="ic"><IconClock size={13} /></span>
              <span className="num">{job.posted}</span>
            </span>
          </div>
        </div>
      </div>

      <div className="jc-foot">
        <button className={"track-toggle" + (tracked ? " on" : "")} onClick={() => onTrack(job.id)}>
          <span className="ic">{tracked ? <IconCheckCircle size={16} /> : <IconCircle size={16} />}</span>
          <span>{tracked ? "Applied" : "Haven't applied"}</span>
        </button>
        <div className="jc-actions">
          <a className="btn btn-secondary" href={job.url} target="_blank" rel="noreferrer">
            <IconExternalLink size={13} /> Open posting
          </a>
        </div>
      </div>
    </article>
  );
}

// ────────────────────────────────────────────────────────────
// Section
// ────────────────────────────────────────────────────────────
function Section({ kind, icon: Ic, title, jobs, tracked, onTrack }) {
  return (
    <section className="section">
      <header className={"section-head " + kind}>
        <span className="bar" />
        <span className="icon"><Ic size={16} /></span>
        <span className="title">{title}</span>
        <span className="count">{jobs.length} {jobs.length === 1 ? "opening" : "openings"}</span>
      </header>
      <div className="card-list">
        {jobs.map(j => (
          <JobCard key={j.id} job={j} kind={kind}
                   tracked={tracked.has(j.id)} onTrack={onTrack} />
        ))}
      </div>
    </section>
  );
}

// ────────────────────────────────────────────────────────────
// Tweaks
// ────────────────────────────────────────────────────────────
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "top",
  "density": "comfortable",
  "showGreeting": true
}/*EDITMODE-END*/;

function TweakControls({ t, setTweak }) {
  return (
    <>
      <TweakSection title="Layout">
        <TweakRadio label="Accent stripe"
          value={t.accent} onChange={v => setTweak("accent", v)}
          options={[
            { value: "top", label: "Top" },
            { value: "left", label: "Left" },
            { value: "none", label: "None" },
          ]} />
        <TweakRadio label="Density"
          value={t.density} onChange={v => setTweak("density", v)}
          options={[
            { value: "comfortable", label: "Comfortable" },
            { value: "compact", label: "Compact" },
          ]} />
      </TweakSection>
      <TweakSection title="Header">
        <TweakToggle label="Italic accent on count" value={t.showGreeting} onChange={v => setTweak("showGreeting", v)} />
      </TweakSection>
    </>
  );
}

// ────────────────────────────────────────────────────────────
// App
// ────────────────────────────────────────────────────────────
function App() {
  const [dateIdx, setDateIdx] = useState(0);
  const [tracked, setTracked] = useState(new Set());
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);

  const toggleTrack = (id) => {
    setTracked(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const rootClasses = [
    "app",
    `accent-${t.accent}`,
    `density-${t.density}`,
    t.showGreeting ? "" : "greet-hidden",
  ].filter(Boolean).join(" ");

  return (
    <div className={rootClasses}>
      <main className="main">
        <TopBar dateIdx={dateIdx} setDateIdx={setDateIdx} />
        <div className="content">
          <PageHeader topCount={RANKED.topPicks.length} nextCount={RANKED.nextBest.length} />
          <SummaryRow topCount={RANKED.topPicks.length} nextCount={RANKED.nextBest.length} />
          <Section kind="top"  icon={IconStar}        title="Top picks"  jobs={RANKED.topPicks}  tracked={tracked} onTrack={toggleTrack} />
          <Section kind="next" icon={IconTrendingUp}  title="Next best"  jobs={RANKED.nextBest}  tracked={tracked} onTrack={toggleTrack} />
        </div>
      </main>
      <TweaksPanel title="Tweaks">
        <TweakControls t={t} setTweak={setTweak} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
