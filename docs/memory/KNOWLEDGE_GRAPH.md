# RIVET Pro Knowledge Graph

> **Living Document** - Updated after each Claude Code session
>
> Last Updated: 2026-01-15 10:55 UTC
>
> This is the canonical backup of the MCP memory graph. If local MCP memory is lost, this document can be used to rebuild it.

---

## Entities

### Project Core

#### RIVET-Pro
- **Type**: Project
- **Observations**:
  - Atlas CMMS extracted from Agent Factory
  - Telegram bot interface for equipment technicians
  - PostgreSQL on Neon (ep-purple-hall-ahimeyn0)
  - AI-powered equipment identification via OCR
  - Self-healing knowledge base with autonomous enrichment

---

### AUTO-KB System (Autonomous Knowledge Base Enrichment)

#### AUTO-KB-System
- **Type**: Feature
- **Observations**:
  - Autonomous Knowledge Base Enrichment system implemented in Jan 2026
  - Consists of 13 stories: AUTO-KB-001 through AUTO-KB-013
  - All stories completed and tracked in ralph_stories database table
  - Also tracked in Backlog.md as task-13 through task-24
  - Enables self-healing knowledge base that learns from user queries

#### EnrichmentWorker
- **Type**: Service
- **Location**: `rivet_pro/workers/enrichment_worker.py`
- **Observations**:
  - 24/7 background worker processing enrichment queue
  - Polls queue every 30 seconds, processes 3 concurrent jobs
  - Graceful shutdown on SIGTERM/SIGINT
  - Heartbeat every 5 minutes to enrichment_stats table
  - Exponential backoff on failures (max 300 seconds)
  - Systemd service file at deploy/rivet-enrichment-worker.service
  - Restart script at scripts/restart_enrichment_worker.sh

#### ManualDownloadManager
- **Type**: Service
- **Location**: `rivet_pro/core/services/manual_download_manager.py`
- **Observations**:
  - Downloads equipment manuals from URLs with streaming
  - Supports 5 concurrent downloads, 30s timeout, 3 retries
  - Stores files in ~/Rivet-PRO/manuals (Windows) or /opt/Rivet-PRO/manuals (Linux)
  - Calculates SHA256 checksums for verification
  - PyPDF2 text extraction with _clean_extracted_text()
  - Optional S3 backup with boto3 (AUTO-KB-010)
  - S3 bucket: rivet-kb-manuals, uses STANDARD_IA storage class

#### SemanticSearchService
- **Type**: Service
- **Location**: `rivet_pro/core/services/semantic_search_service.py`
- **Observations**:
  - Generates embeddings using OpenAI text-embedding-ada-002 (1536 dims)
  - Falls back to sentence-transformers all-MiniLM-L6-v2 (384 dims)
  - Stores embeddings in manual_files.embedding_vector column
  - semantic_search() uses pgvector or Python cosine similarity fallback
  - embed_all_manuals() for batch embedding generation

#### QueryPatternAnalyzer
- **Type**: Service
- **Location**: `rivet_pro/core/services/query_pattern_analyzer.py`
- **Observations**:
  - Tracks user queries in query_patterns table
  - Calculates priority scores based on manufacturer/model popularity
  - Boost factors: HIGH_QUERY_COUNT=2.0, RECENT_QUERIES=1.5, INCOMPLETE_FAMILY=1.3
  - Reduce factors: COMPLETED_FAMILY=0.3, OLD_NO_QUERIES=0.5
  - update_enrichment_priorities() adjusts queue priorities daily
  - daily_priority_update() standalone function for cron jobs

#### CatalogScraper
- **Type**: Service
- **Location**: `rivet_pro/core/services/catalog_scraper.py`
- **Observations**:
  - Scrapes manufacturer documentation portals
  - Supported: Siemens, Rockwell, ABB, Schneider, Emerson
  - Requires beautifulsoup4 for HTML parsing
  - Respects rate limits (2s between requests)
  - Stores discovered manuals in discovered_manuals table
  - scrape_all_manufacturers() for batch scraping

