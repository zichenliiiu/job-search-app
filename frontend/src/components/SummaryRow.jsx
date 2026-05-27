export default function SummaryRow({ topCount, nextCount }) {
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
