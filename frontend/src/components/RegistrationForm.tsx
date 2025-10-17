/**
 * MCP Registration form component
 *
 * Reference: US1 (MCP registration), FR-004 (Registry requirements)
 */

import React, { useState } from 'react';
import { useRegistryStore } from '../store/detections';
import type { Detection, RegistryEntryCreate } from '../api/client';

interface RegistrationFormProps {
  detection?: Detection;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export const RegistrationForm: React.FC<RegistrationFormProps> = ({
  detection,
  onSuccess,
  onCancel,
}) => {
  const { createEntry, isLoading, error } = useRegistryStore();

  const [formData, setFormData] = useState<RegistryEntryCreate>({
    composite_id: detection?.composite_id || '',
    host_id_hash: detection?.host_id || '',
    port: undefined,
    manifest_hash: '',
    process_signature: '',
    name: '',
    description: '',
    version: '',
    business_justification: '',
    tags: [],
    auto_approve: false,
    expires_at: undefined,
  });

  const [tagInput, setTagInput] = useState('');
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const handleChange = (field: keyof RegistryEntryCreate, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors((prev) => {
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

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = 'Name is required';
    }

    if (!formData.business_justification.trim()) {
      errors.business_justification = 'Business justification is required';
    } else if (formData.business_justification.trim().length < 20) {
      errors.business_justification = 'Please provide a more detailed justification (minimum 20 characters)';
    }

    if (!formData.composite_id && !formData.host_id_hash && !formData.manifest_hash) {
      errors.identifiers = 'At least one identifier is required (composite ID, host ID, or manifest hash)';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await createEntry(formData);
      onSuccess?.();
    } catch (err) {
      // Error is handled by the store
      console.error('Failed to create registry entry:', err);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Register MCP Server</h2>
        <p className="text-sm text-gray-600 mt-1">
          Register this MCP server to authorize future detections and prevent alerts.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Basic Information */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Basic Information</h3>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            placeholder="e.g., Production API MCP Server"
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              validationErrors.name ? 'border-red-300' : 'border-gray-300'
            }`}
            disabled={isLoading}
          />
          {validationErrors.name && (
            <p className="text-red-500 text-xs mt-1">{validationErrors.name}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => handleChange('description', e.target.value)}
            placeholder="Brief description of this MCP server"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Version</label>
          <input
            type="text"
            value={formData.version}
            onChange={(e) => handleChange('version', e.target.value)}
            placeholder="e.g., 1.0.0"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Business Justification <span className="text-red-500">*</span>
          </label>
          <textarea
            value={formData.business_justification}
            onChange={(e) => handleChange('business_justification', e.target.value)}
            placeholder="Explain why this MCP server is needed for your work"
            rows={4}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              validationErrors.business_justification ? 'border-red-300' : 'border-gray-300'
            }`}
            disabled={isLoading}
          />
          {validationErrors.business_justification && (
            <p className="text-red-500 text-xs mt-1">{validationErrors.business_justification}</p>
          )}
        </div>
      </div>

      {/* Identifiers */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Identifiers</h3>
        <p className="text-sm text-gray-600">
          At least one identifier is required. Pre-filled from detection if available.
        </p>

        {validationErrors.identifiers && (
          <p className="text-red-500 text-sm">{validationErrors.identifiers}</p>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Composite ID</label>
          <input
            type="text"
            value={formData.composite_id}
            onChange={(e) => handleChange('composite_id', e.target.value)}
            placeholder="SHA256 composite identifier"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Host ID Hash</label>
          <input
            type="text"
            value={formData.host_id_hash}
            onChange={(e) => handleChange('host_id_hash', e.target.value)}
            placeholder="SHA256 hashed host ID"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
          <input
            type="number"
            min="1"
            max="65535"
            value={formData.port || ''}
            onChange={(e) => handleChange('port', e.target.value ? parseInt(e.target.value) : undefined)}
            placeholder="e.g., 3000"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Manifest Hash</label>
          <input
            type="text"
            value={formData.manifest_hash}
            onChange={(e) => handleChange('manifest_hash', e.target.value)}
            placeholder="SHA256 hash of manifest file"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Process Signature</label>
          <input
            type="text"
            value={formData.process_signature}
            onChange={(e) => handleChange('process_signature', e.target.value)}
            placeholder="Process signature"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
        </div>
      </div>

      {/* Tags */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Tags</h3>
        <p className="text-sm text-gray-600">Add tags to categorize this MCP server</p>

        <div className="flex gap-2">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
            placeholder="e.g., production, api, customer-facing"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={handleAddTag}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            disabled={isLoading}
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
                  disabled={isLoading}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Additional Options */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Additional Options</h3>

        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="auto_approve"
            checked={formData.auto_approve}
            onChange={(e) => handleChange('auto_approve', e.target.checked)}
            className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            disabled={isLoading}
          />
          <label htmlFor="auto_approve" className="flex-1">
            <span className="text-sm font-medium text-gray-700">Auto-approve similar detections</span>
            <p className="text-xs text-gray-600 mt-1">
              Automatically approve future detections that match this MCP server
            </p>
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Expiration Date</label>
          <input
            type="datetime-local"
            value={formData.expires_at ? formData.expires_at.slice(0, 16) : ''}
            onChange={(e) => handleChange('expires_at', e.target.value ? e.target.value : undefined)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isLoading}
          />
          <p className="text-xs text-gray-600 mt-1">
            Optional: Set an expiration date for this registration
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          type="submit"
          disabled={isLoading}
          className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Submitting...' : 'Submit Registration'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
        )}
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-900">
          <strong>Note:</strong> Your registration will be pending until approved by an administrator.
          You'll be notified via email once it's processed.
        </p>
      </div>
    </form>
  );
};

export default RegistrationForm;
