-- AUTO-KB-012: Manufacturer Catalog Scraping
-- Stores discovered manuals from manufacturer documentation portals

CREATE TABLE IF NOT EXISTS discovered_manuals (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    manufacturer VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    title TEXT,
    source_page TEXT,
    discovered_at TIMESTAMP DEFAULT NOW(),
    downloaded_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, downloaded, failed, skipped
    error_message TEXT,
    metadata JSONB
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_discovered_manuals_manufacturer
    ON discovered_manuals(LOWER(manufacturer));

CREATE INDEX IF NOT EXISTS idx_discovered_manuals_status
    ON discovered_manuals(status);

CREATE INDEX IF NOT EXISTS idx_discovered_manuals_pending
    ON discovered_manuals(manufacturer, discovered_at DESC)
    WHERE status = 'pending';

-- Comments
COMMENT ON TABLE discovered_manuals IS 'Manuals discovered by catalog scraper (AUTO-KB-012)';
COMMENT ON COLUMN discovered_manuals.url IS 'Direct URL to the manual PDF';
COMMENT ON COLUMN discovered_manuals.source_page IS 'Page where the manual link was found';
COMMENT ON COLUMN discovered_manuals.status IS 'pending=awaiting download, downloaded=complete, failed=error, skipped=intentionally ignored';
