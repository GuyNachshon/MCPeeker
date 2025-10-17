// Scanner service main entry point
// Reference: FR-017 (12-hour scan cycle), FR-018 (filesystem roots), US1
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

	"github.com/ozlabs/mcpeeker/backend/scanner/pkg/config"
	"github.com/ozlabs/mcpeeker/backend/scanner/pkg/filescan"
	"github.com/ozlabs/mcpeeker/backend/scanner/pkg/metrics"
	"github.com/ozlabs/mcpeeker/backend/scanner/pkg/procscan"
	"github.com/ozlabs/mcpeeker/backend/scanner/pkg/publisher"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const (
	defaultConfigPath       = "/etc/mcpeeker/config"
	defaultSchemaPath       = "/etc/mcpeeker/schemas/endpoint-event.schema.json"
	defaultScanInterval     = 12 * time.Hour
	defaultMaxFileSize      = 10 * 1024 * 1024 // 10MB
	defaultMaxProcesses     = 1000
	defaultPublishTimeout   = 5 * time.Second
	defaultMetricsPort      = ":8080"
	defaultHealthPort       = ":8081"
)

func main() {
	log.Println("Starting MCPeeker Scanner Service...")

	// Load configuration
	cfg, err := loadConfig()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Get host ID
	hostID := getHostID()
	log.Printf("Host ID: %s", hostID)

	// Create NATS publisher
	pub, err := createPublisher(cfg)
	if err != nil {
		log.Fatalf("Failed to create publisher: %v", err)
	}
	defer pub.Close()

	// Start metrics server
	go startMetricsServer(cfg.MetricsPort)

	// Start health check server
	go startHealthServer(cfg.HealthPort)

	// Create context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Setup signal handling
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	// Start scan loop
	go runScanLoop(ctx, cfg, pub, hostID)

	// Wait for shutdown signal
	<-sigChan
	log.Println("Shutdown signal received, stopping scanner...")
	cancel()

	// Give ongoing scans time to complete
	time.Sleep(5 * time.Second)
	log.Println("Scanner stopped")
}

// loadConfig loads scanner configuration
func loadConfig() (*config.FlatConfig, error) {
	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = defaultConfigPath
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		return nil, err
	}

	// Flatten config for easier access
	flatCfg, err := cfg.Flatten()
	if err != nil {
		return nil, err
	}

	// Apply defaults if not set
	if flatCfg.ScanInterval == 0 {
		flatCfg.ScanInterval = defaultScanInterval
	}
	if flatCfg.MaxFileSize == 0 {
		flatCfg.MaxFileSize = defaultMaxFileSize
	}
	if flatCfg.MaxProcesses == 0 {
		flatCfg.MaxProcesses = defaultMaxProcesses
	}
	if flatCfg.MetricsPort == "" {
		flatCfg.MetricsPort = defaultMetricsPort
	}
	if flatCfg.HealthPort == "" {
		flatCfg.HealthPort = defaultHealthPort
	}

	return flatCfg, nil
}

// getHostID retrieves or generates host ID
func getHostID() string {
	// Try to read from environment
	if hostID := os.Getenv("HOST_ID"); hostID != "" {
		return hostID
	}

	// Try to read hostname
	hostname, err := os.Hostname()
	if err != nil {
		log.Printf("Warning: failed to get hostname: %v", err)
		return "unknown-host"
	}

	return hostname
}

// createPublisher creates NATS publisher with schema validation
func createPublisher(cfg *config.FlatConfig) (*publisher.Publisher, error) {
	schemaPath := os.Getenv("SCHEMA_PATH")
	if schemaPath == "" {
		schemaPath = defaultSchemaPath
	}

	pubConfig := &publisher.Config{
		NATSUrl:          cfg.NATSUrl,
		Subject:          "endpoint.events",
		SchemaPath:       schemaPath,
		EnableValidation: cfg.EnableSchemaValidation,
		ConnectTimeout:   10 * time.Second,
		PublishTimeout:   defaultPublishTimeout,
	}

	return publisher.NewPublisher(pubConfig)
}

