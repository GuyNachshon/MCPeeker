/**
 * Feedback submission form for analysts
 *
 * Reference: FR-023 (Analyst feedback), US2
 */

import React, { useState } from 'react';
import type { Detection } from '../api/client';

interface FeedbackFormProps {
  detection: Detection;
  onSubmit: (feedback: FeedbackData) => Promise<void>;
  onCancel?: () => void;
}

export interface FeedbackData {
  detection_id: string;
  composite_id?: string;
  feedback_type: 'false_positive' | 'true_positive' | 'investigation_needed' | 'escalation_required' | 'resolved';
  severity?: 'low' | 'medium' | 'high' | 'critical';
  notes: string;
  recommended_action?: string;
  tags?: string[];
  additional_context?: Record<string, any>;
}

export const FeedbackForm: React.FC<FeedbackFormProps> = ({
  detection,
  onSubmit,
  onCancel,
}) => {
  const [formData, setFormData] = useState<FeedbackData>({
    detection_id: detection.detection_id,
    composite_id: detection.composite_id,
    feedback_type: 'investigation_needed',
    severity: 'medium',
    notes: '',
    recommended_action: '',
    tags: [],
  });

  const [tagInput, setTagInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (field: keyof FeedbackData, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags?.includes(tagInput.trim())) {
      setFormData((prev) => ({
        ...prev,
        tags: [...(prev.tags || []), tagInput.trim()],
      }));
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags?.filter((t) => t !== tag) || [],
    }));
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.notes.trim() || formData.notes.trim().length < 10) {
      newErrors.notes = 'Notes must be at least 10 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await onSubmit(formData);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      setErrors({ submit: 'Failed to submit feedback. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getFeedbackTypeLabel = (type: string) => {
    const labels = {
      false_positive: 'False Positive',
      true_positive: 'True Positive',
      investigation_needed: 'Investigation Needed',
      escalation_required: 'Escalation Required',
      resolved: 'Resolved',
    };
    return labels[type as keyof typeof labels] || type;
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Submit Analysis Feedback</h3>
        <p className="text-sm text-gray-600">
          Provide feedback on this detection to improve system accuracy and track investigation progress.
        </p>
      </div>

      {errors.submit && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{errors.submit}</p>
        </div>
      )}

      {/* Feedback Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Feedback Type <span className="text-red-500">*</span>
        </label>
        <div className="grid grid-cols-2 gap-3">
          {['false_positive', 'true_positive', 'investigation_needed', 'escalation_required', 'resolved'].map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => handleChange('feedback_type', type)}
              className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-colors ${
                formData.feedback_type === type
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
              }`}
            >
              {getFeedbackTypeLabel(type)}
            </button>
          ))}
        </div>
      </div>

      {/* Severity */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Severity Assessment
        </label>
        <div className="flex gap-2">
          {['low', 'medium', 'high', 'critical'].map((severity) => (
            <button
              key={severity}
              type="button"
              onClick={() => handleChange('severity', severity)}
              className={`flex-1 px-4 py-2 rounded-lg border-2 text-sm font-medium capitalize transition-colors ${
                formData.severity === severity
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
              }`}
            >
              {severity}
            </button>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Analysis Notes <span className="text-red-500">*</span>
        </label>
        <textarea
          value={formData.notes}
          onChange={(e) => handleChange('notes', e.target.value)}
          rows={6}
          placeholder="Provide detailed analysis of this detection..."
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            errors.notes ? 'border-red-300' : 'border-gray-300'
          }`}
          disabled={isSubmitting}
        />
        {errors.notes && (
          <p className="text-red-500 text-xs mt-1">{errors.notes}</p>
        )}
        <p className="text-xs text-gray-500 mt-1">
          Minimum 10 characters. Include relevant context and findings.
        </p>
      </div>

      {/* Recommended Action */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Recommended Action
        </label>
        <textarea
          value={formData.recommended_action}
          onChange={(e) => handleChange('recommended_action', e.target.value)}
          rows={3}
          placeholder="What action should be taken based on your analysis?"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          disabled={isSubmitting}
        />
      </div>

      {/* Tags */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Tags
        </label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
            placeholder="Add tags (e.g., malware, phishing, insider-threat)"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isSubmitting}
          />
          <button
            type="button"
            onClick={handleAddTag}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            disabled={isSubmitting}
          >
            Add
          </button>
        </div>
        {formData.tags && formData.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {formData.tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => handleRemoveTag(tag)}
                  className="text-blue-500 hover:text-blue-700"
                  disabled={isSubmitting}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-gray-200">
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
};

export default FeedbackForm;
