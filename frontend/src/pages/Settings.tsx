/**
 * Settings page - user profile and notification preferences
 *
 * Reference: US3 (Notification settings), T106
 */

import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { User, NotificationPreference } from '../api/client';

export const Settings: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchUserProfile();
    fetchPreferences();
  }, []);

  const fetchUserProfile = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const userData = await apiClient.getCurrentUser();
      setUser(userData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load user profile');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPreferences = async () => {
    try {
      const prefs = await apiClient.listNotificationPreferences();
      setPreferences(prefs);
    } catch (err) {
      console.error('Failed to fetch notification preferences:', err);
    }
  };

  const handleTogglePreference = async (id: string, enabled: boolean) => {
    try {
      await apiClient.updateNotificationPreference(id, { enabled });
      await fetchPreferences();
      setSuccessMessage('Notification preference updated successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      alert(`Failed to update preference: ${err}`);
    }
  };

  const handleDeletePreference = async (id: string) => {
    if (!confirm('Are you sure you want to delete this notification preference?')) {
      return;
    }

    try {
      await apiClient.deleteNotificationPreference(id);
      await fetchPreferences();
      setSuccessMessage('Notification preference deleted successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      alert(`Failed to delete preference: ${err}`);
    }
  };

  const handleCreatePreference = async () => {
    // Simple form - in production would use a modal with full form
    const channel = prompt('Enter channel (email, slack, webhook, pagerduty):');
    if (!channel || !['email', 'slack', 'webhook', 'pagerduty'].includes(channel)) {
      alert('Invalid channel');
      return;
    }

    try {
      await apiClient.createNotificationPreference({
        channel,
        enabled: true,
        min_severity: 'medium',
        notify_on_authorized: false,
        notify_on_suspect: true,
        notify_on_unauthorized: true,
        max_notifications_per_hour: 10,
      });
      await fetchPreferences();
      setSuccessMessage('Notification preference created successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      alert(`Failed to create preference: ${err}`);
    }
  };

  const getChannelIcon = (channel: string) => {
    const icons = {
      email: '📧',
      slack: '💬',
      webhook: '🔗',
      pagerduty: '🚨',
    };
    return icons[channel as keyof typeof icons] || '📢';
  };

  const getSeverityColor = (severity: string) => {
    const colors = {
      low: 'text-blue-700 bg-blue-50',
      medium: 'text-yellow-700 bg-yellow-50',
      high: 'text-orange-700 bg-orange-50',
      critical: 'text-red-700 bg-red-50',
    };
    return colors[severity as keyof typeof colors] || 'text-gray-700 bg-gray-50';
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
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Settings</h3>
          <p className="text-red-800">{error}</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Settings</h1>
        <p className="text-gray-600">Manage your profile and notification preferences</p>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-800">{successMessage}</p>
        </div>
      )}

      {/* User Profile */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Profile</h2>
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium text-gray-500">Email</p>
            <p className="text-lg text-gray-900">{user.email}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Role</p>
            <span className="inline-block px-3 py-1 bg-blue-100 text-blue-700 text-sm font-semibold rounded capitalize">
              {user.role}
            </span>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Account Created</p>
            <p className="text-sm text-gray-700">
              {new Date(user.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          {user.last_login_at && (
            <div>
              <p className="text-sm font-medium text-gray-500">Last Login</p>
              <p className="text-sm text-gray-700">
                {new Date(user.last_login_at).toLocaleString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Notification Preferences */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Notification Preferences</h2>
            <p className="text-sm text-gray-600 mt-1">
              Configure how you receive alerts for MCP detections
            </p>
          </div>
          <button
            onClick={handleCreatePreference}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            + Add Preference
          </button>
        </div>

        {preferences.length === 0 ? (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
            <p className="text-gray-600">No notification preferences configured.</p>
            <p className="text-sm text-gray-500 mt-2">
              Click "Add Preference" to create your first notification rule.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {preferences.map((pref) => (
              <div
                key={pref.id}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <span className="text-2xl">{getChannelIcon(pref.channel)}</span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-gray-900 capitalize">{pref.channel}</h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded ${getSeverityColor(pref.min_severity)}`}>
                          Min: {pref.min_severity}
                        </span>
                        {!pref.enabled && (
                          <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-600">
                            Disabled
                          </span>
                        )}
                      </div>

                      <div className="text-sm text-gray-600 space-y-1">
                        {pref.email_address && (
                          <p>Email: <span className="font-medium">{pref.email_address}</span></p>
                        )}
                        <p>
                          Notify on:
                          {pref.notify_on_unauthorized && ' Unauthorized'}
                          {pref.notify_on_suspect && ' Suspect'}
                          {pref.notify_on_authorized && ' Authorized'}
                        </p>
                        <p>Rate limit: {pref.max_notifications_per_hour}/hour</p>
                        {pref.digest_enabled && pref.digest_frequency_minutes && (
                          <p>Digest: Every {pref.digest_frequency_minutes} minutes</p>
                        )}
                        {pref.quiet_hours_start && pref.quiet_hours_end && (
                          <p>
                            Quiet hours: {pref.quiet_hours_start} - {pref.quiet_hours_end}
                            {pref.quiet_hours_timezone && ` (${pref.quiet_hours_timezone})`}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => handleTogglePreference(pref.id, !pref.enabled)}
                      className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                        pref.enabled
                          ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                          : 'bg-green-100 text-green-700 hover:bg-green-200'
                      }`}
                    >
                      {pref.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => handleDeletePreference(pref.id)}
                      className="px-3 py-1 text-sm font-medium bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">About Notifications</h3>
        <p className="text-sm text-blue-800">
          Notification preferences control how and when you receive alerts about MCP detections.
          You can configure multiple channels (email, Slack, webhooks, PagerDuty) with different
          severity thresholds and rate limits. Quiet hours and digest modes help reduce notification
          fatigue during off-hours.
        </p>
      </div>
    </div>
  );
};

export default Settings;
