-- Integration Test Seed Data
-- Purpose: Seed database with test registry entries for integration tests
-- Created: 2025-10-18

-- Drop existing test data (for clean re-runs)
TRUNCATE TABLE registry_entries CASCADE;

-- Registry entry #1: Approved MCP for testing registry match scenario
-- This entry will be matched by detection events in integration tests
INSERT INTO registry_entries (
    id,
    composite_id,
    name,
    vendor,
    status,
    approved_at,
    created_at,
    updated_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'testhost:3000:manifesthash123:processsig456',
    '@modelcontextprotocol/server-test',
    'test-vendor',
    'approved',
    NOW(),
    NOW(),
    NOW()
);

-- Registry entry #2: Expired entry for testing expired scenario
-- This entry has an expired_at timestamp in the past
INSERT INTO registry_entries (
    id,
    composite_id,
    name,
    vendor,
    status,
    approved_at,
    expired_at,
    created_at,
    updated_at
) VALUES (
    '650e8400-e29b-41d4-a716-446655440001',
    'testhost:4000:expiredhash789:expiredsig012',
    '@modelcontextprotocol/server-expired',
    'expired-vendor',
    'expired',
    NOW() - INTERVAL '30 days',
    NOW() - INTERVAL '1 day',
    NOW() - INTERVAL '30 days',
    NOW()
);

-- Registry entry #3: Another approved MCP for testing high-score registry match
-- Even with high detection score, this should force "authorized" classification
INSERT INTO registry_entries (
    id,
    composite_id,
    name,
    vendor,
    status,
    approved_at,
    created_at,
    updated_at
) VALUES (
    '750e8400-e29b-41d4-a716-446655440002',
    'testhost:6000:highscorehash345:highscoresig678',
    '@modelcontextprotocol/server-highscore',
    'highscore-vendor',
    'approved',
    NOW(),
    NOW(),
    NOW()
);

-- Verify seed data was inserted
SELECT
    id,
    composite_id,
    name,
    status,
    CASE
        WHEN expired_at IS NOT NULL AND expired_at < NOW() THEN 'EXPIRED'
        WHEN status = 'approved' THEN 'ACTIVE'
        ELSE status
    END as effective_status
FROM registry_entries
ORDER BY created_at;
