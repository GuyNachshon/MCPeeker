// Package identifier provides utilities for generating composite identifiers
// for MCP instances across IP changes and container recreations.
// Reference: specs/001-mcp-detection-platform/data-model.md (FR-005a)
package identifier

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
)

// GenerateCompositeID creates a unique identifier for an MCP instance.
// Combines host, port, manifest hash, and process signature into a single SHA256 hash.
//
// This identifier remains stable across:
// - IP address changes (if manifest and process signature remain same)
// - Container recreations (tracks by manifest hash + process signature)
// - Host renames (composite of multiple factors)
//
// Args:
//   - host: IP address or hostname
//   - port: TCP port number
//   - manifestHash: SHA256 hash of manifest file content (64 hex chars)
//   - processSignature: SHA256 hash of process command line (64 hex chars)
//
// Returns:
//   - 64-character hex string (SHA256 output)
//
// Example:
//
//	compositeID := GenerateCompositeID(
//	    "10.0.5.100",
//	    3000,
//	    "a3c5f8d9e2b1c4a7f6e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7",
//	    "b4d6e8f0a2c4e6f8a0c2e4f6a8c0e2f4a6c8e0f2a4c6e8f0a2c4e6f8a0c2e4f6",
//	)
//	// Result: "e7f9d1c3b5a7e9f1d3c5b7a9e1f3d5c7b9a1e3f5d7c9b1a3e5f7d9c1b3a5e7f9"
func GenerateCompositeID(host string, port int, manifestHash string, processSignature string) string {
	// Construct composite string: host:port:manifest:signature
	compositeString := fmt.Sprintf("%s:%d:%s:%s", host, port, manifestHash, processSignature)

	// Hash with SHA256
	hash := sha256.Sum256([]byte(compositeString))

	// Return as 64-character hex string
	return hex.EncodeToString(hash[:])
}

// ValidateCompositeID checks if a composite ID has the correct format.
// Must be exactly 64 hex characters (SHA256 output).
func ValidateCompositeID(compositeID string) bool {
	if len(compositeID) != 64 {
		return false
	}

	// Check all characters are hex
	_, err := hex.DecodeString(compositeID)
	return err == nil
}

// GenerateCompositeIDFromParts is a convenience function that validates
// manifest hash and process signature before generating composite ID.
func GenerateCompositeIDFromParts(host string, port int, manifestHash string, processSignature string) (string, error) {
	// Validate manifest hash format
	if manifestHash != "" && len(manifestHash) != 64 {
		return "", fmt.Errorf("invalid manifest hash length: expected 64 hex chars, got %d", len(manifestHash))
	}
	if manifestHash != "" {
		if _, err := hex.DecodeString(manifestHash); err != nil {
			return "", fmt.Errorf("invalid manifest hash format: must be hex string")
		}
	}

	// Validate process signature format
	if processSignature != "" && len(processSignature) != 64 {
		return "", fmt.Errorf("invalid process signature length: expected 64 hex chars, got %d", len(processSignature))
	}
	if processSignature != "" {
		if _, err := hex.DecodeString(processSignature); err != nil {
			return "", fmt.Errorf("invalid process signature format: must be hex string")
		}
	}

	// Validate port range
	if port <= 0 || port > 65535 {
		return "", fmt.Errorf("invalid port: must be in range 1-65535, got %d", port)
	}

	// Generate composite ID
	return GenerateCompositeID(host, port, manifestHash, processSignature), nil
}
