-- Insert AUTO-KB Stories into ralph_stories table

-- Insert Phase 1 stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status)
VALUES
  (1, 'AUTO-KB-001', 'Create Enrichment Queue Schema & Service',
   'Create database tables and service for managing enrichment work queue.',
   '["Create enrichment_queue table with migration", "Create product_families table with migration", "Create manual_files table with migration (including vector extension)", "Create enrichment_stats table with migration", "Create EnrichmentQueueService in rivet_pro/core/services/enrichment_queue_service.py", "Implement add_to_queue(manufacturer, model, priority)", "Implement get_next_job() with priority ordering", "Implement update_job_status(job_id, status, metadata)", "Add indexes for performance", "Run migrations on dev database", "Verify tables created with correct schema"]'::jsonb,
   1, 'todo'),

  (1, 'AUTO-KB-002', 'Implement Product Family Discoverer',
   'Service that discovers related product models using LLM and pattern matching.',
   '["Create ProductFamilyDiscoverer in rivet_pro/core/services/product_family_discoverer.py", "Implement discover_family(manufacturer, model) method", "Use LLM to identify product family (e.g., S7-1200 → S7 Series)", "Generate model patterns (e.g., S7-1200 → S7-*, S7-1500, S7-300)", "Query Tavily for each family member in parallel", "Store discovered families in product_families table", "Handle common manufacturer families: Siemens, Allen Bradley, ABB, Schneider", "Add retry logic for failed discoveries", "Test with real equipment: Siemens S7-1200 should find 10+ family members", "Log all discoveries with metrics"]'::jsonb,
   2, 'todo'),

  (1, 'AUTO-KB-003', 'Build Autonomous Enrichment Worker',
   '24/7 background worker that processes enrichment queue continuously.',
   '["Create AutonomousEnrichmentWorker in rivet_pro/workers/enrichment_worker.py", "Implement async run() method that loops forever", "Poll enrichment_queue every 30 seconds for pending jobs", "Process jobs in priority order (highest first)", "For each job: discover family → search manuals → download → create atoms", "Run 3-5 concurrent jobs in parallel (asyncio.gather)", "Implement graceful shutdown on SIGTERM", "Add worker heartbeat every 5 minutes to enrichment_stats", "Add error handling with exponential backoff on failures", "Create systemd service file: /etc/systemd/system/rivet-enrichment-worker.service", "Test: Start worker, add job to queue, verify it processes automatically", "Verify worker survives crashes and restarts"]'::jsonb,
   3, 'todo'),

  (1, 'AUTO-KB-004', 'Integrate User Query Triggers',
   'Modify bot to add enrichment jobs when users search for equipment.',
   '["Update rivet_pro/adapters/telegram/bot.py search_knowledge_base()", "After Tavily search, call enrichment_queue_service.add_to_queue()", "Set priority based on cache miss frequency (more misses = higher priority)", "Deduplicate: Dont add if family already in queue or completed recently", "Track user_query_count: Increment if family already queued", "Log queue additions with reason (user_search, cache_miss, etc.)", "Test: Search new equipment → Verify enrichment job created", "Test: Search same equipment 3 times → Verify priority increases", "Test: Search equipment with existing family → Verify no duplicate jobs"]'::jsonb,
   4, 'todo'),

  (1, 'AUTO-KB-005', 'Add Worker Health Monitoring',
   'Dashboard and alerting for enrichment worker health.',
   '["Create worker_status() endpoint in enrichment_queue_service", "Return: is_running, last_heartbeat, jobs_processed_today, current_job, queue_depth", "Add /kb_worker_status Telegram command", "Display worker status in human-readable format", "Alert if worker hasnt sent heartbeat in 10+ minutes", "Add worker metrics to daily health report", "Create restart script: scripts/restart_enrichment_worker.sh", "Test: Stop worker → Verify alert sent", "Test: /kb_worker_status → Verify correct status shown"]'::jsonb,
   5, 'todo');

