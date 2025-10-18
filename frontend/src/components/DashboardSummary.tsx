import React from 'react';
import { DetectionBadge, Classification } from './DetectionBadge';

export interface DashboardSummaryProps {
  authorizedCount: number;
  suspectCount: number;
  unauthorizedCount: number;
  lastUpdated?: Date;
  loading?: boolean;
  error?: string | null;
  onClassificationClick?: (classification: Classification) => void;
}

/**
 * DashboardSummary component displays aggregate detection counts by classification
 * Provides quick overview of detection status for SOC analysts
 */
export function DashboardSummary({
  authorizedCount,
  suspectCount,
  unauthorizedCount,
  lastUpdated,
  loading = false,
  error = null,
  onClassificationClick,
}: DashboardSummaryProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-3 gap-4 p-6 bg-gray-100 rounded-lg animate-pulse">
        <div className="h-20 bg-gray-300 rounded"></div>
        <div className="h-20 bg-gray-300 rounded"></div>
        <div className="h-20 bg-gray-300 rounded"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-700 font-medium">Error loading detection summary</p>
        <p className="text-red-600 text-sm mt-1">{error}</p>
      </div>
    );
  }

  const handleClick = (classification: Classification) => {
    if (onClassificationClick) {
      onClassificationClick(classification);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Detection Summary</h2>
        {lastUpdated && (
          <p className="text-sm text-gray-500">
            Updated {lastUpdated.toLocaleTimeString()}
          </p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Unauthorized Count */}
        <button
          onClick={() => handleClick('unauthorized')}
          className="flex flex-col items-center p-4 bg-red-50 rounded-lg hover:bg-red-100 transition-colors cursor-pointer border-2 border-transparent hover:border-red-300"
          aria-label={`${unauthorizedCount} unauthorized detections`}
        >
          <div className="flex items-center space-x-2 mb-2">
            <DetectionBadge classification="unauthorized" size="sm" />
          </div>
          <span className="text-3xl font-bold text-red-700">{unauthorizedCount}</span>
          <span className="text-sm text-gray-600 mt-1">Unauthorized</span>
        </button>

        {/* Suspect Count */}
        <button
          onClick={() => handleClick('suspect')}
          className="flex flex-col items-center p-4 bg-yellow-50 rounded-lg hover:bg-yellow-100 transition-colors cursor-pointer border-2 border-transparent hover:border-yellow-300"
          aria-label={`${suspectCount} suspect detections`}
        >
          <div className="flex items-center space-x-2 mb-2">
            <DetectionBadge classification="suspect" size="sm" />
          </div>
          <span className="text-3xl font-bold text-yellow-700">{suspectCount}</span>
          <span className="text-sm text-gray-600 mt-1">Suspect</span>
        </button>

        {/* Authorized Count */}
        <button
          onClick={() => handleClick('authorized')}
          className="flex flex-col items-center p-4 bg-green-50 rounded-lg hover:bg-green-100 transition-colors cursor-pointer border-2 border-transparent hover:border-green-300"
          aria-label={`${authorizedCount} authorized detections`}
        >
          <div className="flex items-center space-x-2 mb-2">
            <DetectionBadge classification="authorized" size="sm" />
          </div>
          <span className="text-3xl font-bold text-green-700">{authorizedCount}</span>
          <span className="text-sm text-gray-600 mt-1">Authorized</span>
        </button>
      </div>
    </div>
  );
}

export default DashboardSummary;
