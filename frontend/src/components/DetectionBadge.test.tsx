import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DetectionBadge } from './DetectionBadge';

describe('DetectionBadge', () => {
  // T040: Test rendering green badge for "authorized" classification
  it('renders green badge for authorized classification', () => {
    render(<DetectionBadge classification="authorized" />);

    const badge = screen.getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Authorized');
    expect(badge).toHaveClass('bg-green-500', 'text-white');
  });

  // T041: Test rendering yellow badge for "suspect" classification
  it('renders yellow badge for suspect classification', () => {
    render(<DetectionBadge classification="suspect" />);

    const badge = screen.getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Suspect');
    expect(badge).toHaveClass('bg-yellow-500', 'text-black');
  });

  // T042: Test rendering red badge for "unauthorized" classification
  it('renders red badge for unauthorized classification', () => {
    render(<DetectionBadge classification="unauthorized" />);

    const badge = screen.getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('Unauthorized');
    expect(badge).toHaveClass('bg-red-500', 'text-white');
  });

  it('applies correct size classes', () => {
    const { rerender } = render(<DetectionBadge classification="authorized" size="sm" />);
    let badge = screen.getByRole('status');
    expect(badge).toHaveClass('px-2', 'py-0.5', 'text-xs');

    rerender(<DetectionBadge classification="authorized" size="md" />);
    badge = screen.getByRole('status');
    expect(badge).toHaveClass('px-3', 'py-1', 'text-sm');

    rerender(<DetectionBadge classification="authorized" size="lg" />);
    badge = screen.getByRole('status');
    expect(badge).toHaveClass('px-4', 'py-2', 'text-base');
  });

  it('shows tooltip when showTooltip is true', () => {
    render(<DetectionBadge classification="authorized" showTooltip={true} />);

    const badge = screen.getByRole('status');
    expect(badge).toHaveAttribute('title', 'Approved MCP or low risk score');
  });

  it('uses custom tooltip text when provided', () => {
    render(
      <DetectionBadge
        classification="unauthorized"
        showTooltip={true}
        tooltipText="Custom tooltip"
      />
    );

    const badge = screen.getByRole('status');
    expect(badge).toHaveAttribute('title', 'Custom tooltip');
  });

  it('applies additional className when provided', () => {
    render(<DetectionBadge classification="authorized" className="ml-4" />);

    const badge = screen.getByRole('status');
    expect(badge).toHaveClass('ml-4');
  });

  it('has accessible label', () => {
    render(<DetectionBadge classification="suspect" />);

    const badge = screen.getByRole('status');
    expect(badge).toHaveAttribute('aria-label', 'Classification: Suspect');
  });
});
