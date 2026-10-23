import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import type { ChartOptions } from 'chart.js';
import { Bar } from 'react-chartjs-2';
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
  BarElement,
  Title,
  Tooltip,
  Legend
);

export interface BarChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
    borderWidth?: number;
  }[];
}

interface BarChartProps {
  data: BarChartData;
  title?: string;
  height?: number;
  className?: string;
}

/** Solid ink bars, hairline value grid, no category gridlines. */
const BarChart: React.FC<BarChartProps> = ({ data, title, height = 400, className = '' }) => {
  const t = useChartTheme();
  const options: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    elements: { bar: { borderRadius: 0, borderWidth: 0 } },
    plugins: {
      // A single series needs no legend; the panel/title names it.
      legend: { ...legendOptions(t), display: data.datasets.length > 1 },
      title: titleOptions(t, title),
      tooltip: tooltipOptions(t),
    },
    scales: {
      x: categoryAxis(t),
      y: valueAxis(t),
    },
  };

  const themed = {
    ...data,
    datasets: data.datasets.map((d) => ({
      ...d,
      backgroundColor: d.backgroundColor ?? t.ink,
      borderColor: d.borderColor ?? t.ink,
      borderWidth: d.borderWidth ?? 0,
    })),
  };

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <Bar data={themed} options={options} />
    </div>
  );
};

export default BarChart;
