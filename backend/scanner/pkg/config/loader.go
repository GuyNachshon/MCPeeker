// Package config provides YAML configuration loading for the scanner service.
// Reference: FR-015 (declarative YAML configuration), FR-016 (JSON Schema validation)
package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// Config represents the scanner service configuration
type Config struct {
	// Global settings
	Global GlobalConfig `yaml:"global"`

	// Scanner-specific settings
	Scanner ScannerConfig `yaml:"scanner"`

	// NATS connection settings
	NATS NATSConfig `yaml:"nats"`

	// Observability settings
	Observability ObservabilityConfig `yaml:"observability"`
}

// GlobalConfig contains settings shared across all services
type GlobalConfig struct {
	Environment string `yaml:"environment"` // dev, staging, prod
	LogLevel    string `yaml:"log_level"`   // debug, info, warn, error
	Version     string `yaml:"version"`     // Service version
}

// ScannerConfig contains scanner-specific settings
type ScannerConfig struct {
	// Filesystem roots to scan (e.g., /home, /Users, /workspace)
	FilesystemRoots []string `yaml:"filesystem_roots"`

	// Scan interval (e.g., "12h")
	ScanInterval string `yaml:"scan_interval"`

	// Maximum concurrent file scans
	MaxConcurrentScans int `yaml:"max_concurrent_scans"`

	// File size limit for scanning (bytes)
	MaxFileSizeBytes int64 `yaml:"max_file_size_bytes"`

	// Process scan enabled
	ProcessScanEnabled bool `yaml:"process_scan_enabled"`

	// Manifest file patterns to search for
	ManifestPatterns []string `yaml:"manifest_patterns"`
}

// NATSConfig contains NATS JetStream connection settings
type NATSConfig struct {
	URL             string        `yaml:"url"`              // NATS server URL
	Subject         string        `yaml:"subject"`          // Subject to publish to
	MaxReconnects   int           `yaml:"max_reconnects"`   // Max reconnection attempts
	ReconnectWait   time.Duration `yaml:"reconnect_wait"`   // Wait time between reconnects
	Timeout         time.Duration `yaml:"timeout"`          // Connection timeout
	TLSEnabled      bool          `yaml:"tls_enabled"`      // Enable mTLS
	TLSCertFile     string        `yaml:"tls_cert_file"`    // Client certificate
	TLSKeyFile      string        `yaml:"tls_key_file"`     // Client key
	TLSCAFile       string        `yaml:"tls_ca_file"`      // CA certificate
}

// ObservabilityConfig contains metrics and logging settings
type ObservabilityConfig struct {
	// Prometheus metrics endpoint port
	MetricsPort int `yaml:"metrics_port"`

	// Enable health check endpoint
	HealthCheckEnabled bool `yaml:"health_check_enabled"`

	// Health check port
	HealthCheckPort int `yaml:"health_check_port"`
}

// LoadConfig loads configuration from YAML files.
// Loads global.yaml first, then scanner.yaml, merging the results.
//
// Args:
//   - configDir: Directory containing YAML config files
//
// Returns:
//   - *Config: Loaded and validated configuration
//   - error: Any error during loading or validation
func LoadConfig(configDir string) (*Config, error) {
	config := &Config{}

	// Load global configuration
	globalPath := fmt.Sprintf("%s/global.yaml", configDir)
	if err := loadYAMLFile(globalPath, config); err != nil {
		return nil, fmt.Errorf("failed to load global.yaml: %w", err)
	}

	// Load scanner-specific configuration
	scannerPath := fmt.Sprintf("%s/scanner.yaml", configDir)
	if err := loadYAMLFile(scannerPath, config); err != nil {
		return nil, fmt.Errorf("failed to load scanner.yaml: %w", err)
	}

	// Validate configuration
	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("configuration validation failed: %w", err)
	}

	return config, nil
}

// loadYAMLFile loads a YAML file and unmarshals it into the config struct
func loadYAMLFile(path string, config *Config) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("failed to read file %s: %w", path, err)
	}

	if err := yaml.Unmarshal(data, config); err != nil {
		return fmt.Errorf("failed to parse YAML from %s: %w", path, err)
	}

	return nil
}

