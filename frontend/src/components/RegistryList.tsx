/**
 * Registry list component - displays registry entries with filtering
 *
 * Reference: US3 (Admin management), T102
 */

import React, { useState } from 'react';
import type { RegistryEntry } from '../api/client';
import ExpirationBadge from './ExpirationBadge';
import ApprovalButtons from './ApprovalButtons';

interface RegistryListProps {
  entries: RegistryEntry[];
  onApprove?: (id: string) => Promise<void>;
  onReject?: (id: string, reason: string) => Promise<void>;
  onRevoke?: (id: string, reason: string) => Promise<void>;
  onUpdate?: (id: string) => void;
  currentUserRole?: 'developer' | 'analyst' | 'admin';
}

export const RegistryList: React.FC<RegistryListProps> = ({
  entries,
  onApprove,
  onReject,
  onRevoke,
  onUpdate,
  currentUserRole = 'developer',
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Filter entries
  const filteredEntries = entries.filter(entry => {
    // Status filter
    if (statusFilter !== 'all' && entry.status !== statusFilter) {
      return false;
    }

    // Search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      return (
        entry.name.toLowerCase().includes(search) ||
        entry.description?.toLowerCase().includes(search) ||
        entry.owner_email.toLowerCase().includes(search) ||
        entry.tags?.some(tag => tag.toLowerCase().includes(search))
      );
    }

    return true;
  });

  const getStatusColor = (status: string) => {
    const colors = {
      pending: 'text-yellow-700 bg-yellow-50 border-yellow-200',
      approved: 'text-green-700 bg-green-50 border-green-200',
      rejected: 'text-red-700 bg-red-50 border-red-200',
      revoked: 'text-gray-700 bg-gray-50 border-gray-200',
    };
    return colors[status as keyof typeof colors] || 'text-gray-700 bg-gray-50 border-gray-200';
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (entries.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
        <p className="text-gray-600">No registry entries found.</p>
        <p className="text-sm text-gray-500 mt-2">
          Create your first MCP registration to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex gap-4">
          {/* Search */}
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search by name, description, owner, or tags..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="revoked">Revoked</option>
          </select>
        </div>

        <div className="mt-2 text-sm text-gray-600">
          Showing {filteredEntries.length} of {entries.length} entries
        </div>
      </div>

      {/* Entries List */}
      <div className="space-y-3">
        {filteredEntries.map((entry) => (
          <div
            key={entry.id}
            className="bg-white border border-gray-200 rounded-lg p-6 hover:border-blue-300 transition-colors"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900">{entry.name}</h3>
                  <span className={`px-3 py-1 text-xs font-semibold rounded-lg border ${getStatusColor(entry.status)}`}>
                    {entry.status.toUpperCase()}
                  </span>
                  {entry.expires_at && <ExpirationBadge expiresAt={entry.expires_at} />}
                </div>
                {entry.description && (
                  <p className="text-sm text-gray-600 mb-2">{entry.description}</p>
                )}
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>Owner: <span className="font-medium">{entry.owner_email}</span></span>
                  {entry.version && <span>Version: {entry.version}</span>}
                  <span>Created: {formatDate(entry.created_at)}</span>
                </div>
              </div>

              {/* Actions */}
              {currentUserRole === 'admin' && entry.status === 'pending' && onApprove && onReject && (
                <ApprovalButtons
                  entryId={entry.id}
                  entryName={entry.name}
                  onApprove={onApprove}
                  onReject={onReject}
                />
              )}

              {currentUserRole === 'admin' && entry.status === 'approved' && onRevoke && (
                <button
                  onClick={() => {
                    const reason = prompt('Enter revocation reason:');
                    if (reason) {
                      onRevoke(entry.id, reason);
                    }
                  }}
                  className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors text-sm font-medium"
                >
                  Revoke
                </button>
              )}
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              {entry.composite_id && (
                <div>
                  <p className="text-xs font-medium text-gray-500">Composite ID</p>
                  <p className="text-xs font-mono text-gray-900 truncate">{entry.composite_id}</p>
                </div>
              )}
              {entry.port && (
                <div>
                  <p className="text-xs font-medium text-gray-500">Port</p>
                  <p className="text-xs text-gray-900">{entry.port}</p>
                </div>
              )}
              {entry.manifest_hash && (
                <div>
                  <p className="text-xs font-medium text-gray-500">Manifest Hash</p>
                  <p className="text-xs font-mono text-gray-900 truncate">{entry.manifest_hash}</p>
                </div>
              )}
              {entry.expires_at && (
                <div>
                  <p className="text-xs font-medium text-gray-500">Expires</p>
                  <p className="text-xs text-gray-900">{formatDate(entry.expires_at)}</p>
                </div>
              )}
            </div>

            {/* Business Justification */}
            <div className="bg-gray-50 border border-gray-200 rounded p-3 mb-3">
              <p className="text-xs font-medium text-gray-700 mb-1">Business Justification</p>
              <p className="text-sm text-gray-900">{entry.business_justification}</p>
            </div>

            {/* Tags */}
            {entry.tags && entry.tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {entry.tags.map((tag) => (
                  <span key={tag} className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Approval Info */}
            {entry.approved_by && entry.approved_at && (
              <div className="text-xs text-gray-500 pt-3 border-t border-gray-200">
                Approved by <span className="font-medium">{entry.approved_by}</span> on{' '}
                {formatDate(entry.approved_at)}
              </div>
            )}

            {/* Rejection Info */}
            {entry.rejection_reason && (
              <div className="bg-red-50 border border-red-200 rounded p-3 text-xs">
                <p className="font-medium text-red-900 mb-1">Rejection Reason:</p>
                <p className="text-red-800">{entry.rejection_reason}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredEntries.length === 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600">No entries match your filters.</p>
        </div>
      )}
    </div>
  );
};

export default RegistryList;
