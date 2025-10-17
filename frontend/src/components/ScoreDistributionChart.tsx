/**
 * Score distribution chart component - histogram visualization
 *
 * Reference: FR-012 (Dashboard), T111
 */

import React, { useEffect, useState } from 'react';

interface ScoreBucket {
  score_min: number;
  score_max: number;
  count: number;
  percentage: number;
}

interface ScoreDistributionData {
  buckets: ScoreBucket[];
  total_detections: number;
  time_range: string;
}

export const ScoreDistributionChart: React.FC = () => {
  const [data, setData] = useState<ScoreDistributionData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/v1/analytics/score-distribution`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch score distribution data');
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

  if (!data || data.total_detections === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded p-8 text-center">
        <p className="text-gray-600">No detection data available for this time period.</p>
      </div>
    );
  }

  const maxCount = Math.max(...data.buckets.map(b => b.count));

  const getBucketColor = (scoreMin: number) => {
    if (scoreMin <= 4) return 'bg-green-500';
    if (scoreMin <= 8) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getBucketLabel = (scoreMin: number, scoreMax: number) => {
    if (scoreMin === 0 && scoreMax === 4) return 'Authorized (0-4)';
    if (scoreMin === 5 && scoreMax === 8) return 'Suspect (5-8)';
    if (scoreMin === 9 && scoreMax === 15) return 'Unauthorized (9-15)';
    return `Very High (${scoreMin}+)`;
  };

  return (
    <div className="space-y-4">
      {/* Chart */}
      <div className="flex items-end justify-between gap-2 h-64">
        {data.buckets.map((bucket, index) => {
          const heightPercent = maxCount > 0 ? (bucket.count / maxCount) * 100 : 0;

          return (
            <div key={index} className="flex-1 flex flex-col items-center">
              {/* Bar */}
              <div className="w-full flex flex-col justify-end items-center" style={{ height: '200px' }}>
                <div
                  className={`w-full ${getBucketColor(bucket.score_min)} rounded-t transition-all duration-300 hover:opacity-80`}
                  style={{ height: `${heightPercent}%` }}
                  title={`${bucket.count} detections (${bucket.percentage.toFixed(1)}%)`}
                >
                  {bucket.count > 0 && (
                    <div className="text-white text-sm font-semibold text-center pt-2">
                      {bucket.count}
                    </div>
                  )}
                </div>
              </div>

              {/* Label */}
              <div className="mt-2 text-center">
                <p className="text-xs font-medium text-gray-700">
                  {getBucketLabel(bucket.score_min, bucket.score_max)}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {bucket.percentage.toFixed(1)}%
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 pt-4 border-t border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded"></div>
          <span className="text-xs text-gray-600">Authorized (≤4)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-500 rounded"></div>
          <span className="text-xs text-gray-600">Suspect (5-8)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <span className="text-xs text-gray-600">Unauthorized (≥9)</span>
        </div>
      </div>

      {/* Stats */}
      <div className="text-center text-sm text-gray-600 pt-2">
        Total detections: <strong>{data.total_detections.toLocaleString()}</strong>
      </div>
    </div>
  );
};

export default ScoreDistributionChart;
