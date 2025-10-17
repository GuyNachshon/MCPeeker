// Package registry provides registry lookup client for correlator.
// Reference: FR-005 (Registry matching), FR-010 (mTLS)
package registry

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/mtls"
)

// MatchRequest represents a registry match query
type MatchRequest struct {
	CompositeID  string `json:"composite_id,omitempty"`
	HostIDHash   string `json:"host_id_hash,omitempty"`
	Port         int    `json:"port,omitempty"`
	ManifestHash string `json:"manifest_hash,omitempty"`
}

// MatchResponse represents a registry match result
type MatchResponse struct {
	Matched bool                   `json:"matched"`
	Entry   map[string]interface{} `json:"entry"`
	Penalty int                    `json:"penalty"` // -6 if matched
}

// Client is a registry API client
type Client struct {
	baseURL    string
	httpClient *http.Client
	authToken  string
}

// Config holds registry client configuration
type Config struct {
	BaseURL    string
	TLSConfig  *mtls.TLSConfig
	AuthToken  string
	Timeout    time.Duration
}

// NewClient creates a new registry API client
func NewClient(config *Config) (*Client, error) {
	// Create HTTP client with optional mTLS
	httpClient := &http.Client{
		Timeout: config.Timeout,
	}

	if config.TLSConfig != nil {
		tlsClient, err := mtls.NewClient(config.TLSConfig)
		if err != nil {
			return nil, fmt.Errorf("failed to create mTLS client: %w", err)
		}

		httpClient.Transport = &http.Transport{
			TLSClientConfig: tlsClient.GetTLSConfig(),
		}
	}

	return &Client{
		baseURL:    config.BaseURL,
		httpClient: httpClient,
		authToken:  config.AuthToken,
	}, nil
}

// CheckMatch checks if a detection matches any registry entry
func (c *Client) CheckMatch(ctx context.Context, req MatchRequest) (*MatchResponse, error) {
	// Build query parameters
	params := url.Values{}
	if req.CompositeID != "" {
		params.Add("composite_id", req.CompositeID)
	}
	if req.HostIDHash != "" {
		params.Add("host_id_hash", req.HostIDHash)
	}
	if req.Port > 0 {
		params.Add("port", fmt.Sprintf("%d", req.Port))
	}
	if req.ManifestHash != "" {
		params.Add("manifest_hash", req.ManifestHash)
	}

	// Build URL
	endpoint := fmt.Sprintf("%s/api/v1/registry/match?%s", c.baseURL, params.Encode())

	// Create request
	httpReq, err := http.NewRequestWithContext(ctx, "GET", endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Add auth token if available
	if c.authToken != "" {
		httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.authToken))
	}

	// Execute request
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("registry API returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse response
	var matchResp MatchResponse
	if err := json.NewDecoder(resp.Body).Decode(&matchResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &matchResp, nil
}

// GetEntry retrieves a specific registry entry by ID
func (c *Client) GetEntry(ctx context.Context, entryID string) (map[string]interface{}, error) {
	endpoint := fmt.Sprintf("%s/api/v1/registry/entries/%s", c.baseURL, entryID)

	httpReq, err := http.NewRequestWithContext(ctx, "GET", endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	if c.authToken != "" {
		httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.authToken))
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("registry entry not found")
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("registry API returned status %d: %s", resp.StatusCode, string(body))
	}

	var entry map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&entry); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return entry, nil
}

// HealthCheck performs a health check on the registry API
func (c *Client) HealthCheck(ctx context.Context) error {
	endpoint := fmt.Sprintf("%s/health", c.baseURL)

	httpReq, err := http.NewRequestWithContext(ctx, "GET", endpoint, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("health check failed with status %d", resp.StatusCode)
	}

	return nil
}
