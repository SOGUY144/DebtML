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
        // Custom CSS Grid for Confusion Matrix
        const cmElement = (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', height: '100%', justifyContent: 'center', alignItems: 'center' }}>
            <div style={{ fontSize: '14px', color: '#A0ABCC', fontFamily: 'Outfit' }}>Confusion Matrix: {model.model_name}</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 80px 80px', gap: '4px', textAlign: 'center', fontSize: '12px' }}>
              <div></div>
              <div style={{ color: 'var(--text-secondary)', paddingBottom: '5px' }}>Stable<br/>(Pred)</div>
              <div style={{ color: 'var(--text-secondary)', paddingBottom: '5px' }}>High-Risk<br/>(Pred)</div>
              
              <div style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: '10px' }}>Stable<br/>(True)</div>
              <div style={{ background: 'rgba(46, 213, 115, 0.1)', border: '1px solid #2ed573', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '15px', fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {cm[0][0]}
              </div>
              <div style={{ background: 'rgba(255, 107, 107, 0.1)', border: '1px solid #FF6B6B', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '15px', fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {cm[0][1]}
              </div>

              <div style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: '10px' }}>High-Risk<br/>(True)</div>
              <div style={{ background: 'rgba(255, 107, 107, 0.1)', border: '1px solid #FF6B6B', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '15px', fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {cm[1][0]}
              </div>
              <div style={{ background: 'rgba(46, 213, 115, 0.1)', border: '1px solid #2ed573', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '15px', fontSize: '20px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {cm[1][1]}
              </div>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              *TN=ทายถูก Stable, TP=ทายถูก High-Risk, FP/FN=ทายผิด
            </div>
            {model.model_name === 'Logistic Regression' && (
              <div style={{ marginTop: '4px', fontSize: '11px', color: '#ffb142', background: 'rgba(255, 177, 66, 0.1)', padding: '6px', borderRadius: '4px', maxWidth: '250px', textAlign: 'center', lineHeight: '1.4' }}>
                ⚠️ หมายเหตุ: โมเดลนี้ถูกออกแบบให้ Recall สูง เพื่อไม่พลาดจังหวัดที่เสี่ยงจริง จึงอาจเตือนเกินจริงในบางกรณี (False Positive สูง)
              </div>
            )}
          </div>
        );

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
                {cmElement}
              </div>
              <div>
                <PlotlyChart data={prData} layout={prLayout} />
              </div>
            </div>
          </div>
        );
      })}

      {/* 3. Feature Importances - Logistic Regression > Random Forest > LightGBM */}
      {(data.feature_importances || []).map(fi => (
        <div key={`${fi.model_name}-importances`}>
          <h3 className="outfit" style={{ fontSize: '1.4rem', marginTop: '2rem', marginBottom: '1rem' }}>
            ปัจจัยสำคัญที่สุด (Feature Importances - {fi.model_name})
          </h3>
          <div className="glass-card" style={{ padding: '1.5rem', marginBottom: '3rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              {fi.top_features.map((feat, idx) => (
                <div key={feat.feature} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ width: '30px', color: 'var(--text-secondary)' }}>#{idx + 1}</div>
                  <div style={{ flex: 1, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{feat.feature.replace(/1$/, '')}</div>
                  <div style={{ width: '100px', background: 'rgba(255,255,255,0.1)', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${(feat.importance * 100).toFixed(0)}%`, background: 'var(--accent)', height: '100%' }}></div>
                  </div>
                  <div style={{ width: '45px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {feat.importance.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}