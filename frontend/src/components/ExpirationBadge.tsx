/**
 * Expiration reminder badge - highlights entries expiring soon
 *
 * Reference: US3 (Expiration monitoring), T104
 */

import React from 'react';

interface ExpirationBadgeProps {
  expiresAt: string;
  className?: string;
}

export const ExpirationBadge: React.FC<ExpirationBadgeProps> = ({ expiresAt, className = '' }) => {
  const expirationDate = new Date(expiresAt);
  const now = new Date();
  const daysUntilExpiration = Math.ceil((expirationDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  // Don't show badge if already expired or more than 14 days away
  if (daysUntilExpiration < 0 || daysUntilExpiration > 14) {
    return null;
  }

  // Determine badge color and icon based on days remaining
  const getBadgeStyle = () => {
    if (daysUntilExpiration <= 1) {
      return {
        color: 'text-red-700 bg-red-50 border-red-300',
        icon: '🚨',
        label: `Expires ${daysUntilExpiration === 0 ? 'today' : 'tomorrow'}!`,
      };
    } else if (daysUntilExpiration <= 3) {
      return {
        color: 'text-orange-700 bg-orange-50 border-orange-300',
        icon: '⚠️',
        label: `Expires in ${daysUntilExpiration} days`,
      };
    } else if (daysUntilExpiration <= 7) {
      return {
        color: 'text-yellow-700 bg-yellow-50 border-yellow-300',
        icon: '⏰',
        label: `Expires in ${daysUntilExpiration} days`,
      };
    } else {
      return {
        color: 'text-blue-700 bg-blue-50 border-blue-300',
        icon: '📅',
        label: `Expires in ${daysUntilExpiration} days`,
      };
    }
  };

  const style = getBadgeStyle();

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded border ${style.color} ${className}`}
      title={`Expires on ${expirationDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}`}
    >
      <span>{style.icon}</span>
      <span>{style.label}</span>
    </span>
  );
};

export default ExpirationBadge;
