import JobCard from './JobCard';

export default function Section({ kind, icon: Icon, title, jobs, tracked, onTrack }) {
  return (
    <section className="section">
      <header className={'section-head ' + kind}>
        <span className="bar" />
        <span className="icon"><Icon size={16} /></span>
        <span className="title">{title}</span>
        <span className="count">{jobs.length} {jobs.length === 1 ? 'opening' : 'openings'}</span>
      </header>
      <div className="card-list">
        {jobs.map(j => (
          <JobCard key={j.id} job={j} kind={kind} tracked={tracked.has(j.id)} onTrack={onTrack} />
        ))}
      </div>
    </section>
  );
}
