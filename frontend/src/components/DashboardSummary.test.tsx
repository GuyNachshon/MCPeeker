import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DashboardSummary } from './DashboardSummary';

describe('DashboardSummary', () => {
  // T043: Test displaying correct counts for each classification
  it('displays correct counts for each classification', () => {
    render(
      <DashboardSummary
        authorizedCount={10}
        suspectCount={5}
        unauthorizedCount={2}
      />
    );

    // Check unauthorized count
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Unauthorized')).toBeInTheDocument();

    // Check suspect count
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Suspect')).toBeInTheDocument();

    // Check authorized count
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('Authorized')).toBeInTheDocument();
  });

  // T044: Test loading state
  it('shows loading state when loading prop is true', () => {
    render(
      <DashboardSummary
        authorizedCount={0}
        suspectCount={0}
        unauthorizedCount={0}
        loading={true}
      />
    );

    // Check for loading skeleton
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);

    // Counts should not be visible during loading
    expect(screen.queryByText('Detection Summary')).not.toBeInTheDocument();
  });

  // T045: Test error state
  it('displays error message when error prop is provided', () => {
    const errorMessage = 'Failed to fetch detection data';
    render(
      <DashboardSummary
        authorizedCount={0}
        suspectCount={0}
        unauthorizedCount={0}
        error={errorMessage}
      />
    );

    expect(screen.getByText('Error loading detection summary')).toBeInTheDocument();
    expect(screen.getByText(errorMessage)).toBeInTheDocument();

    // Counts should not be visible when error is shown
    expect(screen.queryByText('Detection Summary')).not.toBeInTheDocument();
  });

  it('displays last updated timestamp when provided', () => {
    const lastUpdated = new Date('2025-10-18T10:00:00Z');
    render(
      <DashboardSummary
        authorizedCount={1}
        suspectCount={2}
        unauthorizedCount={3}
        lastUpdated={lastUpdated}
      />
    );

    // Check for timestamp (format depends on locale, so just check it exists)
    const timestamp = screen.getByText(/Updated/);
    expect(timestamp).toBeInTheDocument();
  });

  it('calls onClassificationClick when a classification is clicked', () => {
    const mockOnClick = vi.fn();
    render(
      <DashboardSummary
        authorizedCount={10}
        suspectCount={5}
        unauthorizedCount={2}
        onClassificationClick={mockOnClick}
      />
    );

    // Click unauthorized button
    const unauthorizedButton = screen.getByLabelText('2 unauthorized detections');
    fireEvent.click(unauthorizedButton);
    expect(mockOnClick).toHaveBeenCalledWith('unauthorized');

    // Click suspect button
    const suspectButton = screen.getByLabelText('5 suspect detections');
    fireEvent.click(suspectButton);
    expect(mockOnClick).toHaveBeenCalledWith('suspect');

    // Click authorized button
    const authorizedButton = screen.getByLabelText('10 authorized detections');
    fireEvent.click(authorizedButton);
    expect(mockOnClick).toHaveBeenCalledWith('authorized');
  });

  it('renders without crashing with zero counts', () => {
    render(
      <DashboardSummary
        authorizedCount={0}
        suspectCount={0}
        unauthorizedCount={0}
      />
    );

    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getAllByText('0')).toHaveLength(3);
  });
});