-- Insert Phase 2 stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status)
VALUES
  (1, 'AUTO-KB-006', 'Implement Manual Download Manager',
   'Service to download manuals from URLs and store locally.',
   '["Create ManualDownloadManager in rivet_pro/core/services/manual_download_manager.py", "Implement download_manual(url, manufacturer, model) method", "Download PDFs to local storage: /opt/Rivet-PRO/manuals/{manufacturer}/{model}/", "Verify file integrity with checksum", "Handle large files (stream download, progress tracking)", "Retry failed downloads with exponential backoff (3 attempts)", "Store metadata in manual_files table", "Support concurrent downloads (5-10 parallel)", "Add timeout protection (30s per download)", "Test: Download real manual → Verify file saved correctly", "Test: Download 10 manuals in parallel → All succeed"]'::jsonb,
   6, 'todo'),

  (1, 'AUTO-KB-007', 'Add Text Extraction from PDFs',
   'Extract text content from downloaded manuals for search and indexing.',
   '["Add PyPDF2 dependency to requirements.txt", "Implement extract_text(pdf_path) in ManualDownloadManager", "Extract all text from PDF pages", "Clean text: remove headers/footers, normalize whitespace", "Store text_content in manual_files table", "Handle encrypted/password-protected PDFs gracefully", "Add OCR fallback for scanned PDFs (Tesseract or Gemini Vision)", "Limit text storage to first 50 pages (performance)", "Test: Extract text from Siemens manual → Verify readable content", "Test: Handle corrupted PDF → Graceful error, no crash"]'::jsonb,
   7, 'todo'),

  (1, 'AUTO-KB-008', 'Generate Semantic Search Embeddings',
   'Create vector embeddings for semantic search of manual content.',
   '["Add pgvector extension to database", "Install sentence-transformers or use OpenAI embeddings", "Implement generate_embedding(text) method", "Generate embedding vector for each manuals text_content", "Store embedding_vector in manual_files table", "Create vector similarity search function", "Add semantic_search(query) method to return top 10 manuals", "Test: Query PLC programming → Return relevant manuals", "Test: Query motor troubleshooting → Return motor manuals", "Benchmark: Search 1000 manuals in < 100ms"]'::jsonb,
   8, 'todo'),

  (1, 'AUTO-KB-009', 'Implement Local Manual Serving',
   'Serve downloaded manuals directly from local storage with low latency.',
   '["Update manual_service.py get_manual() method", "Check manual_files table first before external URL", "If local file available: Return local file path", "If not available but in download queue: Return downloading status", "Serve files via FastAPI endpoint: /api/manuals/{manual_id}", "Add /manual command in Telegram bot to download local file", "Track access_count and last_accessed_at", "Test: Request manual → Served from local in < 500ms", "Test: Request manual not yet downloaded → Queue for download, return external URL", "Test: 100 concurrent requests → All served successfully"]'::jsonb,
   9, 'todo'),

  (1, 'AUTO-KB-010', 'Add S3 Backup Storage (Optional)',
   'Sync downloaded manuals to S3 for redundancy and CDN serving.',
   '["Add boto3 dependency", "Configure S3 bucket: s3://rivet-kb-manuals/", "Implement upload_to_s3(file_path) in ManualDownloadManager", "Upload files after local download completes", "Store s3_key in manual_files table", "Set storage_location=both when in S3 and local", "Add fallback: If local file missing, fetch from S3", "Configure S3 lifecycle policy: Delete files older than 1 year if not accessed", "Test: Download manual → Verify uploaded to S3", "Test: Delete local file → Verify re-downloaded from S3 on request"]'::jsonb,
   10, 'todo');

-- Insert Phase 3 stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status)
VALUES
  (1, 'AUTO-KB-011', 'Implement Query Pattern Learning',
   'Analyze user query patterns to prioritize enrichment intelligently.',
   '["Create QueryPatternAnalyzer in rivet_pro/core/services/query_pattern_analyzer.py", "Track manufacturer popularity: COUNT queries by manufacturer", "Track model family popularity: COUNT queries by product_family", "Track time-based patterns: Identify peak query times", "Generate priority scores: popular manufacturers get higher priority", "Update enrichment_queue priorities daily based on patterns", "Boost priority for: 1) High user query count, 2) Recent queries, 3) Incomplete families", "Reduce priority for: 1) Completed families, 2) Old families with no recent queries", "Test: 10 users search Siemens → Siemens family boosted to priority 9-10", "Test: 1 user searches obscure brand → Priority stays at 5"]'::jsonb,
   11, 'todo'),

  (1, 'AUTO-KB-012', 'Add Manufacturer Catalog Scraping',
   'Proactively scrape manufacturer product catalogs for complete family discovery.',
   '["Create ManufacturerCatalogScraper in rivet_pro/core/services/catalog_scraper.py", "Implement scrapers for priority manufacturers: Siemens, Rockwell/Allen Bradley, ABB, Schneider Electric", "Use BeautifulSoup or Playwright for scraping", "Extract product model numbers, series names, documentation links", "Store discovered families in product_families table", "Run scraper weekly (cron job)", "Add --scrape-catalog CLI command for manual runs", "Test: Run Siemens scraper → Discover 50+ S7 models", "Test: Run ABB scraper → Discover ACH580 drive family"]'::jsonb,
   12, 'todo'),

  (1, 'AUTO-KB-013', 'Build Enrichment Priority Dashboard',
   'Web dashboard showing enrichment status, queue depth, and coverage.',
   '["Create enrichment dashboard page: /admin/enrichment", "Show current queue depth by priority", "Display top 10 families being enriched", "Show enrichment rate: Manuals indexed per day", "Display storage stats: Total GB stored, file count", "Show manufacturer coverage: % of popular manufacturers indexed", "Add family completion progress bars", "Display worker status: Last heartbeat, current job, uptime", "Add manual controls: Pause worker, boost priority, clear queue", "Test: Dashboard loads in < 1s", "Test: All metrics update in real-time"]'::jsonb,
   13, 'todo');
