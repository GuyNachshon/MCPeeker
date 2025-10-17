/**
 * Trendline chart component - time-series visualization
 *
 * Reference: FR-012 (Dashboard), T112
 */

import React, { useEffect, useState } from 'react';

interface TrendlineDataPoint {
  timestamp: string;
  total_count: number;
  authorized_count: number;
  suspect_count: number;
  unauthorized_count: number;
}

interface TrendlineData {
  data_points: TrendlineDataPoint[];
  granularity: string;
  time_range: string;
}

interface TrendlineChartProps {
  granularity?: 'hour' | 'day' | 'week';
  days?: number;
}

export const TrendlineChart: React.FC<TrendlineChartProps> = ({
  granularity = 'day',
  days = 7,
}) => {
  const [data, setData] = useState<TrendlineData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [granularity, days]);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Calculate start time based on days
      const endTime = new Date();
      const startTime = new Date(endTime.getTime() - days * 24 * 60 * 60 * 1000);

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/v1/analytics/trendlines?` +
          `granularity=${granularity}&` +
          `start_time=${startTime.toISOString()}&` +
          `end_time=${endTime.toISOString()}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch trendline data');
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chart data');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-4">
        <p className="text-red-800 text-sm">{error}</p>
      </div>
    );
  }

  if (!data || data.data_points.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-8 text-center">
        <p className="text-gray-600">No trendline data available for this time period.</p>
      </div>
    );
  }

  // Find max value for scaling
  const maxValue = Math.max(...data.data_points.map(p => p.total_count));

  // Format timestamp based on granularity
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    if (granularity === 'hour') {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } else if (granularity === 'day') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  };

  // Simple line chart using SVG
  const chartWidth = 800;
  const chartHeight = 300;
  const padding = 40;
  const graphWidth = chartWidth - 2 * padding;
  const graphHeight = chartHeight - 2 * padding;

  const xScale = graphWidth / (data.data_points.length - 1 || 1);
  const yScale = maxValue > 0 ? graphHeight / maxValue : 1;

  // Generate path data for each classification
  const generatePath = (getCount: (point: TrendlineDataPoint) => number): string => {
    return data.data_points
      .map((point, index) => {
        const x = padding + index * xScale;
        const y = chartHeight - padding - getCount(point) * yScale;
        return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
      })
      .join(' ');
  };

  const totalPath = generatePath(p => p.total_count);
  const authorizedPath = generatePath(p => p.authorized_count);
  const suspectPath = generatePath(p => p.suspect_count);
  const unauthorizedPath = generatePath(p => p.unauthorized_count);

  return (
    <div className="space-y-4">
      {/* SVG Chart */}
      <div className="overflow-x-auto">
        <svg width={chartWidth} height={chartHeight} className="border border-gray-200 rounded bg-white">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((factor, i) => {
            const y = chartHeight - padding - graphHeight * factor;
            return (
              <g key={i}>
                <line
                  x1={padding}
                  y1={y}
                  x2={chartWidth - padding}
                  y2={y}
                  stroke="#e5e7eb"
                  strokeWidth="1"
                />
                <text
                  x={padding - 10}
                  y={y + 5}
                  textAnchor="end"
                  fontSize="12"
                  fill="#6b7280"
                >
                  {Math.round(maxValue * factor)}
                </text>
              </g>
            );
          })}

          {/* Lines */}
          <path d={totalPath} fill="none" stroke="#3b82f6" strokeWidth="3" />
          <path d={authorizedPath} fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="5,5" />
          <path d={suspectPath} fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="5,5" />
          <path d={unauthorizedPath} fill="none" stroke="#ef4444" strokeWidth="2" strokeDasharray="5,5" />

          {/* Data points */}
          {data.data_points.map((point, index) => {
            const x = padding + index * xScale;
            const y = chartHeight - padding - point.total_count * yScale;
            return (
              <circle
                key={index}
                cx={x}
                cy={y}
                r="4"
                fill="#3b82f6"
                className="hover:r-6 cursor-pointer"
                title={`${formatTimestamp(point.timestamp)}: ${point.total_count} detections`}
              />
            );
          })}

          {/* X-axis labels */}
          {data.data_points.map((point, index) => {
            if (index % Math.ceil(data.data_points.length / 10) !== 0) return null;
            const x = padding + index * xScale;
            return (
              <text
                key={index}
                x={x}
                y={chartHeight - padding + 20}
                textAnchor="middle"
                fontSize="12"
                fill="#6b7280"
              >
                {formatTimestamp(point.timestamp)}
              </text>
            );
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 pt-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-blue-500"></div>
          <span className="text-xs text-gray-600">Total</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-green-500 border-dashed"></div>
          <span className="text-xs text-gray-600">Authorized</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-yellow-500 border-dashed"></div>
          <span className="text-xs text-gray-600">Suspect</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-red-500 border-dashed"></div>
          <span className="text-xs text-gray-600">Unauthorized</span>
        </div>
      </div>

      {/* Stats */}
      <div className="text-center text-sm text-gray-600 pt-2">
        Showing {data.data_points.length} data points over {days} day{days !== 1 ? 's' : ''}
      </div>
    </div>
  );
};

export default TrendlineChart;