// runScanLoop runs the scan loop at configured interval
func runScanLoop(ctx context.Context, cfg *config.FlatConfig, pub *publisher.Publisher, hostID string) {
	// Run initial scan immediately
	runScan(ctx, cfg, pub, hostID)

	// Create ticker for periodic scans
	ticker := time.NewTicker(cfg.ScanInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			runScan(ctx, cfg, pub, hostID)
		case <-ctx.Done():
			log.Println("Scan loop stopped")
			return
		}
	}
}

// runScan performs a single scan cycle
func runScan(ctx context.Context, cfg *config.FlatConfig, pub *publisher.Publisher, hostID string) {
	log.Println("Starting scan cycle...")
	scanStart := time.Now()

	// Run file scan
	fileDetections := runFileScan(ctx, cfg, pub, hostID)

	// Run process scan
	processDetections := runProcessScan(ctx, cfg, pub, hostID)

	// Record scan metrics
	scanDuration := time.Since(scanStart)
	metrics.ScanDurationSeconds.Observe(scanDuration.Seconds())

	totalDetections := fileDetections + processDetections
	log.Printf("Scan cycle completed in %v: %d file detections, %d process detections",
		scanDuration, fileDetections, processDetections)

	// Update last scan time metric
	metrics.LastScanTimestamp.SetToCurrentTime()
}

// runFileScan runs filesystem scan
func runFileScan(ctx context.Context, cfg *config.FlatConfig, pub *publisher.Publisher, hostID string) int {
	log.Println("Running file scan...")

	// Create file scanner
	fileScanner := filescan.NewScanner(
		cfg.FilesystemRoots,
		cfg.ManifestPatterns,
		cfg.MaxFileSize,
		hostID,
	)

	// Perform scan
	detections, err := fileScanner.Scan()
	if err != nil {
		log.Printf("File scan error: %v", err)
		metrics.ErrorsTotal.WithLabelValues("file_scan").Inc()
		return 0
	}

	// Publish detections
	publishedCount := 0
	for _, detection := range detections {
		if err := pub.PublishDetection(ctx, detection); err != nil {
			log.Printf("Failed to publish file detection: %v", err)
			metrics.ErrorsTotal.WithLabelValues("publish").Inc()
			continue
		}
		publishedCount++
		metrics.EventPublishedTotal.WithLabelValues("file").Inc()
		metrics.DetectionsFoundTotal.WithLabelValues("file").Inc()
	}

	log.Printf("File scan completed: %d detections found, %d published", len(detections), publishedCount)
	return publishedCount
}

// runProcessScan runs process scan
func runProcessScan(ctx context.Context, cfg *config.FlatConfig, pub *publisher.Publisher, hostID string) int {
	log.Println("Running process scan...")

	// Create process scanner
	procScanner := procscan.NewScanner(
		cfg.ProcessPatterns,
		cfg.PortPatterns,
		cfg.MaxProcesses,
		hostID,
	)

	// Perform scan
	detections, err := procScanner.Scan()
	if err != nil {
		log.Printf("Process scan error: %v", err)
		metrics.ErrorsTotal.WithLabelValues("process_scan").Inc()
		return 0
	}

	// Publish detections
	publishedCount := 0
	for _, detection := range detections {
		if err := pub.PublishDetection(ctx, detection); err != nil {
			log.Printf("Failed to publish process detection: %v", err)
			metrics.ErrorsTotal.WithLabelValues("publish").Inc()
			continue
		}
		publishedCount++
		metrics.EventPublishedTotal.WithLabelValues("process").Inc()
		metrics.DetectionsFoundTotal.WithLabelValues("process").Inc()
	}

	log.Printf("Process scan completed: %d detections found, %d published", len(detections), publishedCount)
	return publishedCount
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
func startHealthServer(port string) {
	http.HandleFunc("/health", healthCheckHandler)
	http.HandleFunc("/ready", readinessCheckHandler)
	log.Printf("Health server listening on %s", port)
	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatalf("Health server failed: %v", err)
	}
}

// healthCheckHandler handles liveness probe
func healthCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "OK")
}

// readinessCheckHandler handles readiness probe
func readinessCheckHandler(w http.ResponseWriter, r *http.Request) {
	// Could check NATS connection, config loaded, etc.
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "Ready")
}
