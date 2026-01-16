"""
Analytics Service for RIVET Pro

Provides daily usage aggregation, KB health metrics, and SME chat analytics.
Supports admin /stats and /report commands.
"""

from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


@dataclass
class DailyStats:
    """Daily aggregated statistics"""
    date: date
    total_queries: int
    unique_users: int
    equipment_lookups: int
    troubleshooting_queries: int
    manual_searches: int
    sme_chat_sessions: int
    avg_response_time_ms: Optional[float]
    success_rate: float


@dataclass
class KBHealthMetrics:
    """Knowledge base health metrics"""
    total_atoms: int
    atoms_by_manufacturer: Dict[str, int]
    coverage_gaps: int
    stale_atoms: int
    avg_confidence: float
    verified_percentage: float


@dataclass
class SMEChatMetrics:
    """SME chat analytics"""
    total_sessions: int
    sessions_by_vendor: Dict[str, int]
    avg_messages_per_session: float
    confidence_distribution: Dict[str, int]
    safety_warnings_count: int


class AnalyticsService:
    """
    Analytics service for usage tracking, KB health, and SME chat metrics.

    Usage:
        analytics = AnalyticsService(db_pool)
        await analytics.aggregate_daily_stats()
        stats = await analytics.get_today_stats()
    """

    def __init__(self, db):
        """
        Initialize analytics service.

        Args:
            db: Database connection pool (asyncpg)
        """
        self.db = db

    async def aggregate_daily_stats(self, target_date: Optional[date] = None) -> DailyStats:
        """
        Aggregate usage statistics for a specific date.

        Args:
            target_date: Date to aggregate (defaults to yesterday)

        Returns:
            DailyStats object with aggregated metrics
        """
        if target_date is None:
            target_date = (datetime.utcnow() - timedelta(days=1)).date()

        logger.info(f"Aggregating daily stats for {target_date}")

        try:
            # Get interactions for the target date
            stats = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) as total_queries,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(*) FILTER (WHERE interaction_type IN ('manual_lookup', 'equipment_create')) as equipment_lookups,
                    COUNT(*) FILTER (WHERE interaction_type = 'troubleshoot') as troubleshooting_queries,
                    COUNT(*) FILTER (WHERE interaction_type = 'chat_with_manual') as manual_searches,
                    AVG(response_time_seconds * 1000) as avg_response_time_ms,
                    COUNT(*) FILTER (WHERE outcome IN ('resolved', 'manual_delivered', 'equipment_created')) * 100.0 / NULLIF(COUNT(*), 0) as success_rate
                FROM interactions
                WHERE DATE(created_at) = $1
                """,
                target_date
            )

            # Get SME chat sessions for the date
            sme_sessions = await self.db.fetchval(
                """
                SELECT COUNT(*)
                FROM sme_chat_sessions
                WHERE DATE(created_at) = $1
                """,
                target_date
            ) or 0

            daily_stats = DailyStats(
                date=target_date,
                total_queries=stats['total_queries'] or 0,
                unique_users=stats['unique_users'] or 0,
                equipment_lookups=stats['equipment_lookups'] or 0,
                troubleshooting_queries=stats['troubleshooting_queries'] or 0,
                manual_searches=stats['manual_searches'] or 0,
                sme_chat_sessions=sme_sessions,
                avg_response_time_ms=float(stats['avg_response_time_ms']) if stats['avg_response_time_ms'] else None,
                success_rate=float(stats['success_rate']) if stats['success_rate'] else 0.0
            )

            # Upsert into daily_stats table
            await self.db.execute(
                """
                INSERT INTO daily_stats (date, total_lookups, new_users, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (date) DO UPDATE SET
                    total_lookups = EXCLUDED.total_lookups,
                    created_at = NOW()
                """,
                target_date,
                daily_stats.total_queries,
                daily_stats.unique_users
            )

            logger.info(f"Daily stats aggregated | date={target_date} | queries={daily_stats.total_queries} | users={daily_stats.unique_users}")
            return daily_stats

        except Exception as e:
            logger.error(f"Failed to aggregate daily stats | date={target_date} | error={e}")
            raise

    async def get_today_stats(self) -> Dict[str, Any]:
        """
        Get real-time stats for today (not aggregated, direct query).

        Returns:
            Dict with today's statistics
        """
        today = datetime.utcnow().date()

        try:
            # Interactions today
            interactions = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) as total_queries,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(*) FILTER (WHERE interaction_type IN ('manual_lookup', 'equipment_create')) as equipment_lookups,
                    COUNT(*) FILTER (WHERE interaction_type = 'troubleshoot') as troubleshooting,
                    COUNT(*) FILTER (WHERE interaction_type = 'chat_with_manual') as manual_searches
                FROM interactions
                WHERE DATE(created_at) = $1
                """,
                today
            )

            # SME sessions today
            sme_sessions = await self.db.fetchval(
                """
                SELECT COUNT(*) FROM sme_chat_sessions
                WHERE DATE(created_at) = $1
                """,
                today
            ) or 0

            # Top equipment lookups
            top_equipment = await self.db.fetch(
                """
                SELECT
                    em.manufacturer,
                    em.model_number,
                    COUNT(*) as lookup_count
                FROM interactions i
                JOIN equipment_models em ON i.equipment_model_id = em.id
                WHERE DATE(i.created_at) = $1
                  AND i.equipment_model_id IS NOT NULL
                GROUP BY em.manufacturer, em.model_number
                ORDER BY lookup_count DESC
                LIMIT 5
                """,
                today
            )

            # KB atom count
            atom_count = await self.db.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms"
            ) or 0

            return {
                'date': today.isoformat(),
                'queries_today': interactions['total_queries'] or 0,
                'unique_users_today': interactions['unique_users'] or 0,
                'equipment_lookups': interactions['equipment_lookups'] or 0,
                'troubleshooting': interactions['troubleshooting'] or 0,
                'manual_searches': interactions['manual_searches'] or 0,
                'sme_sessions': sme_sessions,
                'top_equipment': [
                    {'manufacturer': r['manufacturer'], 'model': r['model_number'], 'count': r['lookup_count']}
                    for r in top_equipment
                ],
                'kb_atom_count': atom_count
            }

        except Exception as e:
            logger.error(f"Failed to get today stats | error={e}")
            return {
                'date': today.isoformat(),
                'queries_today': 0,
                'unique_users_today': 0,
                'error': str(e)
            }

    async def get_kb_health(self) -> KBHealthMetrics:
        """
        Get knowledge base health metrics.

        Returns:
            KBHealthMetrics with atom stats, coverage, and freshness
        """
        try:
            # Total atoms
            total = await self.db.fetchval("SELECT COUNT(*) FROM knowledge_atoms") or 0

            # Atoms by manufacturer
            by_manufacturer = await self.db.fetch(
                """
                SELECT manufacturer, COUNT(*) as count
                FROM knowledge_atoms
                WHERE manufacturer IS NOT NULL
                GROUP BY manufacturer
                ORDER BY count DESC
                """
            )
            atoms_by_manufacturer = {r['manufacturer']: r['count'] for r in by_manufacturer}

            # Coverage gaps (queries with no KB match in last 7 days)
            coverage_gaps = await self.db.fetchval(
                """
                SELECT COUNT(*)
                FROM interactions
                WHERE created_at > NOW() - INTERVAL '7 days'
                  AND atom_id IS NULL
                  AND interaction_type IN ('manual_lookup', 'troubleshoot')
                """
            ) or 0

            # Stale atoms (not accessed in 30+ days)
            stale_atoms = await self.db.fetchval(
                """
                SELECT COUNT(*)
                FROM knowledge_atoms
                WHERE last_used_at < NOW() - INTERVAL '30 days'
                   OR last_used_at IS NULL
                """
            ) or 0

            # Average confidence
            avg_confidence = await self.db.fetchval(
                "SELECT AVG(confidence) FROM knowledge_atoms"
            ) or 0.0

            # Verified percentage
            verified = await self.db.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms WHERE human_verified = true"
            ) or 0
            verified_pct = (verified / total * 100) if total > 0 else 0.0

            return KBHealthMetrics(
                total_atoms=total,
                atoms_by_manufacturer=atoms_by_manufacturer,
                coverage_gaps=coverage_gaps,
                stale_atoms=stale_atoms,
                avg_confidence=float(avg_confidence),
                verified_percentage=verified_pct
            )

        except Exception as e:
            logger.error(f"Failed to get KB health | error={e}")
            return KBHealthMetrics(
                total_atoms=0,
                atoms_by_manufacturer={},
                coverage_gaps=0,
                stale_atoms=0,
                avg_confidence=0.0,
                verified_percentage=0.0
            )

    async def get_sme_chat_analytics(self, days: int = 7) -> SMEChatMetrics:
        """
        Get SME chat usage analytics.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            SMEChatMetrics with session and message stats
        """
        since_date = datetime.utcnow() - timedelta(days=days)

        try:
            # Total sessions
            total_sessions = await self.db.fetchval(
                """
                SELECT COUNT(*) FROM sme_chat_sessions
                WHERE created_at > $1
                """,
                since_date
            ) or 0

            # Sessions by vendor
            by_vendor = await self.db.fetch(
                """
                SELECT vendor, COUNT(*) as count
                FROM sme_chat_sessions
                WHERE created_at > $1
                GROUP BY vendor
                ORDER BY count DESC
                """,
                since_date
            )
            sessions_by_vendor = {r['vendor']: r['count'] for r in by_vendor}

            # Average messages per session
            avg_messages = await self.db.fetchval(
                """
                SELECT AVG(message_count) FROM (
                    SELECT session_id, COUNT(*) as message_count
                    FROM sme_chat_messages
                    WHERE created_at > $1
                    GROUP BY session_id
                ) subq
                """,
                since_date
            ) or 0.0

            # Confidence distribution
            confidence_dist = await self.db.fetch(
                """
                SELECT confidence_level, COUNT(*) as count
                FROM sme_chat_messages
                WHERE created_at > $1
                  AND role = 'assistant'
                  AND confidence_level IS NOT NULL
                GROUP BY confidence_level
                """,
                since_date
            )
            confidence_distribution = {r['confidence_level']: r['count'] for r in confidence_dist}

            # Safety warnings count
            safety_warnings = await self.db.fetchval(
                """
                SELECT COUNT(*)
                FROM sme_chat_messages
                WHERE created_at > $1
                  AND safety_warnings IS NOT NULL
                  AND jsonb_array_length(safety_warnings) > 0
                """,
                since_date
            ) or 0

            return SMEChatMetrics(
                total_sessions=total_sessions,
                sessions_by_vendor=sessions_by_vendor,
                avg_messages_per_session=float(avg_messages),
                confidence_distribution=confidence_distribution,
                safety_warnings_count=safety_warnings
            )

        except Exception as e:
            logger.error(f"Failed to get SME chat analytics | error={e}")
            return SMEChatMetrics(
                total_sessions=0,
                sessions_by_vendor={},
                avg_messages_per_session=0.0,
                confidence_distribution={},
                safety_warnings_count=0
            )

    async def generate_weekly_report(self) -> str:
        """
        Generate a weekly analytics report for Telegram.

        Returns:
            Formatted Telegram Markdown string
        """
        try:
            # This week vs last week
            today = datetime.utcnow().date()
            week_start = today - timedelta(days=7)
            last_week_start = today - timedelta(days=14)

            # This week stats
            this_week = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) as queries,
                    COUNT(DISTINCT user_id) as users
                FROM interactions
                WHERE DATE(created_at) >= $1
                """,
                week_start
            )

            # Last week stats
            last_week = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) as queries,
                    COUNT(DISTINCT user_id) as users
                FROM interactions
                WHERE DATE(created_at) >= $1 AND DATE(created_at) < $2
                """,
                last_week_start, week_start
            )

            # Trend arrows
            def trend(current, previous):
                if current > previous:
                    return "📈"
                elif current < previous:
                    return "📉"
                return "➡️"

            queries_trend = trend(this_week['queries'] or 0, last_week['queries'] or 0)
            users_trend = trend(this_week['users'] or 0, last_week['users'] or 0)

            # Top unanswered queries (knowledge gaps)
            gaps = await self.db.fetch(
                """
                SELECT
                    ocr_raw_text as query,
                    COUNT(*) as count
                FROM interactions
                WHERE created_at > NOW() - INTERVAL '7 days'
                  AND atom_id IS NULL
                  AND outcome = 'manual_not_found'
                  AND ocr_raw_text IS NOT NULL
                GROUP BY ocr_raw_text
                ORDER BY count DESC
                LIMIT 10
                """
            )

            # SME vendor ranking
            sme_stats = await self.get_sme_chat_analytics(days=7)

            # KB health
            kb_health = await self.get_kb_health()

            # Build report
            report = "📊 *Weekly Analytics Report*\n"
            report += f"_{week_start.isoformat()} to {today.isoformat()}_\n"
            report += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

            # Usage trends
            report += "*📈 Usage Trends*\n"
            report += f"  Queries: {this_week['queries'] or 0:,} {queries_trend}\n"
            report += f"  Users: {this_week['users'] or 0:,} {users_trend}\n\n"

            # SME Chat
            report += "*💬 SME Chat*\n"
            report += f"  Sessions: {sme_stats.total_sessions}\n"
            if sme_stats.sessions_by_vendor:
                report += "  By vendor:\n"
                for vendor, count in list(sme_stats.sessions_by_vendor.items())[:3]:
                    report += f"    • {vendor}: {count}\n"
            report += "\n"

            # KB Health
            report += "*📚 Knowledge Base*\n"
            report += f"  Atoms: {kb_health.total_atoms:,}\n"
            report += f"  Confidence: {kb_health.avg_confidence:.1%}\n"
            report += f"  Coverage gaps: {kb_health.coverage_gaps}\n\n"

            # Knowledge gaps
            if gaps:
                report += "*🔍 Top Unanswered Queries*\n"
                for gap in gaps[:5]:
                    query = gap['query'][:35] + "..." if len(gap['query']) > 35 else gap['query']
                    report += f"  • {query} (×{gap['count']})\n"
                report += "\n"

            report += f"_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_"

            return report

        except Exception as e:
            logger.error(f"Failed to generate weekly report | error={e}")
            return f"❌ *Report Generation Failed*\n\nError: {str(e)[:100]}"

    async def get_response_time_stats(self) -> Dict[str, Any]:
        """
        Get response time statistics from rivet_usage_log.

        Returns:
            Dict with avg_ms, slow_count, and total_count
        """
        today = datetime.utcnow().date()

        try:
            stats = await self.db.fetchrow(
                """
                SELECT
                    AVG(latency_ms) as avg_ms,
                    COUNT(*) FILTER (WHERE latency_ms > 5000) as slow_count,
                    COUNT(*) as total_count
                FROM rivet_usage_log
                WHERE DATE(created_at) = $1
                  AND latency_ms IS NOT NULL
                """,
                today
            )

            return {
                'avg_ms': float(stats['avg_ms']) if stats['avg_ms'] else None,
                'slow_count': stats['slow_count'] or 0,
                'total_count': stats['total_count'] or 0
            }

        except Exception as e:
            logger.error(f"Failed to get response time stats | error={e}")
            return {'avg_ms': None, 'slow_count': 0, 'total_count': 0}

    async def format_stats_message(self) -> str:
        """
        Format today's stats as a Telegram message for /stats command.

        Returns:
            Formatted Telegram Markdown string
        """
        stats = await self.get_today_stats()
        response_stats = await self.get_response_time_stats()

        msg = "📊 *RIVET Pro Stats*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        msg += "*Today's Activity*\n"
        msg += f"  Queries: {stats['queries_today']}\n"
        msg += f"  Users: {stats['unique_users_today']}\n"
        msg += f"  SME Chats: {stats['sme_sessions']}\n\n"

        msg += "*By Category*\n"
        msg += f"  Equipment: {stats['equipment_lookups']}\n"
        msg += f"  Troubleshooting: {stats['troubleshooting']}\n"
        msg += f"  Manuals: {stats['manual_searches']}\n\n"

        if stats.get('top_equipment'):
            msg += "*Top Equipment*\n"
            for eq in stats['top_equipment'][:3]:
                msg += f"  • {eq['manufacturer']} {eq['model']} ({eq['count']})\n"
            msg += "\n"

        # Response time stats (ANALYTICS-006)
        msg += "*Performance*\n"
        if response_stats['avg_ms'] is not None:
            avg_sec = response_stats['avg_ms'] / 1000
            msg += f"  Avg Response: {avg_sec:.2f}s\n"
            if response_stats['slow_count'] > 0:
                msg += f"  Slow (>5s): {response_stats['slow_count']} ⚠️\n"
        else:
            msg += "  Avg Response: --\n"
        msg += "\n"

        msg += f"*KB Atoms:* {stats['kb_atom_count']:,}\n"
        msg += f"\n_Updated: {datetime.utcnow().strftime('%H:%M UTC')}_"

        return msg
