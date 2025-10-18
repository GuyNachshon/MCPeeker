import React from 'react';
import { Classification } from './DetectionBadge';

export interface DetectionFilterState {
  hideAuthorized: boolean;
  searchQuery: string;
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
  classifications: Classification[];
}

export interface DetectionFilterProps {
  filters: DetectionFilterState;
  onFilterChange: (filters: DetectionFilterState) => void;
  totalCount?: number;
  filteredCount?: number;
}

/**
 * DetectionFilter component provides filtering controls for detection list
 * Allows SOC analysts to focus on threats by hiding authorized MCPs
 */
export function DetectionFilter({
  filters,
  onFilterChange,
  totalCount,
  filteredCount,
}: DetectionFilterProps) {
  const handleHideAuthorizedToggle = () => {
    onFilterChange({
      ...filters,
      hideAuthorized: !filters.hideAuthorized,
    });
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      searchQuery: e.target.value,
    });
  };

  const handleClearFilters = () => {
    onFilterChange({
      hideAuthorized: false,
      searchQuery: '',
      dateRange: { start: null, end: null },
      classifications: [],
    });
  };

  const hasActiveFilters =
    filters.hideAuthorized ||
    filters.searchQuery.length > 0 ||
    filters.dateRange.start !== null ||
    filters.dateRange.end !== null ||
    filters.classifications.length > 0;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="space-y-3">
        {/* Search Input */}
        <div>
          <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
            Search
          </label>
          <input
            id="search"
            type="text"
            value={filters.searchQuery}
            onChange={handleSearchChange}
            placeholder="Search composite ID, host, etc."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Hide Authorized Toggle */}
        <div className="flex items-center">
          <input
            id="hideAuthorized"
            type="checkbox"
            checked={filters.hideAuthorized}
            onChange={handleHideAuthorizedToggle}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="hideAuthorized" className="ml-2 text-sm text-gray-700">
            Hide authorized MCPs
          </label>
        </div>

        {/* Result Count */}
        {totalCount !== undefined && filteredCount !== undefined && (
          <div className="pt-2 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              Showing <span className="font-semibold">{filteredCount}</span> of{' '}
              <span className="font-semibold">{totalCount}</span> detections
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DetectionFilter;
