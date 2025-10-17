/**
 * Help tooltip component - explains scoring and classification in plain language
 *
 * Reference: US5 (Transparency), T090
 */

import React, { useState } from 'react';

interface HelpTooltipProps {
  topic: 'scoring' | 'classification' | 'evidence' | 'registry' | 'investigation';
  className?: string;
}

const helpContent = {
  scoring: {
    title: 'How Scoring Works',
    content: `
Detection scores are calculated by adding up points from different types of evidence:

• Endpoint Evidence: +11 points
  File or process detection on your machine

• LLM Classification: +5 points
  AI analysis of the detection context

• Network Evidence: +3 points
  Network traffic patterns detected

• Registry Match: -6 points
  MCP is registered and approved

The final score determines the classification:
• Authorized (≤4): Safe to use
• Suspect (5-8): Needs review
• Unauthorized (≥9): High risk
    `.trim()
  },
  classification: {
    title: 'Classification Levels',
    content: `
MCPeeker uses three classification levels:

🟢 Authorized (Score ≤ 4)
MCPs that are registered and approved, or have very low-risk indicators. These are safe to use.

🟡 Suspect (Score 5-8)
MCPs that have some risk indicators but may be legitimate. These should be reviewed and registered if valid.

🔴 Unauthorized (Score ≥ 9)
MCPs with high-risk indicators or multiple evidence sources. These require immediate investigation and should not be used until cleared.
    `.trim()
  },
  evidence: {
    title: 'Evidence Types',
    content: `
MCPeeker collects evidence from multiple sources:

💻 Endpoint Evidence
Files (manifest.json) and processes detected on your machine. This is the primary detection method.

🌐 Network Evidence
Traffic patterns detected by network monitoring tools (Zeek/Suricata). Provides supporting evidence.

🤖 LLM Classification
AI analysis using Claude that examines the context and provides plain-language explanations.

✅ Registry Status
Whether the MCP is registered and approved in the organization's registry.
    `.trim()
  },
  registry: {
    title: 'Registry System',
    content: `
The registry is your organization's approved list of MCPs:

1. Register Your MCP
   If you're running a legitimate MCP, register it through the UI by providing:
   - Purpose and business justification
   - Team/owner information
   - Expected lifetime (TTL)

2. Approval Process
   Platform engineers review and approve registrations. Once approved, future detections of your MCP will be classified as "Authorized".

3. Benefits
   - Reduces false positives
   - Provides visibility into MCP usage
   - Maintains security oversight
    `.trim()
  },
  investigation: {
    title: 'Investigation Workflow',
    content: `
Security analysts can investigate detections:

1. Review Evidence
   Examine all evidence types (endpoint, network, LLM) to understand what was detected.

2. Provide Feedback
   Mark detections as:
   - True Positive: Real security concern
   - False Positive: Legitimate but not registered
   - Investigation Needed: Requires more analysis
   - Escalation Required: Serious issue

3. Collaborate
   Add notes to investigations, track progress, and resolve issues as a team.

4. Resolution
   Close investigations with resolution notes once the issue is addressed.
    `.trim()
  }
};

export const HelpTooltip: React.FC<HelpTooltipProps> = ({ topic, className = '' }) => {
  const [isOpen, setIsOpen] = useState(false);

  const content = helpContent[topic];

  return (
    <div className={`relative inline-block ${className}`}>
      {/* Help Icon Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        onBlur={() => setTimeout(() => setIsOpen(false), 200)}
        className="inline-flex items-center justify-center w-5 h-5 text-gray-400 hover:text-gray-600 transition-colors"
        aria-label="Help"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </button>

      {/* Tooltip Popup */}
      {isOpen && (
        <div className="absolute z-50 w-96 p-4 bg-white border border-gray-200 rounded-lg shadow-xl -right-2 top-8">
          {/* Arrow */}
          <div className="absolute -top-2 right-3 w-4 h-4 bg-white border-l border-t border-gray-200 transform rotate-45"></div>

          {/* Content */}
          <div className="relative">
            <h4 className="text-sm font-semibold text-gray-900 mb-2">{content.title}</h4>
            <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-line">
              {content.content}
            </p>
          </div>

          {/* Close Button */}
          <button
            onClick={() => setIsOpen(false)}
            className="absolute top-0 right-0 text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
};

export default HelpTooltip;
