/**
 * Registry page - list and manage registry entries
 *
 * Reference: US3 (Admin management), T105
 */

import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { RegistryEntry } from '../api/client';
import RegistryList from '../components/RegistryList';

export const Registry: React.FC = () => {
  const [entries, setEntries] = useState<RegistryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentUserRole, setCurrentUserRole] = useState<'developer' | 'analyst' | 'admin'>('developer');

  useEffect(() => {
    fetchEntries();
    fetchCurrentUser();
  }, []);

  const fetchEntries = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiClient.listRegistryEntries();
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load registry entries');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCurrentUser = async () => {
    try {
      const user = await apiClient.getCurrentUser();
      setCurrentUserRole(user.role);
    } catch (err) {
      console.error('Failed to fetch current user:', err);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await apiClient.approveRegistryEntry(id);
      await fetchEntries(); // Refresh list
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to approve entry');
    }
  };

  const handleReject = async (id: string, reason: string) => {
    try {
      await apiClient.rejectRegistryEntry(id, reason);
      await fetchEntries(); // Refresh list
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to reject entry');
    }
  };

  const handleRevoke = async (id: string, reason: string) => {
    try {
      await apiClient.revokeRegistryEntry(id, reason);
      await fetchEntries(); // Refresh list
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to revoke entry');
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Registry</h3>
          <p className="text-red-800">{error}</p>
          <button
            onClick={fetchEntries}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">MCP Registry</h1>
        <p className="text-gray-600">
          {currentUserRole === 'admin'
            ? 'Manage and approve MCP registrations across your organization'
            : currentUserRole === 'analyst'
            ? 'View registered MCPs across your organization'
            : 'View and manage your MCP registrations'}
        </p>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">Total Entries</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{entries.length}</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">Pending</p>
          <p className="text-3xl font-bold text-yellow-600 mt-2">
            {entries.filter(e => e.status === 'pending').length}
          </p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">Approved</p>
          <p className="text-3xl font-bold text-green-600 mt-2">
            {entries.filter(e => e.status === 'approved').length}
          </p>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">Expiring Soon</p>
          <p className="text-3xl font-bold text-orange-600 mt-2">
            {entries.filter(e => {
              if (!e.expires_at) return false;
              const daysUntil = Math.ceil(
                (new Date(e.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
              );
              return daysUntil > 0 && daysUntil <= 14;
            }).length}
          </p>
        </div>
      </div>

      {/* Registry List */}
      <RegistryList
        entries={entries}
        onApprove={handleApprove}
        onReject={handleReject}
        onRevoke={handleRevoke}
        currentUserRole={currentUserRole}
      />
    </div>
  );
};

export default Registry;
