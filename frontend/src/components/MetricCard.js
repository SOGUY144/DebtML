export default function MetricCard({ title, value, subtitle, highlight = false }) {
  return (
    <div className="glass-card" style={{ padding: '1.5rem', textAlign: 'center', borderColor: highlight ? 'rgba(255, 107, 107, 0.4)' : undefined }}>
      <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: '600' }}>
        {title}
      </div>
      <div className="outfit gradient-text" style={{ fontSize: '2.5rem', fontWeight: '700', margin: '0.5rem 0', lineHeight: 1.2 }}>
        {value}
      </div>
      {subtitle && (
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          {subtitle}
        </div>
      )}
    </div>
  );
}
