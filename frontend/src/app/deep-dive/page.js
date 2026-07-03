"use client";

import { useState, useEffect } from 'react';
import MetricCard from '@/components/MetricCard';
import StatusBadge from '@/components/StatusBadge';
import PlotlyChart from '@/components/PlotlyChart';

export default function DeepDivePage() {
  const [provinces, setProvinces] = useState([]);
  const [selectedProv, setSelectedProv] = useState('กรุงเทพมหานคร');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    fetch(`${apiUrl}/api/provinces`)
      .then(res => res.json())
      .then(d => {
        setProvinces(d.provinces);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    fetch(`${apiUrl}/api/province/${encodeURIComponent(selectedProv)}`)
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(e => {
        console.error(e);
        setLoading(false);
      });
  }, [selectedProv]);

  if (!data && loading) return <div>Loading data...</div>;
  if (!data || data.detail) return <div>Error loading data: {data?.detail || 'Unknown error'}</div>;

  // Chart Data preparation
  const years = data.time_series.map(d => d.Year);
  const dti = data.time_series.map(d => d.DTI);
  const debt = data.time_series.map(d => d.Debt);
  const income = data.time_series.map(d => d.Annual_Income);

  const chartData = [
    {
      x: years, y: debt, type: 'scatter', mode: 'lines+markers',
      name: 'หนี้สิน (Debt)', yaxis: 'y',
      line: { color: '#FF6B6B', width: 3 }
    },
    {
      x: years, y: income, type: 'scatter', mode: 'lines+markers',
      name: 'รายได้ต่อปี (Income)', yaxis: 'y',
      line: { color: '#2ed573', width: 3 }
    },
    {
      x: years, y: dti, type: 'bar',
      name: 'DTI', yaxis: 'y2',
      marker: { color: 'rgba(252, 160, 72, 0.4)' }
    }
  ];

  const chartLayout = {
    title: { text: `แนวโน้มเศรษฐกิจจังหวัด ${selectedProv}`, font: { size: 18, family: 'Outfit' } },
    yaxis: { title: 'บาท (THB)', gridcolor: 'rgba(255,255,255,0.05)' },
    yaxis2: { title: 'DTI (เท่า)', overlaying: 'y', side: 'right', showgrid: false },
    xaxis: { tickmode: 'linear', dtick: 2 },
    legend: { orientation: 'h', y: -0.2 }
  };

  return (
    <div className="slide-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2 className="outfit" style={{ fontSize: '1.8rem', color: 'var(--text-primary)' }}>
          เจาะลึกรายจังหวัด
        </h2>
        <select 
          value={selectedProv} 
          onChange={(e) => setSelectedProv(e.target.value)}
          style={{
            padding: '10px 16px',
            borderRadius: '8px',
            background: 'rgba(255,255,255,0.1)',
            color: 'white',
            border: '1px solid var(--card-border)',
            fontFamily: 'Inter',
            fontSize: '1rem',
            outline: 'none'
          }}
        >
          {provinces.map(p => <option key={p} value={p} style={{ color: 'black' }}>{p}</option>)}
        </select>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
        <MetricCard title="หนี้สินเฉลี่ยล่าสุด" value={`฿${data.latest_debt.toLocaleString()}`} />
        <MetricCard title="รายได้ต่อปีเฉลี่ยล่าสุด" value={`฿${data.latest_income.toLocaleString()}`} />
        <MetricCard title="DTI ล่าสุด" value={data.latest_dti.toFixed(2)} highlight={data.latest_dti > 1.0} />
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '0.5rem', fontWeight: 600 }}>สถานะความเสี่ยง</div>
          <StatusBadge status={data.status} />
        </div>
      </div>

      <div className="glass-card" style={{ height: '500px', padding: '1rem' }}>
        <PlotlyChart data={chartData} layout={chartLayout} />
      </div>
    </div>
  );
}
