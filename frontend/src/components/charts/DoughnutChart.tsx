import React from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import type { ChartOptions } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import { legendOptions, neutralRamp, titleOptions, tooltipOptions, useChartTheme } from './chartTheme';

ChartJS.register(
  ArcElement,
  Title,
  Tooltip,
  Legend
);

export interface DoughnutChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
    borderWidth?: number;
  }[];
}

interface DoughnutChartProps {
  data: DoughnutChartData;
  title?: string;
  height?: number;
  className?: string;
}

/**
 * Neutral-ramp slices (ink to gray) separated by surface-colored gaps.
 * The legend labels every slice, so meaning never rides on color alone.
 */
const DoughnutChart: React.FC<DoughnutChartProps> = ({ data, title, height = 400, className = '' }) => {
  const t = useChartTheme();
  const options: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: legendOptions(t, 'right'),
      title: titleOptions(t, title),
      tooltip: {
        ...tooltipOptions(t),
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.parsed;
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
            const percentage = ((value / total) * 100).toFixed(1);
            return `${label}: ${value} (${percentage}%)`;
          }
        }
      },
    },
  };

  const themed = {
    ...data,
    datasets: data.datasets.map((d) => ({
      ...d,
      backgroundColor: d.backgroundColor ?? neutralRamp(t, d.data.length),
      borderColor: d.borderColor ?? t.surface,
      borderWidth: d.borderWidth ?? 2,
    })),
  };

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <Doughnut data={themed} options={options} />
    </div>
  );
};

export default DoughnutChart;