// Validate checks if the configuration is valid
func (c *Config) Validate() error {
	// Validate global settings
	if c.Global.Environment == "" {
		return fmt.Errorf("global.environment is required")
	}

	// Validate scanner settings
	if len(c.Scanner.FilesystemRoots) == 0 {
		return fmt.Errorf("scanner.filesystem_roots must contain at least one path")
	}

	if c.Scanner.ScanInterval == "" {
		return fmt.Errorf("scanner.scan_interval is required")
	}

	// Parse scan interval to ensure it's valid
	if _, err := time.ParseDuration(c.Scanner.ScanInterval); err != nil {
		return fmt.Errorf("invalid scanner.scan_interval format: %w", err)
	}

	// Validate NATS settings
	if c.NATS.URL == "" {
		return fmt.Errorf("nats.url is required")
	}

	if c.NATS.Subject == "" {
		return fmt.Errorf("nats.subject is required")
	}

	// Validate mTLS settings if enabled
	if c.NATS.TLSEnabled {
		if c.NATS.TLSCertFile == "" || c.NATS.TLSKeyFile == "" || c.NATS.TLSCAFile == "" {
			return fmt.Errorf("mTLS enabled but certificate files not specified")
		}
	}

	return nil
}

// GetScanIntervalDuration returns the scan interval as a time.Duration
func (c *Config) GetScanIntervalDuration() (time.Duration, error) {
	return time.ParseDuration(c.Scanner.ScanInterval)
}

// Load is an alias for LoadConfig for compatibility
func Load(configDir string) (*Config, error) {
	return LoadConfig(configDir)
}

// Helper methods for main.go compatibility
func (c *Config) GetFilesystemRoots() []string {
	return c.Scanner.FilesystemRoots
}

func (c *Config) GetManifestPatterns() []string {
	return c.Scanner.ManifestPatterns
}

func (c *Config) GetMaxFileSize() int64 {
	return c.Scanner.MaxFileSizeBytes
}

func (c *Config) GetMaxProcesses() int {
	// Default to 1000 if not set
	if c.Scanner.MaxConcurrentScans == 0 {
		return 1000
	}
	return c.Scanner.MaxConcurrentScans
}

func (c *Config) GetNATSUrl() string {
	return c.NATS.URL
}

func (c *Config) GetMetricsPort() string {
	if c.Observability.MetricsPort == 0 {
		return ":8080"
	}
	return fmt.Sprintf(":%d", c.Observability.MetricsPort)
}

func (c *Config) GetHealthPort() string {
	if c.Observability.HealthCheckPort == 0 {
		return ":8081"
	}
	return fmt.Sprintf(":%d", c.Observability.HealthCheckPort)
}

// Flattened config for easier access
type FlatConfig struct {
	ScanInterval           time.Duration
	FilesystemRoots        []string
	ManifestPatterns       []string
	ProcessPatterns        []string
	PortPatterns           []string
	MaxFileSize            int64
	MaxProcesses           int
	NATSUrl                string
	EnableSchemaValidation bool
	MetricsPort            string
	HealthPort             string
}

// Flatten converts nested config to flat structure
func (c *Config) Flatten() (*FlatConfig, error) {
	interval, err := c.GetScanIntervalDuration()
	if err != nil {
		return nil, err
	}

	return &FlatConfig{
		ScanInterval:     interval,
		FilesystemRoots:  c.Scanner.FilesystemRoots,
		ManifestPatterns: c.Scanner.ManifestPatterns,
		ProcessPatterns: []string{
			`mcp.*server`,
			`.*mcp.*`,
			`stdio.*mcp`,
		},
		PortPatterns: []string{
			`--port[=\s]+(\d+)`,
			`-p[=\s]+(\d+)`,
		},
		MaxFileSize:            c.Scanner.MaxFileSizeBytes,
		MaxProcesses:           c.GetMaxProcesses(),
		NATSUrl:                c.NATS.URL,
		EnableSchemaValidation: true,
		MetricsPort:            c.GetMetricsPort(),
		HealthPort:             c.GetHealthPort(),
	}, nil
}