#### EnrichmentDashboardAPI
- **Type**: API
- **Location**: `rivet_pro/adapters/web/routers/enrichment.py`
- **Observations**:
  - Endpoints at /api/admin/enrichment/*
  - Requires admin role (admin_required dependency)
  - /dashboard - overview with queue depth, top families, worker status
  - /queue - list with filtering by status, priority, manufacturer
  - /workers - active workers and performance stats
  - /queue/{job_id}/priority - update job priority
  - /queue/{job_id}/retry - retry failed job
  - /stats/daily - daily enrichment statistics
  - /manuals/stats - downloaded manual statistics

#### ManualService-LocalServing
- **Type**: Feature
- **Location**: `rivet_pro/core/services/manual_service.py`
- **Observations**:
  - Updated for AUTO-KB-009
  - search_manual() now checks local files first via prefer_local=True
  - get_local_manual() checks manual_files table for local copies
  - Verifies file exists on disk before returning
  - Tracks access_count and last_accessed_at
  - get_local_manual_stats() for monitoring local storage

---

### Database

#### AUTO-KB-Migrations
- **Type**: Database
- **Observations**:
  - 019_query_patterns.sql - query_patterns table for tracking user searches
  - 020_catalog_scraper.sql - discovered_manuals table for scraped manual URLs
  - manual_files table extended with: s3_key, s3_uploaded_at, last_accessed_at, access_count
  - enrichment_queue table for job queue with priority and status
  - enrichment_stats table for worker heartbeats and metrics

#### DatabaseSchema
- **Type**: Technical
- **Key Tables**:
  - users, organizations, org_memberships (SaaS layer)
  - equipment, work_orders, technicians (CMMS core)
  - knowledge_atoms, manual_cache, manual_files (KB)
  - enrichment_queue, enrichment_stats (AUTO-KB)
  - query_patterns, discovered_manuals (AUTO-KB analytics)
  - ralph_stories, ralph_projects (Task management)

---

### Integrations

#### TelegramBot-KBIntegration
- **Type**: Feature
- **Location**: `rivet_pro/adapters/telegram/bot.py`
- **Observations**:
  - Updated for AUTO-KB-004
  - Triggers enrichment queue on KB miss in _search_knowledge_base()
  - Uses EnrichmentQueueService to add jobs with priority 5
  - /kb_worker_status command shows worker health (admin only)
  - Queries enrichment_stats for recent heartbeats

---

### Task Management

#### BacklogMD-Tasks
- **Type**: TaskManagement
- **Observations**:
  - AUTO-KB tasks added as task-13 through task-24
  - task-13: AUTO-KB epic (parent task)
  - task-14 through task-24: Individual AUTO-KB stories
  - All tasks marked as done with #kb #done labels

#### RalphStories-AUTOKB
- **Type**: TaskManagement
- **Observations**:
  - AUTO-KB-001 through AUTO-KB-013 in ralph_stories table
  - All marked status='done' with completed_at timestamps
  - Implemented by Claude as 'Ralph' agent on 2026-01-15
  - Commits: 2e9e7a0 through 267580b (11 commits)
  - Pushed to GitHub main branch

---

### User Preferences

#### UserPreferences
- **Type**: Preferences
- **Observations**:
  - Archive files instead of permanently deleting
  - Keep local archive for files with secrets/API keys
  - Use trunk-based development with feature flags
  - Self-approve PRs for solo development
  - Prefer automatic reminders to save session context

---

## Relations

```
AUTO-KB-System
├── contains → EnrichmentWorker
├── contains → ManualDownloadManager
├── contains → SemanticSearchService
├── contains → QueryPatternAnalyzer
├── contains → CatalogScraper
├── contains → EnrichmentDashboardAPI
├── contains → ManualService-LocalServing
└── requires → AUTO-KB-Migrations

EnrichmentWorker
├── uses → ManualDownloadManager
└── uses → SemanticSearchService

ManualDownloadManager
└── feeds → SemanticSearchService

QueryPatternAnalyzer
└── configures → EnrichmentWorker

CatalogScraper
└── feeds → ManualDownloadManager

TelegramBot-KBIntegration
└── triggers → EnrichmentWorker

EnrichmentDashboardAPI
└── monitors → EnrichmentWorker

BacklogMD-Tasks
└── tracks → AUTO-KB-System

RalphStories-AUTOKB
└── tracks → AUTO-KB-System
```

---

## How to Restore MCP Memory from This Document

If MCP memory is lost, run these commands in Claude Code:

```python
# 1. Create entities (copy each entity block above)
mcp__memory__create_entities([{
    "name": "AUTO-KB-System",
    "entityType": "Feature",
    "observations": [
        "Autonomous Knowledge Base Enrichment system implemented in Jan 2026",
        # ... copy all observations
    ]
}])

# 2. Create relations
mcp__memory__create_relations([
    {"from": "AUTO-KB-System", "to": "EnrichmentWorker", "relationType": "contains"},
    # ... copy all relations
])
```

---

## Version History

| Date | Changes |
|------|---------|
| 2026-01-15 | Initial creation with AUTO-KB system entities |
| 2026-01-14 | (Implicit) Project setup, cleanup, memory system |
