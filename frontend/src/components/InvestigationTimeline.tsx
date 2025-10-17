/**
 * Investigation timeline component
 *
 * Reference: US2 (Investigation tracking)
 */

import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';

interface TimelineEntry {
  type: 'feedback' | 'note';
  timestamp: string;
  data: any;
}

interface TimelineSummary {
  total_feedback: number;
  open_investigations: number;
  resolved_investigations: number;
}

interface InvestigationTimelineProps {
  detectionId: string;
}

export const InvestigationTimeline: React.FC<InvestigationTimelineProps> = ({ detectionId }) => {
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [summary, setSummary] = useState<TimelineSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTimeline();
  }, [detectionId]);

  const fetchTimeline = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/v1/feedback/detection/${detectionId}/timeline`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch timeline');
      }

      const data = await response.json();
      setTimeline(data.timeline || []);
      setSummary(data.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timeline');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getFeedbackTypeColor = (type: string) => {
    const colors = {
      false_positive: 'bg-green-100 text-green-800',
      true_positive: 'bg-red-100 text-red-800',
      investigation_needed: 'bg-yellow-100 text-yellow-800',
      escalation_required: 'bg-orange-100 text-orange-800',
      resolved: 'bg-blue-100 text-blue-800',
    };
    return colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const renderFeedbackEntry = (entry: TimelineEntry) => {
    const feedback = entry.data;

    return (
      <div className="relative pl-8 pb-8">
        {/* Timeline dot */}
        <div className="absolute left-0 top-1 w-4 h-4 bg-blue-500 rounded-full border-4 border-white"></div>

        {/* Content */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <div className="flex items-start justify-between mb-2">
            <div>
              <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${getFeedbackTypeColor(feedback.feedback_type)}`}>
                {feedback.feedback_type.replace(/_/g, ' ').toUpperCase()}
              </span>
              {feedback.severity && (
                <span className="ml-2 text-xs text-gray-600">
                  Severity: <span className="font-medium capitalize">{feedback.severity}</span>
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500">{formatTimestamp(entry.timestamp)}</span>
          </div>

          <p className="text-sm text-gray-600 mb-2">
            By: <span className="font-medium text-gray-900">{feedback.analyst_email}</span>
          </p>

          <div className="bg-gray-50 rounded p-3 mb-2">
            <p className="text-sm text-gray-900 whitespace-pre-wrap">{feedback.notes}</p>
          </div>

          {feedback.recommended_action && (
            <div className="bg-blue-50 border-l-4 border-blue-400 p-3 mt-2">
              <p className="text-xs font-medium text-blue-900 mb-1">Recommended Action:</p>
              <p className="text-sm text-blue-800">{feedback.recommended_action}</p>
            </div>
          )}

          {feedback.tags && feedback.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {feedback.tags.map((tag: string) => (
                <span key={tag} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {feedback.investigation_status && (
            <div className="mt-2 pt-2 border-t border-gray-200">
              <p className="text-xs text-gray-600">
                Status: <span className="font-medium capitalize">{feedback.investigation_status}</span>
                {feedback.resolved_at && (
                  <span className="ml-2">
                    (Resolved: {formatTimestamp(feedback.resolved_at)})
                  </span>
                )}
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderNoteEntry = (entry: TimelineEntry) => {
    const note = entry.data;

    return (
      <div className="relative pl-8 pb-8">
        {/* Timeline dot */}
        <div className="absolute left-0 top-1 w-3 h-3 bg-gray-400 rounded-full border-4 border-white"></div>

        {/* Content */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <div className="flex items-start justify-between mb-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-700 capitalize">{note.note_type}</span>
              {note.is_internal && (
                <span className="px-1.5 py-0.5 bg-red-100 text-red-700 text-xs rounded">
                  Internal
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500">{formatTimestamp(entry.timestamp)}</span>
          </div>
          <p className="text-xs text-gray-600 mb-2">
            By: <span className="font-medium">{note.author_email}</span>
          </p>
          <p className="text-sm text-gray-900">{note.note_text}</p>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800 text-sm">{error}</p>
      </div>
    );
  }

  if (timeline.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
        <p className="text-gray-600">No investigation history for this detection yet.</p>
        <p className="text-sm text-gray-500 mt-2">
          Be the first to provide feedback!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      {summary && (
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-3">Investigation Summary</h4>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-2xl font-bold text-gray-900">{summary.total_feedback}</p>
              <p className="text-xs text-gray-600">Total Feedback</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-yellow-600">{summary.open_investigations}</p>
              <p className="text-xs text-gray-600">Open</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{summary.resolved_investigations}</p>
              <p className="text-xs text-gray-600">Resolved</p>
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-4">Timeline</h4>
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-gray-200"></div>

          {/* Timeline entries */}
          {timeline.map((entry, index) => (
            <div key={index}>
              {entry.type === 'feedback' ? renderFeedbackEntry(entry) : renderNoteEntry(entry)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default InvestigationTimeline;
