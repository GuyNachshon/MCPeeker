/**
 * API client for Registry API
 *
 * Reference: US1 (Detection and Registration), US2 (Investigation), US3 (Admin)
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

// API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Types
export interface Detection {
  event_id: string;
  timestamp: string;
  host_id: string;
  composite_id: string;
  score: number;
  classification: 'authorized' | 'suspect' | 'unauthorized';
  evidence: Evidence[];
  registry_matched: boolean;
  judge_available: boolean;
}

export interface Evidence {
  type: 'endpoint' | 'network' | 'gateway';
  source: string;
  score_contribution: number;
  snippet?: string;
  file_path?: string;
  process_name?: string;
}

export interface RegistryEntry {
  id: string;
  composite_id?: string;
  host_id_hash?: string;
  port?: number;
  manifest_hash?: string;
  process_signature?: string;
  name: string;
  description?: string;
  version?: string;
  owner_email: string;
  business_justification: string;
  tags?: string[];
  status: 'pending' | 'approved' | 'rejected' | 'revoked';
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
  auto_approve: boolean;
  created_at: string;
  updated_at: string;
  expires_at?: string;
}

export interface RegistryEntryCreate {
  composite_id?: string;
  host_id_hash?: string;
  port?: number;
  manifest_hash?: string;
  process_signature?: string;
  name: string;
  description?: string;
  version?: string;
  business_justification: string;
  tags?: string[];
  auto_approve?: boolean;
  expires_at?: string;
}

export interface NotificationPreference {
  id: string;
  user_id: string;
  registry_entry_id?: string;
  enabled: boolean;
  channel: 'email' | 'slack' | 'webhook' | 'pagerduty';
  email_address?: string;
  min_severity: 'low' | 'medium' | 'high' | 'critical';
  notify_on_authorized: boolean;
  notify_on_suspect: boolean;
  notify_on_unauthorized: boolean;
  max_notifications_per_hour: number;
  digest_enabled: boolean;
  digest_frequency_minutes?: number;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  quiet_hours_timezone?: string;
  created_at: string;
  updated_at: string;
  last_notification_sent_at?: string;
}

export interface User {
  id: string;
  email: string;
  role: 'developer' | 'analyst' | 'admin';
  associated_endpoints?: string[];
  created_at: string;
  last_login_at?: string;
  is_active: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * API Client class
 */
class APIClient {
  private client: AxiosInstance;

