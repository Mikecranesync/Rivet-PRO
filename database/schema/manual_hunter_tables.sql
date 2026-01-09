-- ============================================================================
-- Manual Hunter Database Schema
-- ============================================================================
-- Purpose: PostgreSQL schema for Manual Hunter n8n workflow
--          - manuals: Caching layer for discovered OEM documentation
--          - manual_requests: Priority queue for missing manual acquisition
--
-- Integration: Hybrid approach - new tables with FK to rivet_users.id
-- File Storage: Cloud URLs only (S3/GCS/CDN)
-- Priority: Weighted formula (request_count * 10 + (6 - priority_level))
--
-- Author: Agent 1 - Database Schema
-- Date: 2026-01-09
-- ============================================================================

-- ============================================================================
-- 1. TEST USER SETUP (if rivet_users doesn't exist or needs test data)
-- ============================================================================

-- Create rivet_users table if it doesn't exist (minimal version for testing)
CREATE TABLE IF NOT EXISTS rivet_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(255),
    telegram_first_name VARCHAR(255),
    telegram_last_name VARCHAR(255),
    is_pro BOOLEAN DEFAULT FALSE,
    tier VARCHAR(50) DEFAULT 'free',
    lookup_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP
);

-- Create test user if doesn't exist
INSERT INTO rivet_users (
    id,
    telegram_id,
    telegram_username,
    telegram_first_name,
    is_pro,
    tier
)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    123456789,
    'test_technician',
    'Test User',
    true,
    'pro'
)
ON CONFLICT (telegram_id) DO NOTHING;

-- ============================================================================
-- 2. MANUALS TABLE (Caching Layer)
-- ============================================================================

