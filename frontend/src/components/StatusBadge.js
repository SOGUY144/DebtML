export default function StatusBadge({ status }) {
  const isRisk = status === "High-Risk" || status === 1;
  
  return (
    <span style={{
      background: isRisk ? 'var(--risk-gradient)' : 'var(--stable-gradient)',
      color: isRisk ? 'white' : '#0E1117',
      padding: '4px 12px',
      borderRadius: '20px',
      fontSize: '0.8rem',
      fontWeight: '600',
      display: 'inline-block',
      boxShadow: isRisk ? '0 4px 10px rgba(255, 65, 108, 0.3)' : '0 4px 10px rgba(56, 239, 125, 0.2)'
    }}>
      {isRisk ? "High-Risk" : "Stable"}
    </span>
  );
}
