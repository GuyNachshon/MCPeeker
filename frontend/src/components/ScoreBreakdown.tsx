/**
 * Score breakdown component - shows evidence contribution to total score
 *
 * Reference: US5 (Transparency), T088
 */

import React from 'react';
import type { Detection, Evidence } from '../api/client';

interface ScoreBreakdownProps {
  detection: Detection;
}

interface ScoreContribution {
  source: string;
  type: 'endpoint' | 'network' | 'gateway' | 'registry';
  points: number;
  color: string;
  icon: string;
  description: string;
}

export const ScoreBreakdown: React.FC<ScoreBreakdownProps> = ({ detection }) => {
  // Calculate contributions from evidence
  const contributions: ScoreContribution[] = [];

  // Group evidence by type
  const evidenceByType = detection.evidence.reduce((acc, ev) => {
    if (!acc[ev.type]) acc[ev.type] = [];
    acc[ev.type].push(ev);
    return acc;
  }, {} as Record<string, Evidence[]>);

  // Endpoint evidence (file + process)
  if (evidenceByType.endpoint) {
    const total = evidenceByType.endpoint.reduce((sum, ev) => sum + ev.score_contribution, 0);
    contributions.push({
      source: 'Endpoint Detection',
      type: 'endpoint',
      points: total,
      color: 'bg-purple-100 border-purple-300 text-purple-800',
      icon: '💻',
      description: `File or process detection on host (${evidenceByType.endpoint.length} evidence items)`
    });
  }

  // Network evidence
  if (evidenceByType.network) {
    const total = evidenceByType.network.reduce((sum, ev) => sum + ev.score_contribution, 0);
    contributions.push({
      source: 'Network Detection',
      type: 'network',
      points: total,
      color: 'bg-blue-100 border-blue-300 text-blue-800',
      icon: '🌐',
      description: `Network traffic patterns detected (${evidenceByType.network.length} evidence items)`
    });
  }

  // Gateway/Judge evidence
  if (evidenceByType.gateway) {
    const total = evidenceByType.gateway.reduce((sum, ev) => sum + ev.score_contribution, 0);
    contributions.push({
      source: 'LLM Classification',
      type: 'gateway',
      points: total,
      color: 'bg-indigo-100 border-indigo-300 text-indigo-800',
      icon: '🤖',
      description: `AI analysis of detection context (${evidenceByType.gateway.length} classification)`
    });
  }

  // Registry penalty (if matched)
  if (detection.registry_matched) {
    contributions.push({
      source: 'Registry Match',
      type: 'registry',
      points: -6,
      color: 'bg-green-100 border-green-300 text-green-800',
      icon: '✅',
      description: 'MCP is registered and approved in registry'
    });
  }

  const totalScore = contributions.reduce((sum, c) => sum + c.points, 0);

  const getClassificationColor = () => {
    if (totalScore <= 4) return 'text-green-700';
    if (totalScore <= 8) return 'text-yellow-700';
    return 'text-red-700';
  };

  const getClassificationLabel = () => {
    if (totalScore <= 4) return 'Authorized';
    if (totalScore <= 8) return 'Suspect';
    return 'Unauthorized';
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Score Breakdown</h3>
        <div className="text-right">
          <p className="text-sm text-gray-600">Total Score</p>
          <p className={`text-3xl font-bold ${getClassificationColor()}`}>
            {totalScore}
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Classification: <span className={`font-semibold ${getClassificationColor()}`}>
              {getClassificationLabel()}
            </span>
          </p>
        </div>
      </div>

      {/* Classification Guide */}
      <div className="bg-gray-50 border border-gray-200 rounded p-3 mb-4">
        <p className="text-xs font-medium text-gray-700 mb-2">Classification Thresholds:</p>
        <div className="flex gap-4 text-xs">
          <span className="text-green-700">
            <strong>Authorized:</strong> ≤ 4 points
          </span>
          <span className="text-yellow-700">
            <strong>Suspect:</strong> 5-8 points
          </span>
          <span className="text-red-700">
            <strong>Unauthorized:</strong> ≥ 9 points
          </span>
        </div>
      </div>

      {/* Contributions */}
      <div className="space-y-3">
        {contributions.map((contrib, index) => (
          <div
            key={index}
            className={`border rounded-lg p-4 ${contrib.color}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <span className="text-2xl">{contrib.icon}</span>
                <div className="flex-1">
                  <h4 className="font-semibold text-sm mb-1">{contrib.source}</h4>
                  <p className="text-xs opacity-90">{contrib.description}</p>
                </div>
              </div>
              <div className="text-right ml-4">
                <p className={`text-2xl font-bold ${contrib.points > 0 ? '' : 'text-green-700'}`}>
                  {contrib.points > 0 ? '+' : ''}{contrib.points}
                </p>
                <p className="text-xs opacity-75">points</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Calculation Summary */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center">
          <p className="text-sm font-medium text-gray-700">Calculation:</p>
          <p className="text-sm text-gray-600 font-mono">
            {contributions.map(c => `${c.points > 0 ? '+' : ''}${c.points}`).join(' ')} = {totalScore}
          </p>
        </div>
      </div>

      {/* Judge Unavailable Warning */}
      {!detection.judge_available && (
        <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-yellow-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-yellow-900">Judge Service Unavailable</p>
              <p className="text-xs text-yellow-800 mt-1">
                LLM classification was not available when this detection was scored. The score may be re-calculated when the Judge service recovers.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScoreBreakdown;
