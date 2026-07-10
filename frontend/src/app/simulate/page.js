"use client";

import { useState, useEffect, useRef } from 'react';
import MetricCard from '@/components/MetricCard';
import StatusBadge from '@/components/StatusBadge';

// How long to wait after the user stops moving a slider before we call the API.
const DEBOUNCE_MS = 400;

export default function SimulatePage() {
  const [provinces, setProvinces] = useState([]);
  const [selectedProv, setSelectedProv] = useState('กรุงเทพมหานคร');

  // Values shown in the UI update instantly as the slider is dragged.
  const [debtGrowth, setDebtGrowth] = useState(0);
  const [incomeGrowth, setIncomeGrowth] = useState(0);

  // Debounced values are what actually get sent to the API, so we don't
  // fire a request for every single tick while the user is still dragging.
  const [debouncedDebtGrowth, setDebouncedDebtGrowth] = useState(0);
  const [debouncedIncomeGrowth, setDebouncedIncomeGrowth] = useState(0);

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // Tracks the most recently fired request so late/out-of-order responses
  // from earlier requests get ignored instead of overwriting a newer result
  // (this is what was causing the predicted numbers to "flicker").
  const requestIdRef = useRef(0);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    fetch(`${apiUrl}/api/provinces`)
      .then(res => res.json())
      .then(d => setProvinces(d.provinces))
      .catch(console.error);
  }, []);

  // Debounce: only update the "real" values once the sliders have been
  // still for DEBOUNCE_MS. Rapid changes while dragging get collapsed
  // into a single update.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedDebtGrowth(debtGrowth);
      setDebouncedIncomeGrowth(incomeGrowth);
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [debtGrowth, incomeGrowth]);

  useEffect(() => {
    if (!selectedProv) return;

    const currentRequestId = ++requestIdRef.current;
    const controller = new AbortController();

    setLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    fetch(`${apiUrl}/api/models/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        province: selectedProv,
        debt_growth: debouncedDebtGrowth / 100,
        income_growth: debouncedIncomeGrowth / 100
      })
    })
      .then(res => res.json())
      .then(d => {
        // Ignore this response if a newer request has already been fired -
        // prevents an older, slower response from clobbering a fresher one.
        if (currentRequestId !== requestIdRef.current) return;
        setResult(d);
        setLoading(false);
      })
      .catch(e => {
        if (e.name === 'AbortError') return;
        if (currentRequestId !== requestIdRef.current) return;
        console.error(e);
        setLoading(false);
      });

    return () => controller.abort();
  }, [selectedProv, debouncedDebtGrowth, debouncedIncomeGrowth]);

  return (
    <div className="slide-in">
      <h2 className="outfit" style={{ fontSize: '1.8rem', marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
        จำลองนโยบาย (What-If Simulation)
      </h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '2rem' }}>
        {/* Controls Sidebar */}
        <div className="glass-card" style={{ padding: '1.5rem', height: 'fit-content' }}>
          <h3 className="outfit" style={{ fontSize: '1.2rem', marginBottom: '1.5rem' }}>พารามิเตอร์นโยบาย</h3>
          
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              เลือกจังหวัดเป้าหมาย
            </label>
            <select 
              value={selectedProv} 
              onChange={(e) => setSelectedProv(e.target.value)}
              style={{
                width: '100%', padding: '10px', borderRadius: '8px',
                background: 'rgba(0,0,0,0.2)', color: 'white',
                border: '1px solid var(--card-border)', outline: 'none'
              }}
            >
              {provinces.map(p => <option key={p} value={p} style={{color:'black'}}>{p}</option>)}
            </select>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              <span>หนี้สินเพิ่ม/ลด (%)</span>
              <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{debtGrowth > 0 ? '+' : ''}{debtGrowth}%</span>
            </label>
            <input 
              type="range" min="-50" max="50" step="1" 
              value={debtGrowth} onChange={(e) => setDebtGrowth(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent)' }}
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              <span>รายได้เพิ่ม/ลด (%)</span>
              <span style={{ color: '#2ed573', fontWeight: 600 }}>{incomeGrowth > 0 ? '+' : ''}{incomeGrowth}%</span>
            </label>
            <input 
              type="range" min="-50" max="50" step="1" 
              value={incomeGrowth} onChange={(e) => setIncomeGrowth(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#2ed573' }}
            />
          </div>
        </div>

        {/* Results Area */}
        <div>
          {loading && !result && <div>กำลังคำนวณผลจำลอง...</div>}
          
          {result && result.detail && (
             <div style={{ color: 'var(--risk)' }}>Error: {result.detail}</div>
          )}

          {result && !result.detail && (
            <div style={{
              opacity: loading ? 0.5 : 1,
              transition: 'opacity 0.15s ease',
              pointerEvents: loading ? 'none' : 'auto'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '2rem', marginBottom: '2rem' }}>
                <MetricCard title="DTI จำลอง (Simulated)" value={result.simulated_dti.toFixed(2)} highlight={result.simulated_dti > 1.0} />
                <div style={{ flex: 1, padding: '1rem 2rem', background: 'rgba(0,0,0,0.2)', borderRadius: '16px', border: '1px dashed var(--card-border)' }}>
                  <h4 style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>ผลประเมินสรุป:</h4>
                  <p style={{ fontSize: '1.1rem' }}>
                    เมื่อหนี้สินเปลี่ยน <b style={{color: 'var(--accent)'}}>{debtGrowth}%</b> และรายได้เปลี่ยน <b style={{color: '#2ed573'}}>{incomeGrowth}%</b><br/>
                    ส่งผลให้ DTI ของ <b>{result.province}</b> ขยับไปที่ {result.simulated_dti.toFixed(2)}
                  </p>
                </div>
              </div>
              
              <h3 className="outfit" style={{ fontSize: '1.4rem', marginBottom: '1.5rem' }}>ผลทำนายจาก 3 โมเดล</h3>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
                {Object.entries(result.results).map(([name, res]) => (
                  <div key={name} className="glass-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem', fontWeight: 600 }}>{name}</div>
                    <div style={{ marginBottom: '1.5rem' }}>
                      <StatusBadge status={res.status} />
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      ความน่าจะเป็น: {(res.probability_high_risk * 100).toFixed(1)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      <div style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '1rem', fontStyle: 'italic' }}>
        *โมเดลนี้ calibrate จากข้อมูลที่ส่วนใหญ่เป็น Stable อาจ underestimate ความเสี่ยงในสถานการณ์สุดขีด*
      </div>
    </div>
  );
}