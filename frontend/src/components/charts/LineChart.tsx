import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import type { ChartOptions } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { useTheme } from '../../contexts/ThemeContext';
import { chartTheme } from './chartTheme';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
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
  }[];
}

interface LineChartProps {
  data: LineChartData;
  title?: string;
  height?: number;
  className?: string;
}

const LineChart: React.FC<LineChartProps> = ({ data, title, height = 400, className = '' }) => {
  const { isDarkMode } = useTheme();
  const c = chartTheme(isDarkMode);
  const options: ChartOptions<'line'> = {
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
          color: c.label,
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
          color: c.label,
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
      <Line data={data} options={options} />
    </div>
  );
};

export default LineChart; 