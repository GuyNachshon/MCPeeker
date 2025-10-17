/**
 * Explanation panel component - displays Judge's plain-language reasoning
 *
 * Reference: US5 (Transparency), T089
 */

import React from 'react';
import type { Detection, Evidence } from '../api/client';

interface ExplanationPanelProps {
  detection: Detection;
}

export const ExplanationPanel: React.FC<ExplanationPanelProps> = ({ detection }) => {
  // Find gateway/judge evidence
  const judgeEvidence = detection.evidence.find(ev => ev.type === 'gateway');

  if (!judgeEvidence) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Analysis</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
          <p className="text-gray-600">No AI analysis available for this detection.</p>
          <p className="text-sm text-gray-500 mt-2">
            This detection was classified using only endpoint and network evidence.
          </p>
        </div>
      </div>
    );
  }

  // Extract reasoning from snippet if available
  const reasoning = judgeEvidence.snippet || "Classification performed without detailed explanation.";

  // Parse classification from source or snippet
  const getClassificationFromEvidence = (): string => {
    if (judgeEvidence.source.includes('UNAUTHORIZED')) return 'UNAUTHORIZED';
    if (judgeEvidence.source.includes('AUTHORIZED')) return 'AUTHORIZED';
    if (judgeEvidence.source.includes('SUSPECT')) return 'SUSPECT';
    return 'UNKNOWN';
  };

  const classification = getClassificationFromEvidence();

  const getClassificationColor = (cls: string) => {
    if (cls === 'AUTHORIZED') return 'text-green-700 bg-green-50 border-green-200';
    if (cls === 'SUSPECT') return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    if (cls === 'UNAUTHORIZED') return 'text-red-700 bg-red-50 border-red-200';
    return 'text-gray-700 bg-gray-50 border-gray-200';
  };

  const getClassificationIcon = (cls: string) => {
    if (cls === 'AUTHORIZED') return '✅';
    if (cls === 'SUSPECT') return '⚠️';
    if (cls === 'UNAUTHORIZED') return '🚫';
    return '❓';
  };

  // Extract confidence if available (looking for patterns like "Confidence: 85")
  const confidenceMatch = reasoning.match(/confidence[:\s]+(\d+)/i);
  const confidence = confidenceMatch ? parseInt(confidenceMatch[1]) : null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">AI Analysis</h3>
          <p className="text-sm text-gray-600 mt-1">
            Classification by Judge Service (Claude 3.5 Sonnet)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{getClassificationIcon(classification)}</span>
          <span className={`px-3 py-1 text-sm font-semibold rounded-lg border ${getClassificationColor(classification)}`}>
            {classification}
          </span>
        </div>
      </div>

      {/* Confidence */}
      {confidence !== null && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-700">Confidence</p>
            <p className="text-sm font-semibold text-gray-900">{confidence}%</p>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${
                confidence >= 80 ? 'bg-green-600' : confidence >= 50 ? 'bg-yellow-600' : 'bg-red-600'
              }`}
              style={{ width: `${confidence}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Reasoning */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <div className="text-blue-600 mt-1">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-blue-900 mb-2">Explanation</p>
            <p className="text-sm text-blue-800 leading-relaxed whitespace-pre-wrap">
              {reasoning}
            </p>
          </div>
        </div>
      </div>

      {/* Score Contribution */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center">
          <p className="text-sm font-medium text-gray-700">Score Contribution</p>
          <p className="text-lg font-bold text-indigo-600">
            +{judgeEvidence.score_contribution} points
          </p>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Judge classifications contribute medium weight to the total detection score.
        </p>
      </div>

      {/* Info Footer */}
      <div className="mt-4 bg-gray-50 border border-gray-200 rounded p-3">
        <p className="text-xs text-gray-600">
          <strong>About AI Analysis:</strong> The Judge service uses Claude 3.5 Sonnet to analyze detection context
          and provide plain-language explanations. This helps build trust and transparency in the detection process.
          The AI considers patterns, typical usage, and security implications when making classifications.
        </p>
      </div>
    </div>
  );
};

export default ExplanationPanel;
