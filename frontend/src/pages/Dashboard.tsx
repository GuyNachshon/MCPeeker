/**
 * Dashboard page - main analytics and metrics view
 *
 * Reference: FR-012 (Dashboard), T110
 */

import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import ScoreDistributionChart from '../components/ScoreDistributionChart';
import TrendlineChart from '../components/TrendlineChart';

interface DashboardSummary {
  total_detections: number;
  total_detections_24h: number;
  active_hosts: number;
  classification_breakdown: {
    authorized: number;
    suspect: number;
    unauthorized: number;
  };
  average_score: number;
  high_risk_detections: number;
  registry_match_rate: number;
}

export const Dashboard: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();

    // Auto-refresh every 60 seconds
    const interval = setInterval(fetchDashboardData, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch summary data
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/v1/analytics/summary`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const data = await response.json();
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !summary) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Dashboard</h3>
          <p className="text-red-800">{error}</p>
          <button
            onClick={fetchDashboardData}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  const totalClassifications =
    summary.classification_breakdown.authorized +
    summary.classification_breakdown.suspect +
    summary.classification_breakdown.unauthorized;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
        <p className="text-gray-600">MCP detection analytics and system overview</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">Total Detections</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{summary.total_detections.toLocaleString()}</p>
          <p className="text-sm text-gray-600 mt-2">
            +{summary.total_detections_24h} in last 24h
          </p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">Active Hosts</p>
          <p className="text-3xl font-bold text-blue-600 mt-2">{summary.active_hosts}</p>
          <p className="text-sm text-gray-600 mt-2">Unique endpoints detected</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">High Risk</p>
          <p className="text-3xl font-bold text-red-600 mt-2">{summary.high_risk_detections}</p>
          <p className="text-sm text-gray-600 mt-2">Score ≥ 9 (unauthorized)</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">Registry Match Rate</p>
          <p className="text-3xl font-bold text-green-600 mt-2">
            {summary.registry_match_rate.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-600 mt-2">Authorized MCPs</p>
        </div>
      </div>

      {/* Classification Breakdown */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Classification Breakdown</h2>
        <div className="grid grid-cols-3 gap-6">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-3">
              <span className="text-3xl font-bold text-green-700">
                {totalClassifications > 0
                  ? Math.round((summary.classification_breakdown.authorized / totalClassifications) * 100)
                  : 0}
                %
              </span>
            </div>
            <p className="text-sm font-medium text-gray-500 uppercase">Authorized</p>
            <p className="text-2xl font-bold text-green-700">{summary.classification_breakdown.authorized}</p>
          </div>

          <div className="text-center">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-yellow-100 rounded-full mb-3">
              <span className="text-3xl font-bold text-yellow-700">
                {totalClassifications > 0
                  ? Math.round((summary.classification_breakdown.suspect / totalClassifications) * 100)
                  : 0}
                %
              </span>
            </div>
            <p className="text-sm font-medium text-gray-500 uppercase">Suspect</p>
            <p className="text-2xl font-bold text-yellow-700">{summary.classification_breakdown.suspect}</p>
          </div>

          <div className="text-center">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-red-100 rounded-full mb-3">
              <span className="text-3xl font-bold text-red-700">
                {totalClassifications > 0
                  ? Math.round((summary.classification_breakdown.unauthorized / totalClassifications) * 100)
                  : 0}
                %
              </span>
            </div>
            <p className="text-sm font-medium text-gray-500 uppercase">Unauthorized</p>
            <p className="text-2xl font-bold text-red-700">{summary.classification_breakdown.unauthorized}</p>
          </div>
        </div>
      </div>

      {/* Score Distribution Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Score Distribution</h2>
        <ScoreDistributionChart />
      </div>

      {/* Trendline Chart */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Detection Trends (Last 7 Days)</h2>
        <TrendlineChart granularity="day" days={7} />
      </div>

      {/* Info Footer */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Dashboard Auto-Refresh:</strong> This dashboard refreshes automatically every 60 seconds to show
          the latest detection data. Average score: <strong>{summary.average_score.toFixed(1)}</strong>
        </p>
      </div>
    </div>
  );
};

export default Dashboard;
