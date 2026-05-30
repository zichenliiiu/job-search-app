import { MapPin, ExternalLink, Circle, CheckCircle2 } from 'lucide-react';

export default function JobCard({ job, kind, tracked, onTrack }) {
  return (
    <article className={'jcard ' + kind}>
      <div className="jc-body">
        <div className="jc-main">
          <div className="jc-co">{job.co}</div>
          <div className="jc-role">{job.role}</div>

          <div className="jc-meta">
            <span className="item">
              <span className="ic"><MapPin size={13} /></span>
              <span>{job.loc}</span>
            </span>
            {job.remote && <span className="remote-pill">{job.remote}</span>}
</div>
        </div>
      </div>

      <div className="jc-foot">
        <button className={'track-toggle' + (tracked ? ' on' : '')} onClick={() => onTrack(job.id)}>
          <span className="ic">{tracked ? <CheckCircle2 size={16} /> : <Circle size={16} />}</span>
          <span>{tracked ? 'Applied' : "Haven't applied"}</span>
        </button>
        <div className="jc-actions">
          <a className="btn btn-secondary" href={job.url} target="_blank" rel="noreferrer">
            <ExternalLink size={13} /> Open posting
          </a>
        </div>
      </div>
    </article>
  );
}
