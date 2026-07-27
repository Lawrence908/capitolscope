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
import { useTheme } from '../../contexts/ThemeContext';
import { chartTheme } from './chartTheme';

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

const BarChart: React.FC<BarChartProps> = ({ data, title, height = 400, className = '' }) => {
  const { isDarkMode } = useTheme();
  const c = chartTheme(isDarkMode);
  const options: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: c.label,
          font: {
            size: 12,
          },
        },
      },
      title: {
        display: !!title,
        text: title,
        color: c.title,
        font: {
          size: 16,
          weight: 'bold',
        },
      },
      tooltip: {
        backgroundColor: c.tooltipBg,
        titleColor: c.tooltipTitle,
        bodyColor: c.tooltipBody,
        borderColor: c.tooltipBorder,
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        ticks: {
          color: c.tick,
          font: {
            size: 11,
          },
        },
        grid: {
          color: c.grid,
        },
      },
      y: {
        ticks: {
          color: c.tick,
          font: {
            size: 11,
          },
        },
        grid: {
          color: c.grid,
        },
      },
    },
  };

  return (
    <div className={`w-full ${className}`} style={{ height }}>
      <Bar data={data} options={options} />
    </div>
  );
};

export default BarChart; 