// Package config provides YAML configuration loading for the correlator service.
// Reference: FR-015 (declarative YAML configuration), FR-016 (JSON Schema validation)
package config

import (
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// Config represents the correlator service configuration
type Config struct {
	Global      GlobalConfig      `yaml:"global"`
	Correlator  CorrelatorConfig  `yaml:"correlator"`
	NATS        NATSConfig        `yaml:"nats"`
	ClickHouse  ClickHouseConfig  `yaml:"clickhouse"`
	PostgreSQL  PostgreSQLConfig  `yaml:"postgresql"`
	Observability ObservabilityConfig `yaml:"observability"`
}

// GlobalConfig contains settings shared across all services
type GlobalConfig struct {
	Environment string `yaml:"environment"`
	LogLevel    string `yaml:"log_level"`
	Version     string `yaml:"version"`
}

// CorrelatorConfig contains correlator-specific settings
type CorrelatorConfig struct {
	// Deduplication window in seconds (default: 300 = 5 minutes per FR-002a)
	DedupWindowSeconds int `yaml:"dedup_window_seconds"`

	// Scoring weights for multi-layer correlation (FR-003)
	ScoringWeights ScoringWeights `yaml:"scoring_weights"`

	// Registry penalty for authorized MCPs (FR-005)
	RegistryPenalty int `yaml:"registry_penalty"`

	// Max concurrent event processing workers
	MaxWorkers int `yaml:"max_workers"`

	// Batch size for ClickHouse inserts
	BatchSize int `yaml:"batch_size"`

	// Batch timeout for ClickHouse inserts
	BatchTimeout string `yaml:"batch_timeout"`
}

// ScoringWeights defines weights for different signal types
type ScoringWeights struct {
	Endpoint int `yaml:"endpoint"` // Highest weight (typical: 11)
	Judge    int `yaml:"judge"`    // Medium weight (typical: 5)
	Network  int `yaml:"network"`  // Supporting weight (typical: 3)
}

// NATSConfig contains NATS JetStream connection settings
type NATSConfig struct {
	URL             string        `yaml:"url"`
	ConsumerGroup   string        `yaml:"consumer_group"`
	MaxReconnects   int           `yaml:"max_reconnects"`
	ReconnectWait   time.Duration `yaml:"reconnect_wait"`
	Timeout         time.Duration `yaml:"timeout"`
	TLSEnabled      bool          `yaml:"tls_enabled"`
	TLSCertFile     string        `yaml:"tls_cert_file"`
	TLSKeyFile      string        `yaml:"tls_key_file"`
	TLSCAFile       string        `yaml:"tls_ca_file"`
}

// ClickHouseConfig contains ClickHouse connection settings
type ClickHouseConfig struct {
	Host            string        `yaml:"host"`
	Port            int           `yaml:"port"`
	Database        string        `yaml:"database"`
	Username        string        `yaml:"username"`
	Password        string        `yaml:"password"`
	MaxOpenConns    int           `yaml:"max_open_conns"`
	MaxIdleConns    int           `yaml:"max_idle_conns"`
	ConnMaxLifetime time.Duration `yaml:"conn_max_lifetime"`
	TLSEnabled      bool          `yaml:"tls_enabled"`
	TLSCertFile     string        `yaml:"tls_cert_file"`
	TLSKeyFile      string        `yaml:"tls_key_file"`
	TLSCAFile       string        `yaml:"tls_ca_file"`
}

// PostgreSQLConfig contains PostgreSQL connection settings
type PostgreSQLConfig struct {
	Host            string        `yaml:"host"`
	Port            int           `yaml:"port"`
	Database        string        `yaml:"database"`
	Username        string        `yaml:"username"`
	Password        string        `yaml:"password"`
	SSLMode         string        `yaml:"ssl_mode"`
	MaxOpenConns    int           `yaml:"max_open_conns"`
	MaxIdleConns    int           `yaml:"max_idle_conns"`
	ConnMaxLifetime time.Duration `yaml:"conn_max_lifetime"`
}

// ObservabilityConfig contains metrics and logging settings
type ObservabilityConfig struct {
	MetricsPort        int  `yaml:"metrics_port"`
	HealthCheckEnabled bool `yaml:"health_check_enabled"`
	HealthCheckPort    int  `yaml:"health_check_port"`
}

// LoadConfig loads configuration from YAML files
func LoadConfig(configDir string) (*Config, error) {
	config := &Config{}

	// Load global configuration
	globalPath := fmt.Sprintf("%s/global.yaml", configDir)
	if err := loadYAMLFile(globalPath, config); err != nil {
		return nil, fmt.Errorf("failed to load global.yaml: %w", err)
	}

	// Load correlator-specific configuration
	correlatorPath := fmt.Sprintf("%s/correlator.yaml", configDir)
	if err := loadYAMLFile(correlatorPath, config); err != nil {
		return nil, fmt.Errorf("failed to load correlator.yaml: %w", err)
	}

	// Validate configuration
	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("configuration validation failed: %w", err)
	}

	return config, nil
}

