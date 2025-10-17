/**
 * Detection detail view component
 *
 * Reference: US1 (Detection viewing), US2 (Investigation)
 */

import React, { useState } from 'react';
import type { Detection, Evidence } from '../api/client';
import InvestigationPanel from './InvestigationPanel';
import ScoreBreakdown from './ScoreBreakdown';
import ExplanationPanel from './ExplanationPanel';
import HelpTooltip from './HelpTooltip';

interface DetectionDetailProps {
  detection: Detection;
  onClose?: () => void;
  onRegister?: (detection: Detection) => void;
  showInvestigation?: boolean;
}

export const DetectionDetail: React.FC<DetectionDetailProps> = ({
  detection,
  onClose,
  onRegister,
  showInvestigation = true,
}) => {
  const [activeTab, setActiveTab] = useState<'details' | 'investigation'>('details');
  const getClassificationColor = (classification: string) => {
    const colors = {
      authorized: 'text-green-700 bg-green-50 border-green-200',
      suspect: 'text-yellow-700 bg-yellow-50 border-yellow-200',
      unauthorized: 'text-red-700 bg-red-50 border-red-200',
    };
    return colors[classification as keyof typeof colors] || 'text-gray-700 bg-gray-50 border-gray-200';
  };

  const getEvidenceTypeIcon = (type: string) => {
    const icons = {
      endpoint: '💻',
      network: '🌐',
      gateway: '🚪',
    };
    return icons[type as keyof typeof icons] || '📄';
  };

  const getScoreColor = (score: number) => {
    if (score <= 4) return 'text-green-600';
    if (score <= 8) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const renderEvidence = (evidence: Evidence, index: number) => {
    return (
      <div
        key={index}
        className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
      >
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{getEvidenceTypeIcon(evidence.type)}</span>
            <div>
              <h4 className="font-semibold text-gray-900 capitalize">{evidence.type} Evidence</h4>
              <p className="text-sm text-gray-600">{evidence.source}</p>
            </div>
          </div>
          <span className="px-2 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded">
            +{evidence.score_contribution} points
          </span>
        </div>

        {evidence.file_path && (
          <div className="mt-2">
            <span className="text-xs font-medium text-gray-500">File Path:</span>
            <p className="text-sm font-mono text-gray-900 mt-1 break-all">{evidence.file_path}</p>
          </div>
        )}

        {evidence.process_name && (
          <div className="mt-2">
            <span className="text-xs font-medium text-gray-500">Process:</span>
            <p className="text-sm font-mono text-gray-900 mt-1">{evidence.process_name}</p>
          </div>
        )}

        {evidence.snippet && (
          <div className="mt-2">
            <span className="text-xs font-medium text-gray-500">Snippet (≤1KB):</span>
            <pre className="mt-1 p-2 bg-gray-50 rounded text-xs font-mono overflow-x-auto border border-gray-200">
              {evidence.snippet}
            </pre>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      {showInvestigation && (
        <div className="border-b border-gray-200">
          <nav className="flex gap-4">
            <button
              onClick={() => setActiveTab('details')}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'details'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              Detection Details
            </button>
            <button
              onClick={() => setActiveTab('investigation')}
              className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'investigation'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              Investigation
            </button>
          </nav>
        </div>
      )}

      {activeTab === 'details' && (
        <>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Detection Details</h2>
          <p className="text-sm text-gray-600 mt-1">Event ID: {detection.event_id}</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Summary Card */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Timestamp</p>
            <p className="text-sm font-medium text-gray-900 mt-1">{formatTimestamp(detection.timestamp)}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Score <HelpTooltip topic="scoring" />
            </p>
            <p className={`text-2xl font-bold mt-1 ${getScoreColor(detection.score)}`}>
              {detection.score}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Classification <HelpTooltip topic="classification" />
            </p>
            <span className={`inline-block px-3 py-1 text-sm font-semibold rounded-lg mt-1 border ${getClassificationColor(detection.classification)}`}>
              {detection.classification.toUpperCase()}
            </span>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Registry Match <HelpTooltip topic="registry" />
            </p>
            <p className="text-sm font-medium mt-1">
              {detection.registry_matched ? (
                <span className="text-green-600">✓ Matched</span>
              ) : (
                <span className="text-gray-500">Not matched</span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Score Breakdown */}
      <ScoreBreakdown detection={detection} />

      {/* AI Explanation (if available) */}
      {detection.evidence.some(ev => ev.type === 'gateway') && (
        <ExplanationPanel detection={detection} />
      )}

      {/* Identifiers */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Identifiers</h3>
        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium text-gray-500">Host ID (Hashed)</p>
            <p className="text-sm font-mono text-gray-900 mt-1 break-all">{detection.host_id}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500">Composite ID</p>
            <p className="text-sm font-mono text-gray-900 mt-1 break-all">{detection.composite_id}</p>
          </div>
        </div>
      </div>

      {/* Evidence */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Evidence ({detection.evidence.length})
          </h3>
          <span className="text-sm text-gray-600">
            Total score: {detection.evidence.reduce((sum, e) => sum + e.score_contribution, 0)} points
          </span>
        </div>
        <div className="space-y-3">
          {detection.evidence.map((evidence, index) => renderEvidence(evidence, index))}
        </div>
      </div>

      {/* Judge Status */}
      {detection.judge_available && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-blue-900">Judge Service Available</p>
              <p className="text-xs text-blue-700 mt-1">
                This detection can be analyzed by the Judge service for additional context.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      {!detection.registry_matched && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Actions</h3>
          <div className="flex gap-3">
            <button
              onClick={() => onRegister?.(detection)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Register MCP
            </button>
            <button
              onClick={() => setActiveTab('investigation')}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
            >
              Provide Feedback
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Register this MCP in the registry to prevent future alerts.
          </p>
        </div>
      )}
        </>
      )}

      {/* Investigation Tab */}
      {activeTab === 'investigation' && showInvestigation && (
        <InvestigationPanel detection={detection} />
      )}
    </div>
  );
};

export default DetectionDetail;
