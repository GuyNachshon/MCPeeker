// Package mtls provides mTLS client utilities for secure inter-service communication.
// Reference: FR-010 (mTLS enforcement), research.md (certificate reload)
package mtls

import (
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
)

// TLSConfig holds mTLS configuration
type TLSConfig struct {
	CertFile string // Path to client certificate
	KeyFile  string // Path to client private key
	CAFile   string // Path to CA certificate

	// Auto-reload settings
	EnableAutoReload bool
	ReloadInterval   time.Duration
}

// Client represents an mTLS client with automatic certificate reloading
type Client struct {
	config    *TLSConfig
	tlsConfig *tls.Config
	mu        sync.RWMutex
	watcher   *fsnotify.Watcher
	stopChan  chan struct{}
}

// NewClient creates a new mTLS client
func NewClient(config *TLSConfig) (*Client, error) {
	client := &Client{
		config:   config,
		stopChan: make(chan struct{}),
	}

	// Load initial TLS config
	if err := client.loadTLSConfig(); err != nil {
		return nil, fmt.Errorf("failed to load TLS config: %w", err)
	}

	// Start auto-reload if enabled
	if config.EnableAutoReload {
		if err := client.startAutoReload(); err != nil {
			return nil, fmt.Errorf("failed to start auto-reload: %w", err)
		}
	}

	return client, nil
}

// GetTLSConfig returns the current TLS configuration (thread-safe)
func (c *Client) GetTLSConfig() *tls.Config {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.tlsConfig.Clone()
}

// loadTLSConfig loads certificates and creates TLS configuration
func (c *Client) loadTLSConfig() error {
	// Load client certificate and private key
	cert, err := tls.LoadX509KeyPair(c.config.CertFile, c.config.KeyFile)
	if err != nil {
		return fmt.Errorf("failed to load client certificate: %w", err)
	}

	// Load CA certificate
	caCert, err := os.ReadFile(c.config.CAFile)
	if err != nil {
		return fmt.Errorf("failed to read CA certificate: %w", err)
	}

	caCertPool := x509.NewCertPool()
	if !caCertPool.AppendCertsFromPEM(caCert) {
		return fmt.Errorf("failed to parse CA certificate")
	}

	// Create TLS configuration
	tlsConfig := &tls.Config{
		Certificates: []tls.Certificate{cert},
		RootCAs:      caCertPool,
		ClientCAs:    caCertPool,
		MinVersion:   tls.VersionTLS13, // Enforce TLS 1.3
		ClientAuth:   tls.RequireAndVerifyClientCert,
	}

	// Update client's TLS config (thread-safe)
	c.mu.Lock()
	c.tlsConfig = tlsConfig
	c.mu.Unlock()

	return nil
}

// startAutoReload starts watching certificate files for changes
func (c *Client) startAutoReload() error {
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		return fmt.Errorf("failed to create file watcher: %w", err)
	}

	// Watch certificate files
	if err := watcher.Add(c.config.CertFile); err != nil {
		return fmt.Errorf("failed to watch cert file: %w", err)
	}
	if err := watcher.Add(c.config.KeyFile); err != nil {
		return fmt.Errorf("failed to watch key file: %w", err)
	}
	if err := watcher.Add(c.config.CAFile); err != nil {
		return fmt.Errorf("failed to watch CA file: %w", err)
	}

	c.watcher = watcher

	// Start watching in background
	go c.watchCertificates()

	return nil
}

// watchCertificates watches for certificate file changes and reloads
func (c *Client) watchCertificates() {
	ticker := time.NewTicker(c.config.ReloadInterval)
	defer ticker.Stop()

	for {
		select {
		case event, ok := <-c.watcher.Events:
			if !ok {
				return
			}

			// Reload on write or create events
			if event.Op&fsnotify.Write == fsnotify.Write || event.Op&fsnotify.Create == fsnotify.Create {
				fmt.Printf("Certificate file changed: %s, reloading...\n", event.Name)
				if err := c.loadTLSConfig(); err != nil {
					fmt.Printf("Failed to reload TLS config: %v\n", err)
				} else {
					fmt.Println("TLS config reloaded successfully")
				}
			}

		case err, ok := <-c.watcher.Errors:
			if !ok {
				return
			}
			fmt.Printf("Certificate watcher error: %v\n", err)

		case <-ticker.C:
			// Periodic reload check (in case fsnotify misses events)
			if err := c.loadTLSConfig(); err != nil {
				fmt.Printf("Failed to reload TLS config: %v\n", err)
			}

		case <-c.stopChan:
			return
		}
	}
}

// Close stops the auto-reload watcher and cleans up resources
func (c *Client) Close() error {
	close(c.stopChan)
	if c.watcher != nil {
		return c.watcher.Close()
	}
	return nil
}

// ValidateCertificate checks if the certificate is valid and not expired
func (c *Client) ValidateCertificate() error {
	c.mu.RLock()
	defer c.mu.RUnlock()

	if len(c.tlsConfig.Certificates) == 0 {
		return fmt.Errorf("no certificates loaded")
	}

	cert := c.tlsConfig.Certificates[0]
	if len(cert.Certificate) == 0 {
		return fmt.Errorf("invalid certificate")
	}

	// Parse certificate to check expiration
	x509Cert, err := x509.ParseCertificate(cert.Certificate[0])
	if err != nil {
		return fmt.Errorf("failed to parse certificate: %w", err)
	}

	// Check expiration
	now := time.Now()
	if now.Before(x509Cert.NotBefore) {
		return fmt.Errorf("certificate not yet valid")
	}
	if now.After(x509Cert.NotAfter) {
		return fmt.Errorf("certificate expired on %v", x509Cert.NotAfter)
	}

	// Warn if expiring within 7 days
	sevenDaysFromNow := now.Add(7 * 24 * time.Hour)
	if sevenDaysFromNow.After(x509Cert.NotAfter) {
		daysLeft := int(time.Until(x509Cert.NotAfter).Hours() / 24)
		fmt.Printf("⚠️  WARNING: Certificate expires in %d days! Please renew.\n", daysLeft)
	}

	return nil
}
