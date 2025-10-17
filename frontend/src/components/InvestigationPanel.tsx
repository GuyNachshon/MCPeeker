/**
 * Investigation panel component
 *
 * Reference: US2 (SOC Analyst Investigation)
 */

import React, { useState } from 'react';
import type { Detection } from '../api/client';
import FeedbackForm, { FeedbackData } from './FeedbackForm';
import InvestigationTimeline from './InvestigationTimeline';

interface InvestigationPanelProps {
  detection: Detection;
}

type ViewMode = 'timeline' | 'submit_feedback';

export const InvestigationPanel: React.FC<InvestigationPanelProps> = ({ detection }) => {
  const [viewMode, setViewMode] = useState<ViewMode>('timeline');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSubmitFeedback = async (feedbackData: FeedbackData) => {
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL}/api/v1/feedback`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify(feedbackData),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to submit feedback');
    }

    // Switch back to timeline and refresh
    setViewMode('timeline');
    setRefreshKey((prev) => prev + 1); // Force timeline refresh
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Investigation</h3>
            <p className="text-sm text-gray-600 mt-1">
              Track analysis progress and collaborate with your team
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('timeline')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                viewMode === 'timeline'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              Timeline
            </button>
            <button
              onClick={() => setViewMode('submit_feedback')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                viewMode === 'submit_feedback'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              + Add Feedback
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        {viewMode === 'timeline' ? (
          <InvestigationTimeline key={refreshKey} detectionId={detection.event_id} />
        ) : (
          <FeedbackForm
            detection={detection}
            onSubmit={handleSubmitFeedback}
            onCancel={() => setViewMode('timeline')}
          />
        )}
      </div>
    </div>
  );
};

export default InvestigationPanel;