  constructor(baseURL: string = API_BASE_URL) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor to handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Unauthorized - clear token and redirect to login
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const response = await this.client.post('/api/v1/auth/login', { email, password });
    return response.data;
  }

  async logout(): Promise<void> {
    await this.client.post('/api/v1/auth/logout');
    localStorage.removeItem('access_token');
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/api/v1/auth/me');
    return response.data;
  }

  // Registry API
  async listRegistryEntries(params?: {
    status_filter?: string;
    owner_email?: string;
    tag?: string;
    skip?: number;
    limit?: number;
  }): Promise<RegistryEntry[]> {
    const response = await this.client.get('/api/v1/registry/entries', { params });
    return response.data;
  }

  async getRegistryEntry(id: string): Promise<RegistryEntry> {
    const response = await this.client.get(`/api/v1/registry/entries/${id}`);
    return response.data;
  }

  async createRegistryEntry(data: RegistryEntryCreate): Promise<RegistryEntry> {
    const response = await this.client.post('/api/v1/registry/entries', data);
    return response.data;
  }

  async updateRegistryEntry(id: string, data: Partial<RegistryEntryCreate>): Promise<RegistryEntry> {
    const response = await this.client.patch(`/api/v1/registry/entries/${id}`, data);
    return response.data;
  }

  async deleteRegistryEntry(id: string): Promise<void> {
    await this.client.delete(`/api/v1/registry/entries/${id}`);
  }

  async approveRegistryEntry(id: string): Promise<RegistryEntry> {
    const response = await this.client.post(`/api/v1/registry/entries/${id}/approve`);
    return response.data;
  }

  async rejectRegistryEntry(id: string, reason: string): Promise<RegistryEntry> {
    const response = await this.client.post(`/api/v1/registry/entries/${id}/reject`, { reason });
    return response.data;
  }

  async revokeRegistryEntry(id: string, reason: string): Promise<RegistryEntry> {
    const response = await this.client.post(`/api/v1/registry/entries/${id}/revoke`, { reason });
    return response.data;
  }

  // Detections (placeholder - will be implemented in Phase 4)
  async listDetections(params?: {
    classification?: string;
    start_time?: string;
    end_time?: string;
    skip?: number;
    limit?: number;
  }): Promise<Detection[]> {
    const response = await this.client.get('/api/v1/detections', { params });
    return response.data;
  }

  async getDetection(id: string): Promise<Detection> {
    const response = await this.client.get(`/api/v1/detections/${id}`);
    return response.data;
  }

  // Notifications
  async listNotificationPreferences(params?: {
    registry_entry_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<NotificationPreference[]> {
    const response = await this.client.get('/api/v1/notifications/preferences', { params });
    return response.data;
  }

  async getNotificationPreference(id: string): Promise<NotificationPreference> {
    const response = await this.client.get(`/api/v1/notifications/preferences/${id}`);
    return response.data;
  }

  async createNotificationPreference(data: Partial<NotificationPreference>): Promise<NotificationPreference> {
    const response = await this.client.post('/api/v1/notifications/preferences', data);
    return response.data;
  }

  async updateNotificationPreference(id: string, data: Partial<NotificationPreference>): Promise<NotificationPreference> {
    const response = await this.client.patch(`/api/v1/notifications/preferences/${id}`, data);
    return response.data;
  }

  async deleteNotificationPreference(id: string): Promise<void> {
    await this.client.delete(`/api/v1/notifications/preferences/${id}`);
  }

  async testNotification(id: string): Promise<{ status: string; message: string; channel: string }> {
    const response = await this.client.post(`/api/v1/notifications/preferences/${id}/test`);
    return response.data;
  }

  // Feedback API
  async submitFeedback(data: any): Promise<any> {
    const response = await this.client.post('/api/v1/feedback', data);
    return response.data;
  }

  async listFeedback(params?: {
    detection_id?: string;
    feedback_type?: string;
    investigation_status?: string;
    analyst_email?: string;
    skip?: number;
    limit?: number;
  }): Promise<any[]> {
    const response = await this.client.get('/api/v1/feedback', { params });
    return response.data;
  }

  async getFeedback(id: string): Promise<any> {
    const response = await this.client.get(`/api/v1/feedback/${id}`);
    return response.data;
  }

  async updateFeedback(id: string, data: any): Promise<any> {
    const response = await this.client.patch(`/api/v1/feedback/${id}`, data);
    return response.data;
  }

  async resolveFeedback(id: string, resolution_notes: string): Promise<any> {
    const response = await this.client.post(`/api/v1/feedback/${id}/resolve`, { resolution_notes });
    return response.data;
  }

  async reopenFeedback(id: string): Promise<any> {
    const response = await this.client.post(`/api/v1/feedback/${id}/reopen`);
    return response.data;
  }

  async addInvestigationNote(feedbackId: string, data: any): Promise<any> {
    const response = await this.client.post(`/api/v1/feedback/${feedbackId}/notes`, data);
    return response.data;
  }

  async getInvestigationNotes(feedbackId: string, includeInternal?: boolean): Promise<any[]> {
    const response = await this.client.get(`/api/v1/feedback/${feedbackId}/notes`, {
      params: { include_internal: includeInternal },
    });
    return response.data;
  }

  async getInvestigationTimeline(detectionId: string): Promise<any> {
    const response = await this.client.get(`/api/v1/feedback/detection/${detectionId}/timeline`);
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Export class for testing
export default APIClient;
