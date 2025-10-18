/**
 * UI Component Type Definitions
 * Feature: Testing and UI Improvements (002-testing-ui-improvements)
 *
 * TypeScript type definitions for React components used in integration tests
 * and component testing. These types serve as contracts for UI behavior.
 */

// ============================================================================
// Detection Badge Component
// ============================================================================

/**
 * Classification type for MCP detections
 * Maps to scoring thresholds and registry match logic
 */
export type Classification = 'authorized' | 'suspect' | 'unauthorized';

/**
 * Props for DetectionBadge component
 * Used in detection lists, detail views, and dashboard summary
 */
export interface DetectionBadgeProps {
  /**
   * Classification status determined by correlator
   * - authorized: score ≤4 OR registry match (forced)
   * - suspect: score 5-8 (no registry match)
   * - unauthorized: score ≥9 (no registry match)
   */
  classification: Classification;

  /**
   * Badge size variant
   * @default 'md'
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Show tooltip on hover with explanation
   * @default false
   */
  showTooltip?: boolean;

  /**
   * Custom tooltip text (overrides default)
   * Default tooltips:
   * - authorized: "Approved MCP or low risk score"
   * - suspect: "Medium risk score - review recommended"
   * - unauthorized: "High risk score - action required"
   */
  tooltipText?: string;

  /**
   * Additional CSS classes for custom styling
   */
  className?: string;
}

// ============================================================================
// Dashboard Summary Component
// ============================================================================

/**
 * Props for DashboardSummary component
 * Displays aggregate detection counts by classification
 */
export interface DashboardSummaryProps {
  /**
   * Count of authorized detections (includes registry matches)
   */
  authorizedCount: number;

  /**
   * Count of suspect detections (medium risk)
   */
  suspectCount: number;

  /**
   * Count of unauthorized detections (high risk)
   */
  unauthorizedCount: number;

  /**
   * Timestamp of last data refresh
   */
  lastUpdated: Date;

  /**
   * Loading state (e.g., fetching updated counts)
   * @default false
   */
  loading?: boolean;

  /**
   * Error message if count fetch failed
   */
  error?: string | null;

  /**
   * Callback when user clicks on a classification count
   * Used to filter detection list by classification
   */
  onClassificationClick?: (classification: Classification) => void;
}

/**
 * Internal state model for DashboardSummary component
 * Used in component tests to verify state transitions
 */
export interface DashboardSummaryState {
  authorizedCount: number;
  suspectCount: number;
  unauthorizedCount: number;
  lastUpdated: Date;
  loading: boolean;
  error: string | null;
}

// ============================================================================
// Detection Filter Component
// ============================================================================

/**
 * Props for DetectionFilter component
 * Controls which detections are visible in the list
 */
export interface DetectionFilterProps {
  /**
   * Current filter state
   */
  filters: DetectionFilterState;

  /**
   * Callback when filter state changes
   */
  onFilterChange: (filters: DetectionFilterState) => void;

  /**
   * Total detection count (for displaying "X of Y" summary)
   */
  totalCount?: number;

  /**
   * Filtered detection count
   */
  filteredCount?: number;
}

/**
 * Filter state model
 * Represents active filters applied to detection list
 */
export interface DetectionFilterState {
  /**
   * Hide authorized detections from list
   * @default false
   */
  hideAuthorized: boolean;

  /**
   * Text search query (searches composite_id, host_id, etc.)
   * @default ''
   */
  searchQuery: string;

  /**
   * Date range filter for detection timestamp
   */
  dateRange: {
    /**
     * Start date (inclusive)
     */
    start: Date | null;

    /**
     * End date (inclusive)
     */
    end: Date | null;
  };

  /**
   * Filter by specific classification types
   * Empty array = show all classifications
   * @default []
   */
  classifications: Classification[];
}

// ============================================================================
// Detection Detail View
// ============================================================================

/**
 * Props for detection detail view showing registry match explanation
 */
export interface DetectionDetailProps {
  /**
   * Detection composite ID
   */
  compositeId: string;

  /**
   * Raw detection score (before registry penalty)
   */
  rawScore: number;

  /**
   * Final detection score (after registry penalty)
   */
  finalScore: number;

  /**
   * Classification status
   */
  classification: Classification;

  /**
   * Whether detection matched registry
   */
  registryMatched: boolean;

  /**
   * Registry entry ID if matched
   */
  registryEntryId?: string;

  /**
   * Evidence records contributing to score
   */
  evidence: EvidenceRecord[];
}

/**
 * Evidence record type
 * Represents individual detection signals
 */
export interface EvidenceRecord {
  /**
   * Evidence type
   */
  type: 'endpoint' | 'network' | 'gateway' | 'process' | 'judge' | 'registry';

  /**
   * Score contribution from this evidence
   */
  scoreContribution: number;

  /**
   * Timestamp when evidence was collected
   */
  timestamp: Date;

  /**
   * Additional evidence metadata
   */
  details: Record<string, unknown>;
}

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Mock detection data for component tests
 * Use this type to create test fixtures
 */
export interface MockDetection {
  compositeId: string;
  hostIdHash: string;
  classification: Classification;
  score: number;
  rawScore: number;
  registryMatched: boolean;
  evidence: EvidenceRecord[];
  timestamp: Date;
}

/**
 * Helper function type for creating test detections
 */
export type CreateMockDetection = (
  overrides?: Partial<MockDetection>
) => MockDetection;

// ============================================================================
// API Response Types (used in integration tests)
// ============================================================================

/**
 * API response for fetching detection counts
 * Endpoint: GET /api/v1/detections/summary
 */
export interface DetectionSummaryResponse {
  authorized: number;
  suspect: number;
  unauthorized: number;
  last_updated: string; // ISO 8601 timestamp
}

/**
 * API response for fetching detection list
 * Endpoint: GET /api/v1/detections
 */
export interface DetectionListResponse {
  detections: DetectionListItem[];
  total_count: number;
  filtered_count: number;
  page: number;
  page_size: number;
}

/**
 * Individual detection in list response
 */
export interface DetectionListItem {
  composite_id: string;
  host_id_hash: string;
  classification: Classification;
  score: number;
  registry_matched: boolean;
  timestamp: string; // ISO 8601 timestamp
  evidence_count: number;
}

// ============================================================================
// Component Test Helpers
// ============================================================================

/**
 * Test helper: Render options for React Testing Library
 */
export interface ComponentTestOptions {
  /**
   * Initial props to pass to component
   */
  initialProps?: Record<string, unknown>;

  /**
   * Mock API responses
   */
  mockApi?: {
    summary?: DetectionSummaryResponse;
    list?: DetectionListResponse;
  };

  /**
   * Initial filter state for filter tests
   */
  initialFilters?: DetectionFilterState;
}

/**
 * Test helper: Expected badge styling
 * Used in component tests to verify correct colors/styles
 */
export interface ExpectedBadgeStyle {
  backgroundColor: string;
  textColor: string;
  text: string;
}

/**
 * Mapping of classifications to expected badge styles
 */
export const BADGE_STYLES: Record<Classification, ExpectedBadgeStyle> = {
  authorized: {
    backgroundColor: 'bg-green-500',
    textColor: 'text-white',
    text: 'Authorized',
  },
  suspect: {
    backgroundColor: 'bg-yellow-500',
    textColor: 'text-black',
    text: 'Suspect',
  },
  unauthorized: {
    backgroundColor: 'bg-red-500',
    textColor: 'text-white',
    text: 'Unauthorized',
  },
};
