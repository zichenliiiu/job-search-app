export default function PageHeader({ topCount, syncedAt }) {
  return (
    <div className="page-head">
      <h1>
        <em>{topCount}</em> openings worth a look today.
      </h1>
      <div className="sub">{syncedAt}</div>
    </div>
  );
}