// loadYAMLFile loads a YAML file
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
	if c.Global.Environment == "" {
		return fmt.Errorf("global.environment is required")
	}

	if c.Correlator.DedupWindowSeconds <= 0 {
		return fmt.Errorf("correlator.dedup_window_seconds must be positive")
	}

	if c.Correlator.ScoringWeights.Endpoint <= 0 {
		return fmt.Errorf("correlator.scoring_weights.endpoint must be positive")
	}

	if c.NATS.URL == "" {
		return fmt.Errorf("nats.url is required")
	}

	if c.ClickHouse.Host == "" {
		return fmt.Errorf("clickhouse.host is required")
	}

	if c.PostgreSQL.Host == "" {
		return fmt.Errorf("postgresql.host is required")
	}

	return nil
}

// GetBatchTimeoutDuration returns the batch timeout as a time.Duration
func (c *Config) GetBatchTimeoutDuration() (time.Duration, error) {
	return time.ParseDuration(c.Correlator.BatchTimeout)
}

// Helper methods for main.go compatibility
func (c *Config) GetDedupWindow() time.Duration {
	return time.Duration(c.Correlator.DedupWindowSeconds) * time.Second
}

func (c *Config) GetClickHouseDSN() string {
	return fmt.Sprintf("tcp://%s:%d?database=%s&username=%s&password=%s",
		c.ClickHouse.Host,
		c.ClickHouse.Port,
		c.ClickHouse.Database,
		c.ClickHouse.Username,
		c.ClickHouse.Password,
	)
}

func (c *Config) GetNATSUrl() string {
	return c.NATS.URL
}

func (c *Config) GetRegistryAPIURL() string {
	// TODO: Make this configurable
	return "http://registry-api:8000"
}

func (c *Config) GetRegistryAuthToken() string {
	// TODO: Make this configurable
	return os.Getenv("REGISTRY_AUTH_TOKEN")
}

func (c *Config) GetMetricsPort() string {
	return fmt.Sprintf(":%d", c.Observability.MetricsPort)
}

func (c *Config) GetHealthPort() string {
	return fmt.Sprintf(":%d", c.Observability.HealthCheckPort)
}

// Flattened config structure for easier access
type FlatConfig struct {
	DedupWindow            time.Duration
	WeightEndpoint         int
	WeightJudge            int
	WeightNetwork          int
	RegistryPenalty        int
	ThresholdAuthorized    int
	ThresholdSuspect       int
	ThresholdUnauthorized  int
	ClickHouseURL          string
	ClickHouseDSN          string
	NATSUrl                string
	RegistryAPIURL         string
	RegistryAuthToken      string
	MetricsPort            string
	HealthPort             string
}

// Flatten converts nested config to flat structure
func (c *Config) Flatten() *FlatConfig {
	return &FlatConfig{
		DedupWindow:            c.GetDedupWindow(),
		WeightEndpoint:         c.Correlator.ScoringWeights.Endpoint,
		WeightJudge:            c.Correlator.ScoringWeights.Judge,
		WeightNetwork:          c.Correlator.ScoringWeights.Network,
		RegistryPenalty:        c.Correlator.RegistryPenalty,
		ThresholdAuthorized:    4,  // Default thresholds per FR-003
		ThresholdSuspect:       8,
		ThresholdUnauthorized:  9,
		ClickHouseURL:          fmt.Sprintf("http://%s:%d", c.ClickHouse.Host, c.ClickHouse.Port),
		ClickHouseDSN:          c.GetClickHouseDSN(),
		NATSUrl:                c.GetNATSUrl(),
		RegistryAPIURL:         c.GetRegistryAPIURL(),
		RegistryAuthToken:      c.GetRegistryAuthToken(),
		MetricsPort:            c.GetMetricsPort(),
		HealthPort:             c.GetHealthPort(),
	}
}

// Load is an alias for LoadConfig
func Load(configDir string) (*FlatConfig, error) {
	cfg, err := LoadConfig(configDir)
	if err != nil {
		return nil, err
	}
	return cfg.Flatten(), nil
}