CREATE TABLE IF NOT EXISTS manuals (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Manual Metadata
    title VARCHAR(500) NOT NULL,
    manufacturer VARCHAR(255) NOT NULL,
    model_number VARCHAR(255),
    component_type VARCHAR(100),

    -- File Storage (Cloud URLs only)
    file_url VARCHAR(1000) NOT NULL,

    -- Search Metadata
    source VARCHAR(100) NOT NULL, -- 'tavily', 'groq', 'serper', 'deepseek', 'perplexity', 'user_upload'
    search_tier INTEGER,          -- 1=Tavily, 2=Groq+Serper, 3=DeepSeek
    confidence_score DECIMAL(5,2), -- 0.00-100.00

    -- Document Properties
    page_count INTEGER,
    file_size_kb INTEGER,
    language VARCHAR(10) DEFAULT 'en',

    -- Quality & Attribution
    is_verified BOOLEAN DEFAULT FALSE,
    uploaded_by_user_id UUID,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed_at TIMESTAMP,
    access_count INTEGER DEFAULT 0,

    -- Foreign Keys
    CONSTRAINT fk_manuals_user
        FOREIGN KEY (uploaded_by_user_id)
        REFERENCES rivet_users(id)
        ON DELETE SET NULL,

    -- Unique Constraints (prevent duplicate URLs)
    CONSTRAINT unique_manual_url
        UNIQUE (manufacturer, model_number, file_url)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_manuals_manufacturer ON manuals(manufacturer);
CREATE INDEX IF NOT EXISTS idx_manuals_model ON manuals(model_number);
CREATE INDEX IF NOT EXISTS idx_manuals_type ON manuals(component_type);
CREATE INDEX IF NOT EXISTS idx_manuals_source_tier ON manuals(source, search_tier);
CREATE INDEX IF NOT EXISTS idx_manuals_verified ON manuals(is_verified);

-- Table comments
COMMENT ON TABLE manuals IS 'Caching layer for discovered/uploaded OEM equipment manuals';
COMMENT ON COLUMN manuals.search_tier IS 'Search tier that found this manual: 1=Tavily, 2=Groq+Serper, 3=DeepSeek';
COMMENT ON COLUMN manuals.confidence_score IS 'Relevance score from search API (0-100)';
COMMENT ON COLUMN manuals.file_url IS 'Public cloud URL (S3/GCS/CDN) for PDF access';

-- ============================================================================
-- 3. MANUAL REQUESTS TABLE (Priority Queue)
-- ============================================================================

CREATE TABLE IF NOT EXISTS manual_requests (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User Info
    user_id UUID NOT NULL,
    telegram_chat_id BIGINT NOT NULL,

    -- Request Details
    manufacturer VARCHAR(255) NOT NULL,
    model_number VARCHAR(255),
    component_type VARCHAR(100),
    search_query TEXT NOT NULL,

    -- Priority Management
    request_count INTEGER DEFAULT 1,
    priority_level INTEGER DEFAULT 3, -- 1=Critical, 2=High, 3=Normal, 4=Low, 5=Backlog
    calculated_priority INTEGER GENERATED ALWAYS AS (request_count * 10 + (6 - priority_level)) STORED,

    -- Status Tracking
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'resolved', 'failed'
    resolved_manual_id UUID,
    failed_tiers TEXT[],
    notes TEXT,

    -- Timestamps
    first_requested_at TIMESTAMP DEFAULT NOW(),
    last_requested_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    notified_at TIMESTAMP,

    -- Foreign Keys
    CONSTRAINT fk_requests_user
        FOREIGN KEY (user_id)
        REFERENCES rivet_users(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_requests_manual
        FOREIGN KEY (resolved_manual_id)
        REFERENCES manuals(id)
        ON DELETE SET NULL,

    -- Constraints
    CONSTRAINT check_priority_level
        CHECK (priority_level BETWEEN 1 AND 5),

    CONSTRAINT check_status
        CHECK (status IN ('pending', 'in_progress', 'resolved', 'failed'))
);

-- Unique constraint: Only one pending request per manufacturer/model
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_pending_request
    ON manual_requests(manufacturer, model_number)
    WHERE status = 'pending';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_requests_status ON manual_requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_priority ON manual_requests(status, calculated_priority DESC, last_requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_requests_user ON manual_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_mfr_model ON manual_requests(manufacturer, model_number);

-- Table comments
COMMENT ON TABLE manual_requests IS 'Priority queue for manual acquisition requests';
COMMENT ON COLUMN manual_requests.calculated_priority IS 'Auto-calculated: (request_count * 10) + (6 - priority_level). Higher = more urgent.';
COMMENT ON COLUMN manual_requests.failed_tiers IS 'Array of search tier names that failed to find this manual';

-- ============================================================================
-- 4. SEED DATA - MANUALS
-- ============================================================================

-- Get test user ID for seed data
DO $$
DECLARE
    test_user_id UUID := '00000000-0000-0000-0000-000000000001';
BEGIN
    -- Manual 1: Allen-Bradley PowerFlex 525 VFD
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'Allen-Bradley PowerFlex 525 User Manual',
        'Allen-Bradley',
        'PowerFlex 525',
        'VFD',
        'https://cdn.rockwellautomation.com/manuals/powerflex525.pdf',
        'tavily',
        1,
        95.00,
        test_user_id,
        342,
        4850
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 2: Siemens S7-1200 PLC
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'Siemens S7-1200 Programmable Controller System Manual',
        'Siemens',
        'S7-1200',
        'PLC',
        'https://siemens.com/manuals/s7-1200-system-manual.pdf',
        'tavily',
        1,
        92.00,
        test_user_id,
        1268,
        8920
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 3: Schneider Altivar 320 VFD
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'Schneider Electric Altivar 320 Variable Speed Drive Manual',
        'Schneider Electric',
        'Altivar 320',
        'VFD',
        'https://schneider.com/docs/altivar320-manual.pdf',
        'groq',
        2,
        88.00,
        test_user_id,
        256,
        3450
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 4: ABB ACH580 VFD
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'ABB ACH580 General Purpose Drive User Manual',
        'ABB',
        'ACH580',
        'VFD',
        'https://abb.com/manuals/ach580-user-manual.pdf',
        'tavily',
        1,
        90.00,
        test_user_id,
        428,
        5670
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 5: Mitsubishi FR-D700 VFD
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'Mitsubishi FR-D700 SC Compact Inverter Instruction Manual',
        'Mitsubishi',
        'FR-D700',
        'VFD',
        'https://mitsubishielectric.com/manuals/fr-d700.pdf',
        'serper',
        2,
        85.00,
        test_user_id,
        312,
        4120
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 6: Yaskawa V1000 VFD
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'Yaskawa V1000 Compact Vector Drive Technical Manual',
        'Yaskawa',
        'V1000',
        'VFD',
        'https://yaskawa.com/docs/v1000-technical-manual.pdf',
        'deepseek',
        3,
        78.00,
        test_user_id,
        284,
        3890
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 7: Delta DVP-14SS2 PLC
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb, is_verified)
    VALUES (
        'Delta DVP-14SS2 PLC User Manual',
        'Delta',
        'DVP-14SS2',
        'PLC',
        'https://s3.amazonaws.com/user-uploads/delta-dvp14ss2-manual.pdf',
        'user_upload',
        NULL,
        NULL,
        test_user_id,
        198,
        2340,
        true -- User uploaded and verified
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 8: Omron CP1E PLC
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'Omron CP1E Programmable Controller Operation Manual',
        'Omron',
        'CP1E',
        'PLC',
        'https://omron.com/manuals/cp1e-operation.pdf',
        'tavily',
        1,
        93.00,
        test_user_id,
        542,
        6780
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 9: Eaton XV300 HMI
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'Eaton XV300 HMI User and Installation Manual',
        'Eaton',
        'XV300',
        'HMI',
        'https://eaton.com/docs/xv300-hmi-manual.pdf',
        'groq',
        2,
        87.00,
        test_user_id,
        156,
        2890
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

    -- Manual 10: Danfoss VLT AutomationDrive FC 301
    INSERT INTO manuals (title, manufacturer, model_number, component_type, file_url, source, search_tier, confidence_score, uploaded_by_user_id, page_count, file_size_kb)
    VALUES (
        'Danfoss VLT AutomationDrive FC 301 Operating Instructions',
        'Danfoss',
        'FC 301',
        'VFD',
        'https://danfoss.com/manuals/fc301-operating-instructions.pdf',
        'perplexity',
        3,
        82.00,
        test_user_id,
        378,
        4560
    ) ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING;

END $$;

-- ============================================================================
-- 5. SEED DATA - MANUAL REQUESTS
-- ============================================================================

DO $$
DECLARE
    test_user_id UUID := '00000000-0000-0000-0000-000000000001';
    test_chat_id BIGINT := 123456789;
BEGIN
    -- Request 1: Mitsubishi Q-Series PLC (Highest Priority)
    -- calculated_priority = (5 * 10) + (6 - 1) = 55
    INSERT INTO manual_requests (user_id, telegram_chat_id, manufacturer, model_number, component_type, search_query, request_count, priority_level, failed_tiers, status)
    VALUES (
        test_user_id,
        test_chat_id,
        'Mitsubishi',
        'Q-Series',
        'PLC',
        'Mitsubishi Q-Series PLC programming manual',
        5,
        1, -- Critical
        ARRAY['tavily', 'groq', 'deepseek'],
        'pending'
    ) ON CONFLICT (manufacturer, model_number) WHERE status = 'pending' DO NOTHING;

    -- Request 2: Rockwell Kinetix 5500 Servo (High Priority due to count)
    -- calculated_priority = (4 * 10) + (6 - 3) = 43
    INSERT INTO manual_requests (user_id, telegram_chat_id, manufacturer, model_number, component_type, search_query, request_count, priority_level, failed_tiers, status)
    VALUES (
        test_user_id,
        test_chat_id,
        'Rockwell Automation',
        'Kinetix 5500',
        'Servo Drive',
        'Rockwell Kinetix 5500 servo drive troubleshooting',
        4,
        3, -- Normal
        ARRAY['tavily', 'serper'],
        'pending'
    ) ON CONFLICT (manufacturer, model_number) WHERE status = 'pending' DO NOTHING;

    -- Request 3: Fanuc R-30iB Controller
    -- calculated_priority = (3 * 10) + (6 - 2) = 34
    INSERT INTO manual_requests (user_id, telegram_chat_id, manufacturer, model_number, component_type, search_query, request_count, priority_level, failed_tiers, status)
    VALUES (
        test_user_id,
        test_chat_id,
        'Fanuc',
        'R-30iB',
        'Controller',
        'Fanuc R-30iB controller maintenance manual',
        3,
        2, -- High
        ARRAY['tavily'],
        'pending'
    ) ON CONFLICT (manufacturer, model_number) WHERE status = 'pending' DO NOTHING;

    -- Request 4: Cognex In-Sight 7000 Vision System
    -- calculated_priority = (2 * 10) + (6 - 3) = 23
    INSERT INTO manual_requests (user_id, telegram_chat_id, manufacturer, model_number, component_type, search_query, request_count, priority_level, failed_tiers, status)
    VALUES (
        test_user_id,
        test_chat_id,
        'Cognex',
        'In-Sight 7000',
        'Vision System',
        'Cognex In-Sight 7000 vision system setup guide',
        2,
        3, -- Normal
        ARRAY['groq'],
        'pending'
    ) ON CONFLICT (manufacturer, model_number) WHERE status = 'pending' DO NOTHING;

    -- Request 5: Festo CPV Valve Terminal (Lowest Priority)
    -- calculated_priority = (1 * 10) + (6 - 4) = 12
    INSERT INTO manual_requests (user_id, telegram_chat_id, manufacturer, model_number, component_type, search_query, request_count, priority_level, failed_tiers, status)
    VALUES (
        test_user_id,
        test_chat_id,
        'Festo',
        'CPV',
        'Valve Terminal',
        'Festo CPV valve terminal configuration manual',
        1,
        4, -- Low
        ARRAY['deepseek'],
        'pending'
    ) ON CONFLICT (manufacturer, model_number) WHERE status = 'pending' DO NOTHING;

END $$;

-- ============================================================================
-- 6. HELPER QUERIES FOR N8N WORKFLOW
-- ============================================================================

-- These queries are ready to copy-paste into n8n PostgreSQL nodes
-- All use n8n's {{$json.variable}} syntax for dynamic values

-- -----------------------------------------------------------------------------
-- Query 1: CHECK CACHE (Tier 0 - before hitting search APIs)
-- -----------------------------------------------------------------------------
-- Use Case: Check if manual already exists in cache before searching
-- n8n Node: "Check Cache" (PostgreSQL Execute Query)
-- Returns: Array of matching manuals sorted by confidence score
/*
SELECT
    id,
    title,
    file_url,
    confidence_score,
    source,
    search_tier,
    manufacturer,
    model_number,
    component_type,
    page_count
FROM manuals
WHERE manufacturer ILIKE '%{{$json.manufacturer}}%'
  AND (
      model_number ILIKE '%{{$json.model}}%'
      OR component_type ILIKE '%{{$json.component_type}}%'
  )
ORDER BY confidence_score DESC
LIMIT 5;
*/

-- -----------------------------------------------------------------------------
-- Query 2: INSERT MANUAL FROM SEARCH RESULT
-- -----------------------------------------------------------------------------
-- Use Case: Store newly discovered manual from Tavily/Groq/DeepSeek
-- n8n Node: "Save to Cache" (PostgreSQL Insert)
-- Returns: Inserted manual ID and details
/*
INSERT INTO manuals (
    title,
    manufacturer,
    model_number,
    component_type,
    file_url,
    source,
    search_tier,
    confidence_score,
    uploaded_by_user_id,
    page_count,
    file_size_kb
)
VALUES (
    {{$json.title}},
    {{$json.manufacturer}},
    {{$json.model}},
    {{$json.component_type}},
    {{$json.file_url}},
    {{$json.source}},
    {{$json.tier}},
    {{$json.confidence}},
    {{$json.user_id}},
    {{$json.page_count}},
    {{$json.file_size_kb}}
)
ON CONFLICT (manufacturer, model_number, file_url) DO NOTHING
RETURNING id, title, file_url, created_at;
*/

-- -----------------------------------------------------------------------------
-- Query 3: UPSERT MANUAL REQUEST (Increment count if duplicate)
-- -----------------------------------------------------------------------------
-- Use Case: Log failed search or increment existing request count
-- n8n Node: "Log Manual Request" (PostgreSQL Execute Query)
-- Returns: Request ID and calculated priority
/*
INSERT INTO manual_requests (
    user_id,
    telegram_chat_id,
    manufacturer,
    model_number,
    component_type,
    search_query,
    request_count,
    priority_level,
    failed_tiers
)
VALUES (
    '{{$json.user_id}}',
    {{$json.chat_id}},
    {{$json.manufacturer}},
    {{$json.model}},
    {{$json.component_type}},
    {{$json.query}},
    1,
    3,
    ARRAY[{{$json.failed_tiers}}]
)
ON CONFLICT (manufacturer, model_number)
WHERE status = 'pending'
DO UPDATE SET
    request_count = manual_requests.request_count + 1,
    last_requested_at = NOW(),
    failed_tiers = ARRAY[{{$json.failed_tiers}}]
RETURNING id, calculated_priority, request_count;
*/

-- -----------------------------------------------------------------------------
-- Query 4: GET PRIORITY QUEUE (Top 20 most urgent requests)
-- -----------------------------------------------------------------------------
-- Use Case: Display admin dashboard of missing manuals to hunt
-- n8n Node: "Get Priority Queue" (PostgreSQL Execute Query)
-- Returns: Sorted list of pending requests by urgency
/*
SELECT
    id,
    manufacturer,
    model_number,
    search_query,
    request_count,
    priority_level,
    calculated_priority,
    component_type,
    failed_tiers,
    first_requested_at,
    last_requested_at,
    notes
FROM manual_requests
WHERE status = 'pending'
ORDER BY calculated_priority DESC, last_requested_at DESC
LIMIT 20;
*/

-- -----------------------------------------------------------------------------
-- Query 5: RESOLVE REQUEST (Mark found and link to manual)
-- -----------------------------------------------------------------------------
-- Use Case: When admin uploads manual, resolve pending request
-- n8n Node: "Resolve Request" (PostgreSQL Execute Query)
-- Returns: User info for notification
/*
UPDATE manual_requests
SET
    status = 'resolved',
    resolved_manual_id = '{{$json.manual_id}}',
    resolved_at = NOW()
WHERE id = '{{$json.request_id}}'
RETURNING user_id, telegram_chat_id, manufacturer, model_number;
*/

-- -----------------------------------------------------------------------------
-- Query 6: GET USER REQUEST HISTORY
-- -----------------------------------------------------------------------------
-- Use Case: Show user their past manual requests and statuses
-- n8n Node: "Get User Requests" (PostgreSQL Execute Query)
-- Returns: All requests for a specific user
/*
SELECT
    mr.id,
    mr.manufacturer,
    mr.model_number,
    mr.component_type,
    mr.search_query,
    mr.status,
    mr.calculated_priority,
    mr.first_requested_at,
    mr.resolved_at,
    m.title AS resolved_manual_title,
    m.file_url AS resolved_manual_url
FROM manual_requests mr
LEFT JOIN manuals m ON mr.resolved_manual_id = m.id
WHERE mr.user_id = '{{$json.user_id}}'
ORDER BY mr.last_requested_at DESC
LIMIT 50;
*/

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check that seed data was inserted correctly
SELECT 'Manuals Count:' AS metric, COUNT(*)::TEXT AS value FROM manuals
UNION ALL
SELECT 'Manual Requests Count:', COUNT(*)::TEXT FROM manual_requests
UNION ALL
SELECT 'Pending Requests:', COUNT(*)::TEXT FROM manual_requests WHERE status = 'pending'
UNION ALL
SELECT 'Test User Exists:', COUNT(*)::TEXT FROM rivet_users WHERE id = '00000000-0000-0000-0000-000000000001';

-- Show priority queue (sorted by calculated_priority)
SELECT
    manufacturer || ' ' || model_number AS equipment,
    request_count,
    priority_level,
    calculated_priority,
    status
FROM manual_requests
WHERE status = 'pending'
ORDER BY calculated_priority DESC;

-- Show manuals by search tier
SELECT
    search_tier,
    source,
    COUNT(*) AS manual_count,
    AVG(confidence_score)::DECIMAL(5,2) AS avg_confidence
FROM manuals
WHERE search_tier IS NOT NULL
GROUP BY search_tier, source
ORDER BY search_tier, source;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
