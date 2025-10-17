// Package identifier provides host ID hashing utilities for privacy compliance.
// Reference: FR-008 - Host identifiers must be hashed before storage
package identifier

import (
	"crypto/sha256"
	"encoding/hex"
)

// HashHostID hashes a host identifier using SHA256 for privacy compliance.
// Per FR-008, host identifiers must be hashed before storage in ClickHouse.
//
// Args:
//   - hostID: Original host identifier (IP, hostname, container ID, etc.)
//
// Returns:
//   - 64-character hex string (SHA256 hash)
//
// Example:
//
//	hashedID := HashHostID("workstation-42.corp.example.com")
//	// Store hashedID in ClickHouse detections.host_id_hash
//
// Privacy Note:
//   - Original host_id is NEVER stored in analytics database
//   - Hash is one-way: cannot reverse to get original identifier
//   - Same host_id always produces same hash (for correlation)
func HashHostID(hostID string) string {
	hash := sha256.Sum256([]byte(hostID))
	return hex.EncodeToString(hash[:])
}

// ValidateHashFormat checks if a hash has the correct format.
// Must be exactly 64 hex characters (SHA256 output).
func ValidateHashFormat(hash string) bool {
	if len(hash) != 64 {
		return false
	}

	// Check all characters are hex
	_, err := hex.DecodeString(hash)
	return err == nil
}

// BatchHashHostIDs hashes multiple host identifiers in a single call.
// Useful for bulk processing or batch operations.
//
// Args:
//   - hostIDs: Slice of original host identifiers
//
// Returns:
//   - Slice of hashed identifiers in same order as input
func BatchHashHostIDs(hostIDs []string) []string {
	hashed := make([]string, len(hostIDs))
	for i, hostID := range hostIDs {
		hashed[i] = HashHostID(hostID)
	}
	return hashed
}
