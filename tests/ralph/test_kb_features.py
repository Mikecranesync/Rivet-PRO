"""
Automated tests for KB features implemented by Ralph.

Tests the 5 KB stories currently being processed:
- KB-006: Create knowledge atoms from approved Ralph fixes
- KB-008: Add /kb_stats command for monitoring
- KB-007: Add knowledge base analytics service
- CRITICAL-KB-001: Knowledge atoms not being created from user interactions
- KB-002: Create SPEC atom after manual found
"""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4, UUID

# These imports will be available after Ralph implements the features
try:
    from rivet_pro.core.services.feedback_service import FeedbackService
    from rivet_pro.core.services.kb_analytics_service import KnowledgeBaseAnalytics
    from rivet_pro.core.models.knowledge import KnowledgeAtomCreate, AtomType
except ImportError:
    # KB analytics service doesn't exist yet - Ralph will create it
    KnowledgeBaseAnalytics = None


class TestKB006_CreateAtomsFromRalphFixes:
    """Test KB-006: Create knowledge atoms from approved Ralph fixes"""

    @pytest.mark.asyncio
    async def test_create_atom_from_feedback_exists(self, db_pool):
        """Verify create_atom_from_feedback() method exists"""
        feedback_service = FeedbackService(db_pool)

        # Should have the new method
        assert hasattr(feedback_service, 'create_atom_from_feedback'), \
            "FeedbackService missing create_atom_from_feedback() method"

    @pytest.mark.asyncio
    async def test_feedback_to_atom_pipeline(self, db_pool):
        """
        Test complete pipeline: User reports bug → Ralph fixes → Atom created
        """
        feedback_service = FeedbackService(db_pool)

        # 1. User reports manual 404
        user_id = await db_pool.fetchval(
            "SELECT id FROM users WHERE telegram_user_id = '12345' LIMIT 1"
        )

        interaction_id = await feedback_service.create_feedback(
            user_id=user_id,
            feedback_text="Allen Bradley 2080-LC20 manual returns 404",
            feedback_type='manual_404',
            context_data={
                'manufacturer': 'Allen Bradley',
                'model': '2080-LC20',
                'equipment_type': 'PLC'
            },
            telegram_user_id='12345'
        )

        # 2. Ralph creates fix story
        story_id = f"FEEDBACK-TEST-{uuid4().hex[:8]}"
        await db_pool.execute(
            """
            INSERT INTO ralph_stories (
                story_id, project_id, title, description,
                acceptance_criteria, status, priority,
                feedback_interaction_id, approval_status
            ) VALUES ($1, 1, $2, $3, $4, 'done', 8, $5, 'approved')
            """,
            story_id,
            "Fix: Manual 404 for Allen Bradley 2080-LC20",
            "Manual link was broken. Updated to correct URL.",
            '["Manual accessible", "Returns 200 status"]',
            interaction_id
        )

        # 3. Trigger atom creation (simulating n8n workflow)
        await feedback_service.create_atom_from_feedback(
            story_id=story_id,
            interaction_id=interaction_id
        )

        # 4. Verify atom was created
        atom = await db_pool.fetchrow(
            """
            SELECT * FROM knowledge_atoms
            WHERE source_type = 'feedback'
              AND source_id = $1
            """,
            str(interaction_id)
        )

        assert atom is not None, "Knowledge atom should be created from feedback"
        assert atom['atom_type'] == 'SPEC', "Manual 404 should create SPEC atom"
        assert atom['confidence'] >= 0.85, "Feedback-validated atoms should have high confidence"
        assert atom['human_verified'] is True, "Atoms from approved fixes should be human-verified"

        # Verify content includes fix details
        content = atom['content']
        assert 'Allen Bradley' in content
        assert '2080-LC20' in content


