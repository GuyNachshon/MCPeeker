// Package filescan provides filesystem scanning for MCP manifest files.
// Reference: FR-017 (12-hour scan cycle), FR-018 (filesystem roots), US1
package filescan

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/google/uuid"
)

// Detection represents a detected MCP manifest file
type Detection struct {
	EventID      string    `json:"event_id"`
	Timestamp    time.Time `json:"timestamp"`
	HostID       string    `json:"host_id"`
	DetectionType string   `json:"detection_type"`
	Score        int       `json:"score"`
	Evidence     Evidence  `json:"evidence"`
}

// Evidence contains detailed information about the detection
type Evidence struct {
	Source    string            `json:"source"`
	FilePath  string            `json:"file_path"`
	FileHash  string            `json:"file_hash"`
	Snippet   string            `json:"snippet"`
	Port      int               `json:"port,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// Scanner scans filesystem for MCP manifest files
type Scanner struct {
	FilesystemRoots []string
	ManifestPatterns []string
	MaxFileSizeBytes int64
	HostID          string
	ScannerVersion  string
}

// NewScanner creates a new filesystem scanner
func NewScanner(roots []string, patterns []string, maxSize int64, hostID string) *Scanner {
	return &Scanner{
		FilesystemRoots: roots,
		ManifestPatterns: patterns,
		MaxFileSizeBytes: maxSize,
		HostID:          hostID,
		ScannerVersion:  "scanner-v1.0.0",
	}
}

// Scan performs a filesystem scan for MCP manifest files
func (s *Scanner) Scan() ([]*Detection, error) {
	detections := []*Detection{}

	for _, root := range s.FilesystemRoots {
		rootDetections, err := s.scanRoot(root)
		if err != nil {
			fmt.Printf("Error scanning root %s: %v\n", root, err)
			continue
		}
		detections = append(detections, rootDetections...)
	}

	return detections, nil
}

// scanRoot scans a single filesystem root
func (s *Scanner) scanRoot(root string) ([]*Detection, error) {
	detections := []*Detection{}

	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			// Skip paths that can't be accessed
			return nil
		}

		// Skip directories
		if info.IsDir() {
			return nil
		}

		// Skip files that are too large
		if info.Size() > s.MaxFileSizeBytes {
			return nil
		}

		// Check if filename matches any manifest pattern
		if s.isManifestFile(path) {
			detection, err := s.analyzeManifestFile(path, info)
			if err != nil {
				fmt.Printf("Error analyzing %s: %v\n", path, err)
				return nil
			}

			if detection != nil {
				detections = append(detections, detection)
			}
		}

		return nil
	})

	return detections, err
}

// isManifestFile checks if the file matches manifest patterns
func (s *Scanner) isManifestFile(path string) bool {
	filename := filepath.Base(path)

	for _, pattern := range s.ManifestPatterns {
		// Simple pattern matching (supports **/manifest.json style)
		if strings.Contains(pattern, "**") {
			// Extract just the filename part after **/
			parts := strings.Split(pattern, "**/")
			if len(parts) > 0 {
				expectedName := parts[len(parts)-1]
				if filename == expectedName {
					return true
				}
			}
		} else if filename == pattern {
			return true
		}
	}

	return false
}

// analyzeManifestFile analyzes a potential MCP manifest file
func (s *Scanner) analyzeManifestFile(path string, info os.FileInfo) (*Detection, error) {
	// Read file content (up to 1KB per FR-009)
	content, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	// Try to parse as JSON to validate it's a real manifest
	var manifest map[string]interface{}
	if err := json.Unmarshal(content, &manifest); err != nil {
		// Not a valid JSON file, skip
		return nil, nil
	}

	// Check if it looks like an MCP manifest (has name, version, etc.)
	if !s.looksLikeMCPManifest(manifest) {
		return nil, nil
	}

	// Extract port if present
	port := s.extractPort(manifest)

	// Generate SHA256 hash of file content
	hash := sha256.Sum256(content)
	fileHash := hex.EncodeToString(hash[:])

	// Truncate snippet to 1KB (FR-009 privacy requirement)
	snippet := string(content)
	if len(snippet) > 1024 {
		snippet = snippet[:1024]
	}

	// Calculate score (endpoint signals have highest weight per FR-003)
	score := s.calculateScore(manifest)

	// Create detection
	detection := &Detection{
		EventID:      uuid.New().String(),
		Timestamp:    time.Now().UTC(),
		HostID:       s.HostID,
		DetectionType: "file",
		Score:        score,
		Evidence: Evidence{
			Source:   s.ScannerVersion,
			FilePath: path,
			FileHash: fileHash,
			Snippet:  snippet,
			Port:     port,
			Metadata: map[string]interface{}{
				"file_size_bytes": info.Size(),
				"scan_duration_ms": 0, // Will be set by caller
			},
		},
	}

	return detection, nil
}

// looksLikeMCPManifest checks if JSON looks like an MCP manifest
func (s *Scanner) looksLikeMCPManifest(manifest map[string]interface{}) bool {
	// Check for common MCP manifest fields
	hasName := manifest["name"] != nil
	hasVersion := manifest["version"] != nil
	hasProtocol := manifest["protocol"] != nil || manifest["mcp"] != nil
	hasTools := manifest["tools"] != nil

	// At least 2 of these fields should be present
	count := 0
	if hasName {
		count++
	}
	if hasVersion {
		count++
	}
	if hasProtocol {
		count++
	}
	if hasTools {
		count++
	}

	return count >= 2
}

// extractPort extracts port from manifest if present
func (s *Scanner) extractPort(manifest map[string]interface{}) int {
	// Try common port field names
	if port, ok := manifest["port"].(float64); ok {
		return int(port)
	}
	if server, ok := manifest["server"].(map[string]interface{}); ok {
		if port, ok := server["port"].(float64); ok {
			return int(port)
		}
	}
	return 0
}

// calculateScore assigns a score based on manifest confidence
func (s *Scanner) calculateScore(manifest map[string]interface{}) int {
	// Endpoint signals have highest weight (typical: 11 per FR-003)
	baseScore := 11

	// Adjust based on confidence indicators
	if manifest["protocol"] != nil || manifest["mcp"] != nil {
		baseScore += 2 // High confidence - explicit MCP protocol
	}
	if manifest["tools"] != nil {
		baseScore += 1 // Tools array present
	}

	return baseScore
}
