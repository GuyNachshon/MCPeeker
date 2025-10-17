/**
 * Detection list component
 *
 * Reference: US1 (Detection viewing), FR-001 (Real-time detection)
 */

import React, { useEffect, useState } from 'react';
import { useDetectionStore } from '../store/detections';
import type { Detection } from '../api/client';

interface DetectionListProps {
  onSelectDetection?: (detection: Detection) => void;
}

export const DetectionList: React.FC<DetectionListProps> = ({ onSelectDetection }) => {
  const {
    detections,
    filters,
    isLoading,
    error,
    skip,
    limit,
    total,
    fetchDetections,
    setFilters,
    clearFilters,
    nextPage,
    prevPage,
  } = useDetectionStore();

  const [classificationFilter, setClassificationFilter] = useState<string>('');

  useEffect(() => {
    fetchDetections();
  }, [fetchDetections]);

  const handleClassificationChange = (classification: string) => {
    setClassificationFilter(classification);
    if (classification) {
      setFilters({ classification: classification as any });
    } else {
      clearFilters();
    }
  };

  const getClassificationBadge = (classification: string) => {
    const styles = {
      authorized: 'bg-green-100 text-green-800',
      suspect: 'bg-yellow-100 text-yellow-800',
      unauthorized: 'bg-red-100 text-red-800',
    };
    return styles[classification as keyof typeof styles] || 'bg-gray-100 text-gray-800';
  };

  const getScoreBadge = (score: number) => {
    if (score <= 4) return 'bg-green-500';
    if (score <= 8) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-semibold">Error loading detections</h3>
        <p className="text-red-600 text-sm mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">Filter by classification:</label>
          <select
            value={classificationFilter}
            onChange={(e) => handleClassificationChange(e.target.value)}
            className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="">All</option>
            <option value="authorized">Authorized</option>
            <option value="suspect">Suspect</option>
            <option value="unauthorized">Unauthorized</option>
          </select>

          {filters.classification && (
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Detection list */}
      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : detections.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">No detections found</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Host ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Classification
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Evidence Count
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Registry Match
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {detections.map((detection) => (
                <tr
                  key={detection.event_id}
                  onClick={() => onSelectDetection?.(detection)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(detection.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
                    {detection.host_id.substring(0, 16)}...
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${getScoreBadge(detection.score)}`}></div>
                      <span className="text-sm font-medium text-gray-900">{detection.score}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getClassificationBadge(detection.classification)}`}>
                      {detection.classification}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {detection.evidence.length}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {detection.registry_matched ? (
                      <span className="text-green-600 text-sm">✓ Matched</span>
                    ) : (
                      <span className="text-gray-400 text-sm">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > limit && (
        <div className="bg-white rounded-lg shadow px-4 py-3 flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing {skip + 1} to {Math.min(skip + limit, total)} of {total} results
          </div>
          <div className="flex gap-2">
            <button
              onClick={prevPage}
              disabled={skip === 0}
              className="px-4 py-2 border rounded-md text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              onClick={nextPage}
              disabled={skip + limit >= total}
              className="px-4 py-2 border rounded-md text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DetectionList;
