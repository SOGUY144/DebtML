"use client";

import dynamic from 'next/dynamic';
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false, loading: () => <p>Loading chart...</p> });

export default function PlotlyChart({ data, layout, style }) {
  const defaultLayout = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter', color: '#FAFAFA' },
    margin: { t: 40, b: 40, l: 40, r: 20 },
    ...layout
  };

  return (
    <div style={{ width: '100%', height: '100%', ...style }}>
      <Plot
        data={data}
        layout={defaultLayout}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
        config={{ displayModeBar: false }}
      />
    </div>
  );
}
