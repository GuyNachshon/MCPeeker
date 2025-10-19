import React from 'react';

export type Classification = 'authorized' | 'suspect' | 'unauthorized';

export interface DetectionBadgeProps {
  classification: Classification;
  size?: 'sm' | 'md' | 'lg';
  showTooltip?: boolean;
  tooltipText?: string;
  className?: string;
}

const badgeStyles: Record<Classification, string> = {
  authorized: 'bg-green-500 text-white',
  suspect: 'bg-yellow-500 text-black',
  unauthorized: 'bg-red-500 text-white',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
  lg: 'px-4 py-2 text-base',
};

const defaultTooltips: Record<Classification, string> = {
  authorized: 'Approved MCP or low risk score',
  suspect: 'Medium risk score - review recommended',
  unauthorized: 'High risk score - action required',
};

/**
 * DetectionBadge component displays classification status with color coding
 * Used in detection lists, detail views, and dashboard summary
 */
export function DetectionBadge({
  classification,
  size = 'md',
  showTooltip = false,
  tooltipText,
  className = '',
}: DetectionBadgeProps) {
  const displayText = classification.charAt(0).toUpperCase() + classification.slice(1);
  const tooltip = tooltipText || defaultTooltips[classification];

  return (
    <span
      role="status"
      className={`inline-flex items-center rounded-full font-medium ${badgeStyles[classification]} ${sizeStyles[size]} ${className}`}
      title={showTooltip ? tooltip : undefined}
      aria-label={`Classification: ${displayText}`}
    >
      {displayText}
    </span>
  );
}

export default DetectionBadge;
