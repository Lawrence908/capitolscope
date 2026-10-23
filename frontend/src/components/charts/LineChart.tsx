import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import type { ChartOptions } from 'chart.js';
import { Line } from 'react-chartjs-2';
import {
  categoryAxis,
  legendOptions,
  titleOptions,
  tooltipOptions,
  useChartTheme,
  valueAxis,
} from './chartTheme';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Title,
  Tooltip,
  Legend
);

export interface LineChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
    borderWidth?: number;
    fill?: boolean;
    tension?: number;
    borderDash?: number[];
  }[];
}

interface LineChartProps {
  data: LineChartData;
  title?: string;
  height?: number;
  className?: string;
}

/** Thick ink strokes, no point dots, hairline value grid only. */
const LineChart: React.FC<LineChartProps> = ({ data, title, height = 400, className = '' }) => {
  const t = useChartTheme();
  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    elements: {
      point: { radius: 0, hoverRadius: 4, hitRadius: 8 },
      line: { borderCapStyle: 'square' },
    },
    plugins: {
      legend: { ...legendOptions(t), display: data.datasets.length > 1 },
      title: titleOptions(t, title),
      tooltip: tooltipOptions(t),
    },
    scales: {
      x: { ...categoryAxis(t), ticks: { ...categoryAxis(t).ticks, maxTicksLimit: 8, autoSkip: true } },
      y: valueAxis(t),
    },
  };

  const themed = {
    ...data,
    datasets: data.datasets.map((d, i) => ({
      ...d,
      borderColor: d.borderColor ?? (i === 0 ? t.ink : t.bench),
      backgroundColor: d.backgroundColor ?? 'transparent',
      borderWidth: d.borderWidth ?? (i === 0 ? 3 : 2),
      pointHoverBackgroundColor: d.borderColor ?? (i === 0 ? t.ink : t.bench),
    })),
  };

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <Line data={themed} options={options} />
    </div>
  );
};

export default LineChart;
