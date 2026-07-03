import MetricCard from '@/components/MetricCard';
import StatusBadge from '@/components/StatusBadge';

// Fetch data from FastAPI backend
async function getOverview() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const res = await fetch(`${apiUrl}/api/overview`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error('Failed to fetch overview data');
  }
  return res.json();
}

export default async function OverviewPage() {
  let data;
  try {
    data = await getOverview();
  } catch (error) {
    return <div>Error loading data: {error.message}. Make sure FastAPI is running.</div>;
  }

  return (
    <div>
      <h2 className="outfit" style={{ fontSize: '1.8rem', marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
        ภาพรวมระดับประเทศ (ปี {data.latest_year})
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
        <MetricCard title="จังหวัดทั้งหมด" value={data.n_provinces} />
        <MetricCard title="จังหวัดกลุ่มเสี่ยง (High-Risk)" value={data.n_high_risk} highlight={true} />
        <MetricCard title="อัตรา DTI เฉลี่ย (เท่า)" value={data.avg_dti.toFixed(2)} subtitle="หนี้สินเฉลี่ยต่อรายได้ต่อปี" />
        <MetricCard title="ปีล่าสุด" value={data.latest_year} />
      </div>

      <h3 className="outfit" style={{ fontSize: '1.4rem', marginBottom: '1rem' }}>
        Top 10 จังหวัดที่มีภาระหนี้สูงสุด (DTI)
      </h3>
      
      <div className="glass-card" style={{ padding: '0', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.2)', borderBottom: '1px solid var(--card-border)' }}>
              <th style={{ padding: '1rem 1.5rem', color: 'var(--text-secondary)' }}>อันดับ</th>
              <th style={{ padding: '1rem 1.5rem', color: 'var(--text-secondary)' }}>จังหวัด</th>
              <th style={{ padding: '1rem 1.5rem', color: 'var(--text-secondary)' }}>DTI (เท่า)</th>
              <th style={{ padding: '1rem 1.5rem', color: 'var(--text-secondary)' }}>สถานะ</th>
            </tr>
          </thead>
          <tbody>
            {data.top10_dti.map((prov, index) => (
              <tr key={prov.Province} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)', transition: 'background 0.2s' }}>
                <td style={{ padding: '1rem 1.5rem' }}>{index + 1}</td>
                <td style={{ padding: '1rem 1.5rem', fontWeight: '600' }}>{prov.Province}</td>
                <td style={{ padding: '1rem 1.5rem', color: prov.Label === 1 ? 'var(--accent)' : 'var(--text-primary)' }}>
                  {prov.DTI.toFixed(2)}
                </td>
                <td style={{ padding: '1rem 1.5rem' }}>
                  <StatusBadge status={prov.Status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
