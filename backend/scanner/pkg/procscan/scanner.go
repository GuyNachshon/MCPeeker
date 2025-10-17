// Package procscan provides process scanning for MCP server processes.
// Reference: FR-017 (12-hour scan cycle), FR-018 (process detection), US1
package procscan

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/shirou/gopsutil/v3/process"
)

// Detection represents a detected MCP server process
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
	ProcessID int32             `json:"process_id"`
	ProcessName string          `json:"process_name"`
	CommandLine string          `json:"command_line"`
	BinaryPath  string          `json:"binary_path"`
	ProcessHash string          `json:"process_hash"`
	Port        int               `json:"port,omitempty"`
	Snippet     string            `json:"snippet"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// Scanner scans running processes for MCP servers
type Scanner struct {
	MCPPatterns     []string
	PortPatterns    []string
	MaxProcesses    int
	HostID          string
	ScannerVersion  string
}

// NewScanner creates a new process scanner
func NewScanner(patterns []string, portPatterns []string, maxProcs int, hostID string) *Scanner {
	return &Scanner{
		MCPPatterns:    patterns,
		PortPatterns:   portPatterns,
		MaxProcesses:   maxProcs,
		HostID:         hostID,
		ScannerVersion: "scanner-v1.0.0",
	}
}

// Scan performs a process scan for MCP server processes
func (s *Scanner) Scan() ([]*Detection, error) {
	detections := []*Detection{}

	// Get all running processes
	processes, err := process.Processes()
	if err != nil {
		return nil, fmt.Errorf("failed to list processes: %w", err)
	}

	// Scan each process
	for _, proc := range processes {
		if len(detections) >= s.MaxProcesses {
			break
		}

		detection, err := s.analyzeProcess(proc)
		if err != nil {
			// Skip processes we can't access
			continue
		}

		if detection != nil {
			detections = append(detections, detection)
		}
	}

	return detections, nil
}

// analyzeProcess analyzes a single process to determine if it's an MCP server
func (s *Scanner) analyzeProcess(proc *process.Process) (*Detection, error) {
	// Get process name
	name, err := proc.Name()
	if err != nil {
		return nil, err
	}

	// Get command line arguments
	cmdline, err := proc.Cmdline()
	if err != nil {
		return nil, err
	}

	// Get executable path
	exe, err := proc.Exe()
	if err != nil {
		// Some processes don't allow exe access, use name instead
		exe = name
	}

	// Check if this looks like an MCP server
	if !s.looksLikeMCPServer(name, cmdline) {
		return nil, nil
	}

	// Extract port from command line
	port := s.extractPort(cmdline)

	// Generate process signature hash
	processHash := s.generateProcessHash(exe, cmdline)

	// Create snippet (≤1KB for privacy per FR-009)
	snippet := s.createSnippet(name, cmdline)
	if len(snippet) > 1024 {
		snippet = snippet[:1024]
	}

	// Calculate score
	score := s.calculateScore(name, cmdline, port)

	// Get process metadata
	pid := proc.Pid
	createTime, _ := proc.CreateTime()
	username, _ := proc.Username()

	// Create detection
	detection := &Detection{
		EventID:      uuid.New().String(),
		Timestamp:    time.Now().UTC(),
		HostID:       s.HostID,
		DetectionType: "process",
		Score:        score,
		Evidence: Evidence{
			Source:      s.ScannerVersion,
			ProcessID:   pid,
			ProcessName: name,
			CommandLine: cmdline,
			BinaryPath:  exe,
			ProcessHash: processHash,
			Port:        port,
			Snippet:     snippet,
			Metadata: map[string]interface{}{
				"create_time_unix": createTime,
				"username":         username,
			},
		},
	}

	return detection, nil
}

// looksLikeMCPServer checks if process looks like an MCP server
func (s *Scanner) looksLikeMCPServer(name string, cmdline string) bool {
	// Convert to lowercase for case-insensitive matching
	nameLower := strings.ToLower(name)
	cmdlineLower := strings.ToLower(cmdline)

	// Check against MCP patterns
	for _, pattern := range s.MCPPatterns {
		matched, _ := regexp.MatchString(pattern, nameLower)
		if matched {
			return true
		}
		matched, _ = regexp.MatchString(pattern, cmdlineLower)
		if matched {
			return true
		}
	}

	// Common MCP server indicators
	indicators := []string{
		"mcp-server",
		"mcp_server",
		"mcpserver",
		"--mcp",
		"stdio-mcp",
		"sse-mcp",
		"websocket-mcp",
		"--protocol=mcp",
		"--mode=mcp",
	}

	for _, indicator := range indicators {
		if strings.Contains(nameLower, indicator) || strings.Contains(cmdlineLower, indicator) {
			return true
		}
	}

	// Check for common MCP server languages with MCP-related args
	if (strings.Contains(nameLower, "node") || strings.Contains(nameLower, "python") ||
	    strings.Contains(nameLower, "go") || strings.Contains(nameLower, "java")) {
		mcpKeywords := []string{"mcp", "model-context-protocol", "anthropic"}
		for _, keyword := range mcpKeywords {
			if strings.Contains(cmdlineLower, keyword) {
				return true
			}
		}
	}

	return false
}

// extractPort extracts port number from command line arguments
func (s *Scanner) extractPort(cmdline string) int {
	// Try port patterns first
	for _, pattern := range s.PortPatterns {
		re := regexp.MustCompile(pattern)
		matches := re.FindStringSubmatch(cmdline)
		if len(matches) > 1 {
			port, err := strconv.Atoi(matches[1])
			if err == nil && port > 0 && port < 65536 {
				return port
			}
		}
	}

	// Common port argument patterns
	commonPatterns := []string{
		`--port[=\s]+(\d+)`,
		`-p[=\s]+(\d+)`,
		`--listen[=\s]+:(\d+)`,
		`--bind[=\s]+:(\d+)`,
		`--address[=\s]+:\d+\.\d+\.\d+\.\d+:(\d+)`,
		`:(\d{4,5})\b`, // Standalone port numbers (4-5 digits)
	}

	for _, pattern := range commonPatterns {
		re := regexp.MustCompile(pattern)
		matches := re.FindStringSubmatch(cmdline)
		if len(matches) > 1 {
			port, err := strconv.Atoi(matches[1])
			if err == nil && port > 0 && port < 65536 {
				return port
			}
		}
	}

	return 0 // Port not found
}

// generateProcessHash creates a unique hash for the process
func (s *Scanner) generateProcessHash(binaryPath string, cmdline string) string {
	// Combine binary path and command line for unique signature
	signature := fmt.Sprintf("%s|%s", binaryPath, cmdline)
	hash := sha256.Sum256([]byte(signature))
	return hex.EncodeToString(hash[:])
}

// createSnippet creates a JSON snippet of process information
func (s *Scanner) createSnippet(name string, cmdline string) string {
	snippet := map[string]interface{}{
		"process_name": name,
		"command_line": cmdline,
		"detection_method": "process_scan",
	}

	data, err := json.Marshal(snippet)
	if err != nil {
		return fmt.Sprintf(`{"process_name":"%s","error":"marshaling failed"}`, name)
	}

	return string(data)
}

// calculateScore assigns a score based on process confidence
func (s *Scanner) calculateScore(name string, cmdline string, port int) int {
	// Endpoint signals have highest weight (typical: 11 per FR-003)
	baseScore := 11

	nameLower := strings.ToLower(name)
	cmdlineLower := strings.ToLower(cmdline)

	// High confidence indicators
	if strings.Contains(nameLower, "mcp-server") || strings.Contains(cmdlineLower, "--mcp") {
		baseScore += 2
	}

	// Port found increases confidence
	if port > 0 {
		baseScore += 1
	}

	// Protocol-specific transport modes
	if strings.Contains(cmdlineLower, "stdio") ||
	   strings.Contains(cmdlineLower, "sse") ||
	   strings.Contains(cmdlineLower, "websocket") {
		baseScore += 1
	}

	return baseScore
}