class TestKB007_AnalyticsService:
    """Test KB-007: Add knowledge base analytics service"""

    @pytest.mark.asyncio
    async def test_analytics_service_exists(self, db_pool):
        """Verify KnowledgeBaseAnalytics service was created"""
        if KnowledgeBaseAnalytics is None:
            pytest.skip("KB analytics service not yet implemented by Ralph")

        analytics = KnowledgeBaseAnalytics(db_pool)
        assert analytics is not None

    @pytest.mark.asyncio
    async def test_get_learning_stats(self, db_pool):
        """Test get_learning_stats() returns comprehensive KB metrics"""
        if KnowledgeBaseAnalytics is None:
            pytest.skip("KB analytics service not yet implemented by Ralph")

        analytics = KnowledgeBaseAnalytics(db_pool)
        stats = await analytics.get_learning_stats()

        # Verify required metrics
        assert 'total_atoms' in stats
        assert 'atoms_by_source' in stats
        assert 'verified_atoms' in stats
        assert 'gaps_detected' in stats
        assert 'gaps_resolved' in stats
        assert 'avg_confidence' in stats
        assert 'most_used_atoms' in stats

    @pytest.mark.asyncio
    async def test_get_kb_hit_rate(self, db_pool):
        """Test KB hit rate calculation"""
        if KnowledgeBaseAnalytics is None:
            pytest.skip("KB analytics service not yet implemented by Ralph")

        analytics = KnowledgeBaseAnalytics(db_pool)
        hit_rate = await analytics.get_kb_hit_rate()

        assert isinstance(hit_rate, float)
        assert 0 <= hit_rate <= 100, "Hit rate should be percentage"

    @pytest.mark.asyncio
    async def test_get_response_time_comparison(self, db_pool):
        """Test response time comparison between KB and external search"""
        if KnowledgeBaseAnalytics is None:
            pytest.skip("KB analytics service not yet implemented by Ralph")

        analytics = KnowledgeBaseAnalytics(db_pool)
        comparison = await analytics.get_response_time_comparison()

        assert 'kb_avg_ms' in comparison
        assert 'external_avg_ms' in comparison
        assert comparison['kb_avg_ms'] < comparison['external_avg_ms'], \
            "KB should be faster than external search"


class TestKB008_StatsCommand:
    """Test KB-008: Add /kb_stats command for monitoring"""

    @pytest.mark.asyncio
    async def test_kb_stats_command_exists(self, bot_app):
        """Verify /kb_stats command was registered"""
        # Check bot.py has kb_stats_command handler
        from rivet_pro.adapters.telegram import bot

        assert hasattr(bot, 'kb_stats_command'), \
            "bot.py should have kb_stats_command handler"

    @pytest.mark.asyncio
    async def test_kb_stats_returns_formatted_message(self, db_pool, mock_telegram_update):
        """Test /kb_stats returns properly formatted Telegram message"""
        from rivet_pro.adapters.telegram.bot import kb_stats_command

        # Mock admin user
        mock_telegram_update.effective_user.id = 123456  # Your admin ID

        # Call command
        await kb_stats_command(mock_telegram_update, None)

        # Verify message sent
        reply = mock_telegram_update.message.reply_text
        assert reply.called, "/kb_stats should send reply"

        message_text = reply.call_args[0][0]

        # Verify message contains expected stats
        assert 'Total atoms' in message_text
        assert 'KB hit rate' in message_text
        assert 'Avg response time' in message_text
        assert 'Top 5 most used atoms' in message_text
        assert 'Pending gaps' in message_text

    @pytest.mark.asyncio
    async def test_kb_stats_admin_only(self, db_pool, mock_telegram_update):
        """Test /kb_stats is restricted to admin users"""
        from rivet_pro.adapters.telegram.bot import kb_stats_command

        # Mock non-admin user
        mock_telegram_update.effective_user.id = 999999

        # Call command
        await kb_stats_command(mock_telegram_update, None)

        # Should deny access
        reply = mock_telegram_update.message.reply_text
        message_text = reply.call_args[0][0]
        assert 'unauthorized' in message_text.lower() or 'admin only' in message_text.lower()


