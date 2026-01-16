-- Ralph Stories: Technical Debt Cleanup
-- Run this after database is available
-- psql $DATABASE_URL -f scripts/ralph/insert_tech_debt_stories.sql

-- Clear any existing stories from this batch (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'DEBT-%';

-- Insert tech debt cleanup stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status) VALUES

-- Story 1: Extract Hardcoded Configuration
(1, 'DEBT-001', 'Extract Hardcoded Chat ID to Configuration',
'The chat ID 8445149012 is hardcoded in 6+ locations across the codebase. Extract to rivet_pro/config/settings.py as ADMIN_CHAT_ID and update all references.

Files to modify:
- rivet_pro/adapters/telegram/bot.py (line ~73)
- rivet_pro/core/services/agent_executor.py (line ~82)
- rivet_pro/core/services/alerting_service.py (line ~32)
- rivet_pro/infra/database.py (line ~119)
- rivet_pro/troubleshooting/commands.py (line ~28)
- rivet_pro/test_ocr_flow.py (line ~130)

Steps:
1. Add ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "8445149012") to settings.py
2. Import settings in each file and replace hardcoded value
3. Add ADMIN_CHAT_ID to .env.example with documentation
4. Verify with: grep -rn "8445149012" rivet_pro/ (should return 0 results)',
'["No hardcoded chat IDs remain in codebase (grep returns 0 results)", "ADMIN_CHAT_ID added to rivet_pro/config/settings.py", "All 6 files updated to use settings.ADMIN_CHAT_ID", ".env.example documents the ADMIN_CHAT_ID setting", "Bot starts and works correctly with config value"]'::jsonb,
1, 'todo'),

-- Story 2: Persistent Node Callback Storage
(1, 'DEBT-002', 'Implement Persistent Node Callback Storage',
'Node callback mappings are stored in an in-memory dict (rivet_pro/troubleshooting/callback.py:149). This means callbacks are lost on bot restart, breaking troubleshooting tree navigation.

Steps:
1. Create migration 027_node_callback_mappings.sql with table:
   - id SERIAL PRIMARY KEY
   - callback_id VARCHAR(64) UNIQUE NOT NULL
   - node_data JSONB NOT NULL
   - created_at TIMESTAMPTZ DEFAULT NOW()
   - expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL ''24 hours''

2. Update callback.py:
   - Replace module-level dict with async PostgreSQL functions
   - _store_node_mapping() -> INSERT into node_callback_mappings
   - _get_node_mapping() -> SELECT from node_callback_mappings
   - Add cleanup function to delete expired mappings

3. Add index on callback_id and expires_at for efficient queries

4. Test that callbacks survive bot restart',
'["Migration 027_node_callback_mappings.sql created and applied", "callback.py uses PostgreSQL instead of in-memory dict", "Callbacks persist across bot restarts", "Expired mappings (>24h) are automatically cleaned up", "No memory leak from accumulating mappings", "Troubleshooting tree navigation works after restart"]'::jsonb,
2, 'todo'),

-- Story 3: Implement Troubleshooting Tree DB Query
(1, 'DEBT-003', 'Implement Troubleshooting Tree Database Query',
'The functions _query_cached_trees() and _load_tree_from_db() in rivet_pro/troubleshooting/fallback.py (lines 375-420) have TODO comments and are not implemented. This causes the system to always fall back to expensive Claude API calls.

Steps:
1. Check if troubleshooting_trees table exists, create migration if needed
2. Implement _query_cached_trees() at line 375:
   - Query troubleshooting_trees table by equipment_type/manufacturer
   - Return list of matching tree metadata (id, title, created_at)
   - Add similarity search on title/description if available

3. Implement _load_tree_from_db() at line 418:
   - Fetch full tree JSON from database by tree_id
   - Parse into TroubleshootingTree dataclass
   - Add in-memory TTL cache (5 minutes) to reduce DB queries

4. Update fallback flow to check DB before calling Claude

5. Verify Claude API calls are reduced for repeat equipment queries',
'["_query_cached_trees() implemented with real database query", "_load_tree_from_db() implemented with full tree retrieval", "In-memory TTL cache (5 min) reduces database queries", "Falls back to Claude only when no cached tree exists", "Claude API calls measurably reduced for repeat queries", "Existing tests still pass"]'::jsonb,
3, 'todo'),

-- Story 4: Silent Error Handling Cleanup
(1, 'DEBT-004', 'Replace Silent Error Handling with Proper Logging',
'There are 17 instances of bare "except: pass" or "except Exception: pass" that silently swallow errors. This makes debugging impossible and hides system failures.

Files to fix:
- rivet_pro/core/services/feedback_service.py:559
- rivet_pro/core/services/pipeline_integration.py:192
- rivet_pro/core/services/resilient_telegram_manager.py:143
- rivet_pro/workers/enrichment_worker.py (lines 103, 146, 158, 173, 291)

Steps for each instance:
1. Identify what exception types are expected
2. Replace bare except with specific exception types (e.g., asyncio.CancelledError, ConnectionError)
3. Add logger.exception() or logger.warning() call
4. Re-raise critical exceptions that should not be swallowed
5. Add context to log message (what operation failed, relevant IDs)

Example transformation:
BEFORE: except: pass
AFTER:  except asyncio.CancelledError:
            raise  # Re-raise cancellation
        except Exception as e:
            logger.warning(f"Non-critical error in {operation}: {e}")

Verify: grep -rn "except.*:.*pass" rivet_pro/ should return 0 results',
'["No bare except: pass remains in codebase", "All 5 files updated with proper exception handling", "Each caught exception is logged with context", "Critical exceptions (CancelledError, SystemExit) are re-raised", "grep -rn \"except.*:.*pass\" rivet_pro/ returns 0 results", "Bot operates normally with new error handling", "Errors now visible in logs for debugging"]'::jsonb,
4, 'todo');

-- Verify insertion
SELECT story_id, title, status FROM ralph_stories WHERE story_id LIKE 'DEBT-%' ORDER BY priority;
