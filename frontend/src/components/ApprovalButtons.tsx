/**
 * Approval action buttons component - Admin-only approve/deny buttons
 *
 * Reference: US3 (Admin approval workflow), T103
 */

import React, { useState } from 'react';

interface ApprovalButtonsProps {
  entryId: string;
  entryName: string;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
}

export const ApprovalButtons: React.FC<ApprovalButtonsProps> = ({
  entryId,
  entryName,
  onApprove,
  onReject,
}) => {
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await onApprove(entryId);
      setShowApproveDialog(false);
    } catch (error) {
      alert(`Failed to approve: ${error}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      alert('Please provide a rejection reason');
      return;
    }

    setIsSubmitting(true);
    try {
      await onReject(entryId, rejectReason);
      setShowRejectDialog(false);
      setRejectReason('');
    } catch (error) {
      alert(`Failed to reject: ${error}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex gap-2">
      {/* Approve Button */}
      <button
        onClick={() => setShowApproveDialog(true)}
        disabled={isSubmitting}
        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50"
      >
        Approve
      </button>

      {/* Reject Button */}
      <button
        onClick={() => setShowRejectDialog(true)}
        disabled={isSubmitting}
        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium disabled:opacity-50"
      >
        Reject
      </button>

      {/* Approve Confirmation Dialog */}
      {showApproveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Approve Registration</h3>
            <p className="text-sm text-gray-600 mb-4">
              Are you sure you want to approve the registration for <strong>{entryName}</strong>?
            </p>
            <p className="text-xs text-gray-500 mb-4">
              This will allow the MCP to operate without triggering unauthorized detections.
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowApproveDialog(false)}
                disabled={isSubmitting}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleApprove}
                disabled={isSubmitting}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Approving...' : 'Approve'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Dialog */}
      {showRejectDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Reject Registration</h3>
            <p className="text-sm text-gray-600 mb-4">
              Provide a reason for rejecting the registration for <strong>{entryName}</strong>:
            </p>

            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Enter rejection reason (required)"
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
            />

            <p className="text-xs text-gray-500 mb-4">
              The owner will be notified of your decision and the reason provided.
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowRejectDialog(false);
                  setRejectReason('');
                }}
                disabled={isSubmitting}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={isSubmitting || !rejectReason.trim()}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Rejecting...' : 'Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApprovalButtons;
