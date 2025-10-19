package engine

import (
	"context"

	"github.com/stretchr/testify/mock"
)

// MockRegistryClient implements the registry client interface for testing
type MockRegistryClient struct {
	mock.Mock
}

// TestDetection represents a detection used in unit tests
type TestDetection struct {
	CompositeID            string
	HostIDHash             string
	Evidence               []TestEvidence
	Score                  int
	Classification         string
	RegistryMatched        bool
	RegistryPenalty        int
	ExpectedScore          int
	ExpectedClassification string
}

// TestEvidence represents evidence used in unit tests
type TestEvidence struct {
	Type              string // "endpoint", "network", "gateway", "process", "judge", "registry"
	ScoreContribution int
	Details           map[string]interface{}
}

// MockRegistryResponse represents a mock response from the registry API
type MockRegistryResponse struct {
	Matched bool
	EntryID string // Optional: UUID of matched entry
	Expired bool   // For testing expired entries
	Error   error  // For testing error scenarios
}

// Test fixtures for different scenarios
var (
	// DetectionWithRegistryMatch: Detection with registry match (should be "authorized")
	DetectionWithRegistryMatch = &TestDetection{
		CompositeID: "host123:3000:abc123:sig456",
		HostIDHash:  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
		Evidence: []TestEvidence{
			{Type: "endpoint", ScoreContribution: 11},
		},
		RegistryMatched:        true,
		RegistryPenalty:        -6,
		ExpectedScore:          5, // 11 - 6
		ExpectedClassification: "authorized",
	}

	// HighScoreUnauthorized: High-score detection without registry match
	HighScoreUnauthorized = &TestDetection{
		CompositeID: "host456:4000:def789:sig789",
		HostIDHash:  "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
		Evidence: []TestEvidence{
			{Type: "endpoint", ScoreContribution: 13},
			{Type: "network", ScoreContribution: 3},
			{Type: "judge", ScoreContribution: 5},
		},
		RegistryMatched:        false,
		ExpectedScore:          21,
		ExpectedClassification: "unauthorized",
	}

	// LowScoreAuthorized: Low-score detection (should be "authorized")
	LowScoreAuthorized = &TestDetection{
		CompositeID: "host789:5000:ghi012:sig012",
		HostIDHash:  "8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92",
		Evidence: []TestEvidence{
			{Type: "endpoint", ScoreContribution: 3},
		},
		RegistryMatched:        false,
		ExpectedScore:          3,
		ExpectedClassification: "authorized",
	}

	// HighScoreWithRegistryMatch: High score but registry match forces "authorized"
	HighScoreWithRegistryMatch = &TestDetection{
		CompositeID: "host999:6000:jkl345:sig345",
		HostIDHash:  "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
		Evidence: []TestEvidence{
			{Type: "endpoint", ScoreContribution: 15},
			{Type: "network", ScoreContribution: 5},
		},
		RegistryMatched:        true,
		RegistryPenalty:        -6,
		ExpectedScore:          14, // 20 - 6
		ExpectedClassification: "authorized",
	}
)

// Mock registry responses
var (
	// RegistryMatch: approved MCP
	RegistryMatch = &MockRegistryResponse{
		Matched: true,
		EntryID: "550e8400-e29b-41d4-a716-446655440000",
		Expired: false,
	}

	// RegistryNoMatch: no registry match
	RegistryNoMatch = &MockRegistryResponse{
		Matched: false,
	}

	// RegistryExpired: expired registry entry
	RegistryExpired = &MockRegistryResponse{
		Matched: false,
		Expired: true,
	}
)

// GetTestDetection returns a test detection by scenario name
func GetTestDetection(scenario string) *TestDetection {
	switch scenario {
	case "registry_match":
		return DetectionWithRegistryMatch
	case "high_score":
		return HighScoreUnauthorized
	case "low_score":
		return LowScoreAuthorized
	case "high_score_with_match":
		return HighScoreWithRegistryMatch
	default:
		panic("unknown test scenario: " + scenario)
	}
}

// CheckMatch mocks the registry client's CheckMatch method
func (m *MockRegistryClient) CheckMatch(ctx context.Context, compositeID string) (*MockRegistryResponse, error) {
	args := m.Called(ctx, compositeID)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*MockRegistryResponse), args.Error(1)
}
