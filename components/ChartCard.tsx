'use client';

import { useEffect, useRef } from 'react';
import { Chart, ChartDataset, ChartOptions, registerables } from 'chart.js';

Chart.register(...registerables);

type ChartCardProps = {
  type: 'line' | 'bar';
  data: {
    labels: string[];
    datasets: ChartDataset<'line' | 'bar', number[]>[];
  };
  options?: ChartOptions<'line' | 'bar'>;
};

export default function ChartCard({ type, data, options }: ChartCardProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chartRef = useRef<Chart<'line' | 'bar'> | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    chartRef.current?.destroy();
    chartRef.current = new Chart(canvasRef.current, {
      type,
      data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1e263a',
            titleColor: '#eef0f8',
            bodyColor: '#8b95b0',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            padding: 10,
          },
        },
        ...(options ?? {}),
      },
    });

    return () => {
      chartRef.current?.destroy();
    };
  }, [type, data, options]);

  return <canvas ref={canvasRef} role="img" style={{ width: '100%', height: '100%' }} />;
}
