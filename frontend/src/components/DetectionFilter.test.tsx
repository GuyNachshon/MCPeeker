import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DetectionFilter, DetectionFilterState } from './DetectionFilter';

describe('DetectionFilter', () => {
  const defaultFilters: DetectionFilterState = {
    hideAuthorized: false,
    searchQuery: '',
    dateRange: { start: null, end: null },
    classifications: [],
  };

  // T046: Test toggle behavior for "Hide authorized" checkbox
  it('toggles hide authorized filter when checkbox is clicked', () => {
    const mockOnFilterChange = vi.fn();
    render(
      <DetectionFilter
        filters={defaultFilters}
        onFilterChange={mockOnFilterChange}
      />
    );

    const checkbox = screen.getByLabelText('Hide authorized MCPs') as HTMLInputElement;
    expect(checkbox.checked).toBe(false);

    // Click checkbox
    fireEvent.click(checkbox);

    expect(mockOnFilterChange).toHaveBeenCalledWith({
      ...defaultFilters,
      hideAuthorized: true,
    });
  });

  it('shows checkbox as checked when hideAuthorized is true', () => {
    const mockOnFilterChange = vi.fn();
    render(
      <DetectionFilter
        filters={{ ...defaultFilters, hideAuthorized: true }}
        onFilterChange={mockOnFilterChange}
      />
    );

    const checkbox = screen.getByLabelText('Hide authorized MCPs') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
  });

  // T047: Test search query update
  it('updates search query when input changes', () => {
    const mockOnFilterChange = vi.fn();
    render(
      <DetectionFilter
        filters={defaultFilters}
        onFilterChange={mockOnFilterChange}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search composite ID, host, etc.');
    fireEvent.change(searchInput, { target: { value: 'testhost' } });

    expect(mockOnFilterChange).toHaveBeenCalledWith({
      ...defaultFilters,
      searchQuery: 'testhost',
    });
  });

  it('displays current search query value', () => {
    const mockOnFilterChange = vi.fn();
    render(
      <DetectionFilter
        filters={{ ...defaultFilters, searchQuery: 'existing query' }}
        onFilterChange={mockOnFilterChange}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search composite ID, host, etc.') as HTMLInputElement;
    expect(searchInput.value).toBe('existing query');
  });

  it('displays result counts when provided', () => {
    const mockOnFilterChange = vi.fn();
    render(
      <DetectionFilter
        filters={defaultFilters}
        onFilterChange={mockOnFilterChange}
        totalCount={100}
        filteredCount={45}
      />
    );

    expect(screen.getByText('Showing')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('shows clear all button when filters are active', () => {
    const mockOnFilterChange = vi.fn();
    render(
      <DetectionFilter
        filters={{ ...defaultFilters, hideAuthorized: true }}
        onFilterChange={mockOnFilterChange}
      />
    );

    const clearButton = screen.getByText('Clear all');
    expect(clearButton).toBeInTheDocument();

    // Click clear button
    fireEvent.click(clearButton);

    expect(mockOnFilterChange).toHaveBeenCalledWith({
      hideAuthorized: false,
      searchQuery: '',
      dateRange: { start: null, end: null },
      classifications: [],
    });
  });

  it('hides clear all button when no filters are active', () => {
    const mockOnFilterChange = vi.fn();
    render(
      <DetectionFilter
        filters={defaultFilters}
        onFilterChange={mockOnFilterChange}
      />
    );

    const clearButton = screen.queryByText('Clear all');
    expect(clearButton).not.toBeInTheDocument();
  });

  it('shows clear all button when search query is present', () => {
    const mockOnFilterChange = vi.fn();
    render(
      <DetectionFilter
        filters={{ ...defaultFilters, searchQuery: 'test' }}
        onFilterChange={mockOnFilterChange}
      />
    );

    const clearButton = screen.getByText('Clear all');
    expect(clearButton).toBeInTheDocument();
  });
});
