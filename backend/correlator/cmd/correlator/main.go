// Correlator service main entry point
// Reference: FR-002 (Multi-layer detection), FR-003 (Weighted scoring), US4
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/clickhouse"
	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/config"
	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/consumer"
	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/engine"
	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/metrics"
	"github.com/ozlabs/mcpeeker/backend/correlator/pkg/registry"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const (
	defaultConfigPath  = "/etc/mcpeeker/config"
	defaultMetricsPort = ":8080"
	defaultHealthPort  = ":8081"
)

func main() {
	log.Println("Starting MCPeeker Correlator Service...")

	// Load configuration
	cfg, err := loadConfig()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Create registry client
	registryClient, err := createRegistryClient(cfg)
	if err != nil {
		log.Fatalf("Failed to create registry client: %v", err)
	}

	// Create correlator engine
	correlator := engine.NewCorrelator(
		cfg.DedupWindow,
		registryClient,
		cfg.ClickHouseURL,
		engine.ScoringWeights{
			Endpoint: cfg.WeightEndpoint,
			Judge:    cfg.WeightJudge,
			Network:  cfg.WeightNetwork,
			Registry: cfg.RegistryPenalty,
		},
		engine.ClassificationThresholds{
			Authorized:   cfg.ThresholdAuthorized,
			Suspect:      cfg.ThresholdSuspect,
			Unauthorized: cfg.ThresholdUnauthorized,
		},
	)

	// Create ClickHouse writer
	chWriter, err := clickhouse.NewWriter(&clickhouse.Config{
		DSN:             cfg.ClickHouseDSN,
		MaxOpenConns:    20,
		MaxIdleConns:    10,
		ConnMaxLifetime: 30 * time.Minute,
	})
	if err != nil {
		log.Fatalf("Failed to create ClickHouse writer: %v", err)
	}
	defer chWriter.Close()

	// Test ClickHouse connection
	ctx := context.Background()
	if err := chWriter.HealthCheck(ctx); err != nil {
		log.Fatalf("ClickHouse health check failed: %v", err)
	}
	log.Println("✓ ClickHouse connection established")

	// Create NATS consumer
	natsConsumer, err := consumer.NewConsumer(
		&consumer.Config{
			NATSUrl:    cfg.NATSUrl,
			Subjects:   []string{"endpoint.events", "network.events", "gateway.events"},
			StreamName: "detections",
			DurableName: "correlator",
			BatchSize:  10,
		},
		correlator,
		chWriter,
	)
	if err != nil {
		log.Fatalf("Failed to create NATS consumer: %v", err)
	}
	defer natsConsumer.Close()

	// Start metrics server
	go startMetricsServer(cfg.MetricsPort)

	// Start health check server
	go startHealthServer(cfg.HealthPort, natsConsumer, chWriter)

	// Start cleanup routine for expired detections
	go startCleanupRoutine(ctx, correlator)

	// Create context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Setup signal handling
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	// Start consumer
	go func() {
		if err := natsConsumer.Start(ctx); err != nil {
			log.Printf("Consumer error: %v", err)
		}
	}()

	log.Println("✓ Correlator service started successfully")

	// Wait for shutdown signal
	<-sigChan
	log.Println("Shutdown signal received, stopping correlator...")
	cancel()

	// Give ongoing operations time to complete
	time.Sleep(5 * time.Second)
	log.Println("Correlator stopped")
}

// loadConfig loads correlator configuration
func loadConfig() (*config.Config, error) {
	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = defaultConfigPath
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		return nil, err
	}

	// Apply defaults
	if cfg.MetricsPort == "" {
		cfg.MetricsPort = defaultMetricsPort
	}
	if cfg.HealthPort == "" {
		cfg.HealthPort = defaultHealthPort
	}
	if cfg.DedupWindow == 0 {
		cfg.DedupWindow = 5 * time.Minute // FR-002a default
	}

	return cfg, nil
}

// createRegistryClient creates a registry API client
func createRegistryClient(cfg *config.Config) (*registry.Client, error) {
	return registry.NewClient(&registry.Config{
		BaseURL:   cfg.RegistryAPIURL,
		AuthToken: cfg.RegistryAuthToken,
		Timeout:   10 * time.Second,
		TLSConfig: nil, // TODO: Add mTLS config if needed
	})
}

// startMetricsServer starts Prometheus metrics HTTP server
func startMetricsServer(port string) {
	http.Handle("/metrics", promhttp.Handler())
	log.Printf("Metrics server listening on %s", port)
	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Metrics server failed: %v", err)
	}
}

// startHealthServer starts health check HTTP server
func startHealthServer(port string, natsConsumer *consumer.Consumer, chWriter *clickhouse.Writer) {
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "OK")
	})

	http.HandleFunc("/ready", func(w http.ResponseWriter, r *http.Request) {
		// Check ClickHouse
		ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
		defer cancel()

		if err := chWriter.HealthCheck(ctx); err != nil {
			http.Error(w, "ClickHouse unhealthy", http.StatusServiceUnavailable)
			return
		}

		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "Ready")
	})

	http.HandleFunc("/stats", func(w http.ResponseWriter, r *http.Request) {
		stats := natsConsumer.GetStats()
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"stats": %v}`, stats)
	})

	log.Printf("Health server listening on %s", port)
	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Health server failed: %v", err)
	}
}

// startCleanupRoutine periodically cleans up expired detections from the correlation window
func startCleanupRoutine(ctx context.Context, correlator *engine.Correlator) {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			removed := correlator.CleanupExpired()
			if removed > 0 {
				log.Printf("Cleaned up %d expired detections from correlation window", removed)
				metrics.DeduplicationMatchesTotal.Add(float64(removed))
			}
		}
	}
}
