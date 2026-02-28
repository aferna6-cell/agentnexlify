export default function SkeletonLoader() {
  return (
    <div className="fade-in">
      <div className="skeleton-row">
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
        <div className="skeleton skeleton-card" />
      </div>
      <div className="skeleton skeleton-block" />
      <div className="skeleton skeleton-block" style={{ height: 200 }} />
    </div>
  );
}