class TestCRITICAL_KB001_AtomCreation:
    """Test CRITICAL-KB-001: Knowledge atoms not being created from user interactions"""

    @pytest.mark.asyncio
    async def test_atoms_created_after_ocr(self, db_pool):
        """
        Test that atoms are created after successful OCR + manual retrieval
        """
        # 1. Simulate user sending nameplate photo
        user_id = await db_pool.fetchval(
            "SELECT id FROM users WHERE telegram_user_id = '12345' LIMIT 1"
        )

        # 2. Create interaction record
        interaction_id = await db_pool.fetchval(
            """
            INSERT INTO interactions (
                id, user_id, interaction_type,
                context_data, outcome, created_at
            ) VALUES (
                gen_random_uuid(), $1, 'photo_ocr',
                $2::jsonb, 'manual_found', NOW()
            )
            RETURNING id
            """,
            user_id,
            '{"manufacturer": "Siemens", "model": "S7-1200", "manual_url": "https://example.com/manual.pdf"}'
        )

        # 3. Check atom was created
        atom = await db_pool.fetchrow(
            """
            SELECT * FROM knowledge_atoms
            WHERE source_type = 'user_interaction'
              AND source_id = $1
            """,
            str(interaction_id)
        )

        assert atom is not None, \
            "CRITICAL: Atom should be auto-created after successful manual retrieval"

        assert atom['manufacturer'] == 'Siemens'
        assert atom['model'] == 'S7-1200'
        assert 'manual_url' in atom['content']

    @pytest.mark.asyncio
    async def test_atoms_linked_to_interactions(self, db_pool):
        """Verify interactions table has atom_id foreign key"""
        # Check schema
        schema = await db_pool.fetchrow(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'interactions'
              AND column_name = 'atom_id'
            """
        )

        assert schema is not None, "interactions table should have atom_id column"
        assert schema['data_type'] == 'uuid'


class TestKB002_SpecAtomAfterManual:
    """Test KB-002: Create SPEC atom after manual found"""

    @pytest.mark.asyncio
    async def test_create_manual_atom_helper_exists(self):
        """Verify _create_manual_atom() helper was added to bot.py"""
        from rivet_pro.adapters.telegram import bot

        assert hasattr(bot, '_create_manual_atom') or hasattr(bot, 'create_manual_atom'), \
            "bot.py should have _create_manual_atom() helper"

    @pytest.mark.asyncio
    async def test_atom_created_after_manual_search(self, db_pool, mock_ocr_result):
        """
        Integration test: OCR → Manual search → Atom creation
        """
        from rivet_pro.adapters.telegram.bot import _handle_photo

        # Mock Tavily finding manual
        mock_ocr_result['manual_url'] = 'https://example.com/test-manual.pdf'

        # Trigger photo handling (this should create atom)
        result = await _handle_photo(
            manufacturer='Rockwell Automation',
            model='1756-L73',
            equipment_type='PLC',
            user_id='12345'
        )

        # Verify atom was created
        atom = await db_pool.fetchrow(
            """
            SELECT * FROM knowledge_atoms
            WHERE manufacturer = 'Rockwell Automation'
              AND model = '1756-L73'
              AND atom_type = 'SPEC'
            ORDER BY created_at DESC
            LIMIT 1
            """
        )

        assert atom is not None, "SPEC atom should be created after manual found"
        assert atom['confidence'] <= 0.95, "Auto-created atoms should have capped confidence"
        assert 'manual_url' in atom['content']


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
async def db_pool():
    """Provide database connection pool for tests"""
    import asyncpg
    from rivet_pro.config.settings import settings

    pool = await asyncpg.create_pool(settings.database_url)
    yield pool
    await pool.close()


@pytest.fixture
def mock_telegram_update():
    """Mock Telegram Update object for testing bot commands"""
    from unittest.mock import Mock, AsyncMock

    update = Mock()
    update.effective_user = Mock()
    update.effective_user.id = 123456
    update.message = Mock()
    update.message.reply_text = AsyncMock()

    return update


@pytest.fixture
def mock_ocr_result():
    """Mock OCR result from Gemini Vision"""
    return {
        'manufacturer': 'Test Manufacturer',
        'model': 'TEST-MODEL-123',
        'serial_number': 'SN123456',
        'equipment_type': 'Motor'
    }


@pytest.fixture
def bot_app():
    """Provide Telegram bot application for testing"""
    from rivet_pro.adapters.telegram.bot import application
    return application


# ============================================================================
# Performance Tests
# ============================================================================

class TestKBPerformance:
    """Test KB system performance meets requirements"""

    @pytest.mark.asyncio
    async def test_kb_query_under_500ms(self, db_pool):
        """KB queries should complete in under 500ms"""
        import time

        start = time.time()

        # Query KB for common equipment
        result = await db_pool.fetchrow(
            """
            SELECT * FROM knowledge_atoms
            WHERE manufacturer = 'Allen Bradley'
              AND model LIKE '2080%'
            ORDER BY confidence DESC
            LIMIT 1
            """
        )

        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 500, \
            f"KB query took {elapsed_ms:.1f}ms, should be under 500ms"

    @pytest.mark.asyncio
    async def test_atom_creation_under_1s(self, db_pool):
        """Atom creation should complete in under 1 second"""
        import time
        from rivet_pro.core.services.knowledge_service import KnowledgeService

        knowledge_service = KnowledgeService(db_pool)

        start = time.time()

        atom = KnowledgeAtomCreate(
            atom_type='SPEC',
            manufacturer='Test Mfr',
            model='TEST-123',
            equipment_type='Test',
            content='Test manual content',
            keywords=['test', 'manual'],
            confidence=0.9
        )

        await knowledge_service.create_atom(atom)

        elapsed_s = time.time() - start

        assert elapsed_s < 1.0, \
            f"Atom creation took {elapsed_s:.2f}s, should be under 1s"


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == '__main__':
    """Run tests with pytest"""
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])
