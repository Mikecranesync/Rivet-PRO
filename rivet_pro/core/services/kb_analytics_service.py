"""
Knowledge Base Analytics Service

Tracks KB learning effectiveness, usage patterns, and performance metrics.
Used for monitoring KB growth and quality over time.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class KnowledgeBaseAnalytics:
    """Analytics service for knowledge base learning and effectiveness"""

    def __init__(self, db_pool):
        """
        Initialize KB analytics service.

        Args:
            db_pool: asyncpg connection pool
        """
        self.db = db_pool

    async def get_learning_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive KB learning statistics.

        Returns:
            Dict containing:
            - total_atoms: Total number of knowledge atoms
            - atoms_by_source: Breakdown by source (feedback/system/research)
            - verified_atoms: Count of human-verified atoms
            - gaps_detected: Number of knowledge gaps identified
            - gaps_resolved: Number of gaps that have been filled
            - avg_confidence: Average confidence score across all atoms
            - most_used_atoms: Top 5 most frequently accessed atoms
        """
        try:
            # Get total atoms
            total_atoms = await self.db.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms"
            )

            # Get atoms by source
            source_breakdown = await self.db.fetch(
                """
                SELECT
                    source_type,
                    COUNT(*) as count
                FROM knowledge_atoms
                GROUP BY source_type
                ORDER BY count DESC
                """
            )

            atoms_by_source = {row['source_type']: row['count'] for row in source_breakdown}

            # Get verified atoms count
            verified_atoms = await self.db.fetchval(
                "SELECT COUNT(*) FROM knowledge_atoms WHERE human_verified = true"
            )

            # Get knowledge gaps stats
            gaps_stats = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE resolved = false) as gaps_detected,
                    COUNT(*) FILTER (WHERE resolved = true) as gaps_resolved
                FROM knowledge_gaps
                """
            )

            # Get average confidence
            avg_confidence = await self.db.fetchval(
                "SELECT AVG(confidence) FROM knowledge_atoms"
            ) or 0.0

            # Get most used atoms
            most_used = await self.db.fetch(
                """
                SELECT
                    id,
                    manufacturer,
                    model,
                    atom_type,
                    usage_count,
                    confidence
                FROM knowledge_atoms
                WHERE usage_count > 0
                ORDER BY usage_count DESC
                LIMIT 5
                """
            )

            most_used_atoms = [
                {
                    'id': str(row['id']),
                    'manufacturer': row['manufacturer'],
                    'model': row['model'],
                    'type': row['atom_type'],
                    'usage_count': row['usage_count'],
                    'confidence': float(row['confidence'])
                }
                for row in most_used
            ]

            return {
                'total_atoms': total_atoms,
                'atoms_by_source': atoms_by_source,
                'verified_atoms': verified_atoms,
                'gaps_detected': gaps_stats['gaps_detected'] if gaps_stats else 0,
                'gaps_resolved': gaps_stats['gaps_resolved'] if gaps_stats else 0,
                'avg_confidence': float(avg_confidence),
                'most_used_atoms': most_used_atoms
            }

        except Exception as e:
            logger.error(f"Failed to get learning stats | error={e}")
            return {
                'total_atoms': 0,
                'atoms_by_source': {},
                'verified_atoms': 0,
                'gaps_detected': 0,
                'gaps_resolved': 0,
                'avg_confidence': 0.0,
                'most_used_atoms': []
            }

    async def get_atom_effectiveness(self, atom_id: str) -> Dict[str, Any]:
        """
        Get effectiveness metrics for a specific atom.

        Args:
            atom_id: UUID of the knowledge atom

        Returns:
            Dict containing:
            - usage_count: How many times atom has been used
            - avg_confidence: Confidence score
            - feedback_count: Number of feedback interactions
            - gap_fill_success: Whether atom successfully filled a gap
            - last_used_at: Timestamp of last usage
        """
        try:
            atom = await self.db.fetchrow(
                """
                SELECT
                    usage_count,
                    confidence,
                    human_verified,
                    created_at,
                    last_used_at
                FROM knowledge_atoms
                WHERE id = $1
                """,
                atom_id
            )

            if not atom:
                return None

            # Get feedback count for this atom
            feedback_count = await self.db.fetchval(
                """
                SELECT COUNT(*)
                FROM interactions
                WHERE atom_id = $1
                  AND interaction_type = 'feedback'
                """,
                atom_id
            )

            # Check if atom filled a gap
            gap_fill_success = await self.db.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1 FROM knowledge_gaps
                    WHERE resolved_by_atom_id = $1
                      AND resolved = true
                )
                """,
                atom_id
            )

            return {
                'usage_count': atom['usage_count'],
                'avg_confidence': float(atom['confidence']),
                'human_verified': atom['human_verified'],
                'feedback_count': feedback_count or 0,
                'gap_fill_success': gap_fill_success,
                'created_at': atom['created_at'].isoformat() if atom['created_at'] else None,
                'last_used_at': atom['last_used_at'].isoformat() if atom['last_used_at'] else None
            }

        except Exception as e:
            logger.error(f"Failed to get atom effectiveness | atom_id={atom_id} | error={e}")
            return None

    async def get_kb_hit_rate(self, days=7) -> float:
        """
        Calculate KB hit rate - percentage of queries answered from KB vs external search.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Float representing hit rate percentage (0-100)
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)

            stats = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) FILTER (WHERE atom_id IS NOT NULL) as kb_hits,
                    COUNT(*) FILTER (WHERE atom_id IS NULL) as external_searches,
                    COUNT(*) as total_queries
                FROM interactions
                WHERE interaction_type IN ('equipment_lookup', 'manual_search')
                  AND created_at > $1
                """,
                since_date
            )

            if not stats or stats['total_queries'] == 0:
                return 0.0

            kb_hits = stats['kb_hits'] or 0
            total = stats['total_queries']

            hit_rate = (kb_hits / total) * 100.0
            return round(hit_rate, 2)

        except Exception as e:
            logger.error(f"Failed to calculate KB hit rate | error={e}")
            return 0.0

    async def get_response_time_comparison(self, days=7) -> Dict[str, float]:
        """
        Compare average response times for KB queries vs external search.

        Args:
            days: Number of days to analyze (default: 7)

        Returns:
            Dict with:
            - kb_avg_ms: Average response time for KB queries (milliseconds)
            - external_avg_ms: Average response time for external searches (milliseconds)
            - speedup_factor: How much faster KB is than external (multiplier)
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)

            # Get average response times
            stats = await self.db.fetchrow(
                """
                SELECT
                    AVG(response_time_ms) FILTER (WHERE atom_id IS NOT NULL) as kb_avg,
                    AVG(response_time_ms) FILTER (WHERE atom_id IS NULL) as external_avg
                FROM interactions
                WHERE interaction_type IN ('equipment_lookup', 'manual_search')
                  AND created_at > $1
                  AND response_time_ms IS NOT NULL
                """,
                since_date
            )

            kb_avg = float(stats['kb_avg']) if stats and stats['kb_avg'] else 500.0
            external_avg = float(stats['external_avg']) if stats and stats['external_avg'] else 3000.0

            speedup_factor = external_avg / kb_avg if kb_avg > 0 else 1.0

            return {
                'kb_avg_ms': round(kb_avg, 2),
                'external_avg_ms': round(external_avg, 2),
                'speedup_factor': round(speedup_factor, 2)
            }

        except Exception as e:
            logger.error(f"Failed to get response time comparison | error={e}")
            return {
                'kb_avg_ms': 0.0,
                'external_avg_ms': 0.0,
                'speedup_factor': 1.0
            }

    async def get_atoms_created_today(self) -> int:
        """Get count of atoms created today"""
        try:
            count = await self.db.fetchval(
                """
                SELECT COUNT(*)
                FROM knowledge_atoms
                WHERE DATE(created_at) = CURRENT_DATE
                """
            )
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get atoms created today | error={e}")
            return 0

    async def get_pending_gaps_count(self) -> int:
        """Get count of unresolved knowledge gaps"""
        try:
            count = await self.db.fetchval(
                "SELECT COUNT(*) FROM knowledge_gaps WHERE resolved = false"
            )
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get pending gaps count | error={e}")
            return 0
