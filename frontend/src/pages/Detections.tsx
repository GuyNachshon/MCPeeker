/**
 * Detections page - main view for detection management
 *
 * Reference: US1 (Detection and Registration MVP)
 */

import React, { useState } from 'react';
import DetectionList from '../components/DetectionList';
import DetectionDetail from '../components/DetectionDetail';
import RegistrationForm from '../components/RegistrationForm';
import type { Detection } from '../api/client';

type ViewMode = 'list' | 'detail' | 'register';

export const DetectionsPage: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null);

  const handleSelectDetection = (detection: Detection) => {
    setSelectedDetection(detection);
    setViewMode('detail');
  };

  const handleRegister = (detection: Detection) => {
    setSelectedDetection(detection);
    setViewMode('register');
  };

  const handleBackToList = () => {
    setViewMode('list');
    setSelectedDetection(null);
  };

  const handleRegistrationSuccess = () => {
    setViewMode('list');
    setSelectedDetection(null);
    // TODO: Show success toast notification
  };

  const renderBreadcrumb = () => {
    return (
      <nav className="flex items-center space-x-2 text-sm mb-6">
        <button
          onClick={handleBackToList}
          className={`hover:text-blue-600 transition-colors ${
            viewMode === 'list' ? 'text-gray-900 font-semibold' : 'text-gray-600'
          }`}
        >
          Detections
        </button>
        {viewMode !== 'list' && (
          <>
            <span className="text-gray-400">/</span>
            <span className="text-gray-900 font-semibold">
              {viewMode === 'detail' ? 'Detail' : 'Register MCP'}
            </span>
          </>
        )}
      </nav>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">MCP Detections</h1>
              <p className="text-sm text-gray-600 mt-1">
                Monitor and manage Model Context Protocol server detections across your infrastructure
              </p>
            </div>
            {viewMode === 'list' && (
              <div className="flex gap-3">
                <button
                  onClick={() => setViewMode('register')}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  + Register MCP
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderBreadcrumb()}

        {viewMode === 'list' && (
          <DetectionList onSelectDetection={handleSelectDetection} />
        )}

        {viewMode === 'detail' && selectedDetection && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <DetectionDetail
              detection={selectedDetection}
              onClose={handleBackToList}
              onRegister={handleRegister}
            />
          </div>
        )}

        {viewMode === 'register' && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <RegistrationForm
              detection={selectedDetection || undefined}
              onSuccess={handleRegistrationSuccess}
              onCancel={handleBackToList}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default DetectionsPage;
