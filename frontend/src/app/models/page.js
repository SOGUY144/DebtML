"use client";

import { useState, useEffect } from 'react';
import MetricCard from '@/components/MetricCard';
import PlotlyChart from '@/components/PlotlyChart';

export default function ModelsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    fetch(`${apiUrl}/api/models/evaluation`)
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(e => {
        console.error(e);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading model data...</div>;
  if (!data) return <div>Error loading data.</div>;

  return (
    <div className="slide-in">
      <h2 className="outfit" style={{ fontSize: '1.8rem', marginBottom: '1.5rem', color: 'var(--text-primary)' }}>
        เปรียบเทียบผลโมเดล (Test Year: 2566) - Detailed View
      </h2>
      
      {/* 1. Summary Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
        {data.evaluations.map(model => (
          <div key={model.model_name} className="glass-card" style={{ padding: '1.5rem', textAlign: 'center' }}>
            <h3 className="outfit" style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', marginBottom: '1rem' }}>
              {model.model_name}
            </h3>
            <div className="outfit gradient-text" style={{ fontSize: '2.2rem', fontWeight: '700', marginBottom: '1rem' }}>
              PR-AUC: {model.pr_auc.toFixed(3)}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem', color: 'var(--text-primary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid var(--card-border)' }}>
                <span>F1 (High-Risk)</span>
                <span style={{ fontWeight: '600' }}>{model.f1_high_risk.toFixed(3)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.5rem', borderBottom: '1px solid var(--card-border)' }}>
                <span>Recall (High-Risk)</span>
                <span style={{ fontWeight: '600' }}>{model.recall_high_risk.toFixed(3)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Precision</span>
                <span style={{ fontWeight: '600' }}>{model.precision_high_risk.toFixed(3)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 2. Detailed Charts Row: Confusion Matrix + PR Curve */}
      <h3 className="outfit" style={{ fontSize: '1.4rem', marginBottom: '1rem' }}>วิเคราะห์เจาะลึก (Deep Analysis)</h3>
      {data.evaluations.map(model => {
        // Confusion Matrix Data
        const cm = model.confusion_matrix;
        const z = [[cm[1][0], cm[1][1]], [cm[0][0], cm[0][1]]]; // flip for better visualization (y: True, x: Pred)
        const x = ['Stable (Pred)', 'High-Risk (Pred)'];
        const y = ['High-Risk (True)', 'Stable (True)'];

        const cmData = [{
          z: z,
          x: x,
          y: y,
          type: 'heatmap',
          colorscale: [
            [0, '#161A23'],
            [1, '#FF6B6B']
          ],
          showscale: false,
          text: z,
          texttemplate: "%{text}",
          textfont: { color: "white", size: 16 }
        }];

        const cmLayout = {
          title: { text: `Confusion Matrix: ${model.model_name}`, font: { size: 14, color: '#A0ABCC' } },
          margin: { t: 40, l: 120, r: 20, b: 40 },
          xaxis: { tickfont: { size: 11 } },
          yaxis: { tickfont: { size: 11 } }
        };

        // PR Curve Data
        const prData = [{
          x: model.recall_curve,
          y: model.precision_curve,
          type: 'scatter',
          mode: 'lines',
          fill: 'tozeroy',
          line: { color: '#2ed573', width: 2 },
          fillcolor: 'rgba(46, 213, 115, 0.2)'
        }];

        const prLayout = {
          title: { text: `Precision-Recall Curve`, font: { size: 14, color: '#A0ABCC' } },
          xaxis: { title: 'Recall', range: [0, 1.05], showgrid: true, gridcolor: 'rgba(255,255,255,0.05)' },
          yaxis: { title: 'Precision', range: [0, 1.05], showgrid: true, gridcolor: 'rgba(255,255,255,0.05)' },
          margin: { t: 40, l: 50, r: 20, b: 40 }
        };

        return (
          <div key={`${model.model_name}-charts`} className="glass-card" style={{ padding: '1rem', marginBottom: '1.5rem' }}>
            <h4 style={{ color: 'var(--text-primary)', marginBottom: '1rem', paddingLeft: '1rem' }}>{model.model_name}</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', height: '300px' }}>
              <div style={{ borderRight: '1px dashed var(--card-border)' }}>
                <PlotlyChart data={cmData} layout={cmLayout} />
              </div>
              <div>
                <PlotlyChart data={prData} layout={prLayout} />
              </div>
            </div>
          </div>
        );
      })}

      {/* 3. Feature Importances */}
      <h3 className="outfit" style={{ fontSize: '1.4rem', marginTop: '2rem', marginBottom: '1rem' }}>
        ปัจจัยสำคัญที่สุด (Feature Importances - Random Forest)
      </h3>
      <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '3rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          {data.top_features.map((feat, idx) => (
            <div key={feat.feature} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ width: '30px', color: 'var(--text-secondary)' }}>#{idx + 1}</div>
              <div style={{ flex: 1, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{feat.feature}</div>
              <div style={{ width: '100px', background: 'rgba(255,255,255,0.1)', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${(feat.importance * 100).toFixed(0)}%`, background: 'var(--accent)', height: '100%' }}></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
