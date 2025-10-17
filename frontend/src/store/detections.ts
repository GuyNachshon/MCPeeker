/**
 * Zustand store for detection management
 *
 * Reference: US1 (Detection viewing), US2 (Investigation)
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient, Detection } from '../api/client';

interface DetectionFilters {
  classification?: 'authorized' | 'suspect' | 'unauthorized';
  startTime?: string;
  endTime?: string;
  searchTerm?: string;
}

interface DetectionState {
  // State
  detections: Detection[];
  selectedDetection: Detection | null;
  filters: DetectionFilters;
  isLoading: boolean;
  error: string | null;

  // Pagination
  skip: number;
  limit: number;
  total: number;

  // Actions
  fetchDetections: () => Promise<void>;
  fetchDetection: (id: string) => Promise<void>;
  setFilters: (filters: DetectionFilters) => void;
  clearFilters: () => void;
  setSelectedDetection: (detection: Detection | null) => void;
  nextPage: () => void;
  prevPage: () => void;
  setPage: (page: number) => void;
}

export const useDetectionStore = create<DetectionState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        detections: [],
        selectedDetection: null,
        filters: {},
        isLoading: false,
        error: null,
        skip: 0,
        limit: 25,
        total: 0,

        // Fetch detections with filters
        fetchDetections: async () => {
          set({ isLoading: true, error: null });

          try {
            const { filters, skip, limit } = get();

            const detections = await apiClient.listDetections({
              classification: filters.classification,
              start_time: filters.startTime,
              end_time: filters.endTime,
              skip,
              limit,
            });

            set({
              detections,
              isLoading: false,
              total: detections.length, // TODO: Get total from API
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch detections',
              isLoading: false,
            });
          }
        },

        // Fetch single detection
        fetchDetection: async (id: string) => {
          set({ isLoading: true, error: null });

          try {
            const detection = await apiClient.getDetection(id);
            set({
              selectedDetection: detection,
              isLoading: false,
            });
          } catch (error) {
            set({
              error: error instanceof Error ? error.message : 'Failed to fetch detection',
              isLoading: false,
            });
          }
        },

        // Set filters and fetch
        setFilters: (filters: DetectionFilters) => {
          set({ filters, skip: 0 }); // Reset to first page
          get().fetchDetections();
        },

        // Clear filters
        clearFilters: () => {
          set({ filters: {}, skip: 0 });
          get().fetchDetections();
        },

        // Set selected detection
        setSelectedDetection: (detection: Detection | null) => {
          set({ selectedDetection: detection });
        },

        // Pagination
        nextPage: () => {
          const { skip, limit, total } = get();
          if (skip + limit < total) {
            set({ skip: skip + limit });
            get().fetchDetections();
          }
        },

        prevPage: () => {
          const { skip, limit } = get();
          if (skip > 0) {
            set({ skip: Math.max(0, skip - limit) });
            get().fetchDetections();
          }
        },

        setPage: (page: number) => {
          const { limit } = get();
          set({ skip: page * limit });
          get().fetchDetections();
        },
      }),
      {
        name: 'detection-store',
        partialize: (state) => ({
          filters: state.filters,
          limit: state.limit,
        }),
      }
    )
  )
);

// Registry store
interface RegistryState {
  entries: any[];
  selectedEntry: any | null;
  isLoading: boolean;
  error: string | null;

  fetchEntries: () => Promise<void>;
  fetchEntry: (id: string) => Promise<void>;
  createEntry: (data: any) => Promise<void>;
  updateEntry: (id: string, data: any) => Promise<void>;
  deleteEntry: (id: string) => Promise<void>;
  approveEntry: (id: string) => Promise<void>;
  rejectEntry: (id: string, reason: string) => Promise<void>;
}

export const useRegistryStore = create<RegistryState>()(
  devtools((set, get) => ({
    entries: [],
    selectedEntry: null,
    isLoading: false,
    error: null,

    fetchEntries: async () => {
      set({ isLoading: true, error: null });
      try {
        const entries = await apiClient.listRegistryEntries();
        set({ entries, isLoading: false });
      } catch (error) {
        set({
          error: error instanceof Error ? error.message : 'Failed to fetch entries',
          isLoading: false,
        });
      }
    },

    fetchEntry: async (id: string) => {
      set({ isLoading: true, error: null });
      try {
        const entry = await apiClient.getRegistryEntry(id);
        set({ selectedEntry: entry, isLoading: false });
      } catch (error) {
        set({
          error: error instanceof Error ? error.message : 'Failed to fetch entry',
          isLoading: false,
        });
      }
    },

    createEntry: async (data: any) => {
      set({ isLoading: true, error: null });
      try {
        await apiClient.createRegistryEntry(data);
        set({ isLoading: false });
        // Refresh list
        get().fetchEntries();
      } catch (error) {
        set({
          error: error instanceof Error ? error.message : 'Failed to create entry',
          isLoading: false,
        });
        throw error;
      }
    },

    updateEntry: async (id: string, data: any) => {
      set({ isLoading: true, error: null });
      try {
        await apiClient.updateRegistryEntry(id, data);
        set({ isLoading: false });
        get().fetchEntries();
      } catch (error) {
        set({
          error: error instanceof Error ? error.message : 'Failed to update entry',
          isLoading: false,
        });
        throw error;
      }
    },

    deleteEntry: async (id: string) => {
      set({ isLoading: true, error: null });
      try {
        await apiClient.deleteRegistryEntry(id);
        set({ isLoading: false });
        get().fetchEntries();
      } catch (error) {
        set({
          error: error instanceof Error ? error.message : 'Failed to delete entry',
          isLoading: false,
        });
        throw error;
      }
    },

    approveEntry: async (id: string) => {
      set({ isLoading: true, error: null });
      try {
        await apiClient.approveRegistryEntry(id);
        set({ isLoading: false });
        get().fetchEntries();
      } catch (error) {
        set({
          error: error instanceof Error ? error.message : 'Failed to approve entry',
          isLoading: false,
        });
        throw error;
      }
    },

    rejectEntry: async (id: string, reason: string) => {
      set({ isLoading: true, error: null });
      try {
        await apiClient.rejectRegistryEntry(id, reason);
        set({ isLoading: false });
        get().fetchEntries();
      } catch (error) {
        set({
          error: error instanceof Error ? error.message : 'Failed to reject entry',
          isLoading: false,
        });
        throw error;
      }
    },
  }))
);
