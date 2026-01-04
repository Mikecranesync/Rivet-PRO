"""
VPS Knowledge Base Client for RIVET Pro

Provides unified interface for querying the VPS KB Factory database
running on Hostinger VPS (72.60.175.144).

Features:
- Keyword search across atoms
- Semantic search with pgvector embeddings
- Equipment-specific queries
- Connection pooling for performance
- Automatic fallback (VPS down -> graceful degradation)
- Health monitoring

Usage:
    >>> from agent_factory.rivet_pro.vps_kb_client import VPSKBClient
    >>> client = VPSKBClient()
    >>> atoms = client.query_atoms("motor overheating", limit=5)
    >>> print(f"Found {len(atoms)} atoms")

Configuration:
    Set these environment variables in .env:
    - VPS_KB_HOST (default: 72.60.175.144)
    - VPS_KB_PORT (default: 5432)
    - VPS_KB_USER (default: rivet)
    - VPS_KB_PASSWORD (required)
    - VPS_KB_DATABASE (default: rivet)
    - VPS_OLLAMA_URL (default: http://72.60.175.144:11434)

Created: 2025-12-15
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class VPSKBClient:
    """
    Client for querying VPS Knowledge Base Factory.

    Manages connections to PostgreSQL database on VPS and provides
    high-level query methods for knowledge atom retrieval.
    """

    def __init__(self):
        """Initialize VPS KB Client with connection pool"""

        # VPS connection config
        self.config = {
            'host': os.getenv('VPS_KB_HOST', '72.60.175.144'),
            'port': int(os.getenv('VPS_KB_PORT', 5432)),
            'user': os.getenv('VPS_KB_USER', 'rivet'),
            'password': os.getenv('VPS_KB_PASSWORD', ''),
            'database': os.getenv('VPS_KB_DATABASE', 'rivet'),
        }

        # Ollama for embeddings
        self.ollama_url = os.getenv('VPS_OLLAMA_URL', 'http://72.60.175.144:11434')

        # Connection pool (reuse connections for performance)
        self.pool = None
        self._init_pool()

        # Cache for health checks (avoid hammering VPS)
        self._last_health_check = None
        self._health_status = None
        self._health_cache_duration = timedelta(minutes=1)

    def _init_pool(self):
        """Initialize connection pool"""
        try:
            self.pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                dbname=self.config['database'],
                cursor_factory=RealDictCursor,
                connect_timeout=5  # 5 second timeout
            )
            logger.info(f"VPS KB connection pool initialized ({self.config['host']})")
        except Exception as e:
            logger.error(f"Failed to initialize VPS KB connection pool: {e}")
            self.pool = None

    def _get_connection(self):
        """Get connection from pool"""
        if not self.pool:
            raise ConnectionError("VPS KB connection pool not initialized")

        try:
            return self.pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise

    def _return_connection(self, conn):
        """Return connection to pool"""
        if self.pool and conn:
            self.pool.putconn(conn)

    def health_check(self) -> Dict[str, Any]:
        """
        Check VPS KB Factory health status.

        Returns cached result if checked within last minute.

        Returns:
            Dict with health status:
            {
                "status": "healthy" | "degraded" | "down",
                "database_connected": bool,
                "atom_count": int,
                "last_ingestion": str (ISO timestamp),
                "ollama_available": bool,
                "response_time_ms": int,
                "checked_at": str (ISO timestamp)
            }
        """
        # Return cached result if fresh
        if self._last_health_check and self._health_status:
            elapsed = datetime.now() - self._last_health_check
            if elapsed < self._health_cache_duration:
                logger.debug(f"Returning cached health status ({elapsed.seconds}s old)")
                return self._health_status

        # Perform fresh health check
        start_time = datetime.now()
        health = {
            "status": "unknown",
            "database_connected": False,
            "atom_count": 0,
            "last_ingestion": None,
            "ollama_available": False,
            "response_time_ms": 0,
            "checked_at": start_time.isoformat()
        }

        # Test database connection
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Count atoms
                cur.execute("SELECT COUNT(*) as count FROM knowledge_atoms")
                result = cur.fetchone()
                health["atom_count"] = result["count"] if result else 0

                # Get last ingestion timestamp
                cur.execute("""
                    SELECT MAX(created_at) as last_ingestion
                    FROM knowledge_atoms
                """)
                result = cur.fetchone()
                if result and result["last_ingestion"]:
                    health["last_ingestion"] = result["last_ingestion"].isoformat()

            self._return_connection(conn)
            health["database_connected"] = True
            logger.info(f"VPS KB health check: {health['atom_count']} atoms available")

        except Exception as e:
            logger.error(f"VPS KB health check failed (database): {e}")
            health["database_connected"] = False

        # Test Ollama availability
        try:
            import requests
            response = requests.get(
                f"{self.ollama_url}/api/tags",
                timeout=5
            )
            health["ollama_available"] = response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            health["ollama_available"] = False

        # Calculate response time
        end_time = datetime.now()
        health["response_time_ms"] = int((end_time - start_time).total_seconds() * 1000)

        # Determine overall status
        if health["database_connected"] and health["atom_count"] > 0:
            health["status"] = "healthy"
        elif health["database_connected"]:
            health["status"] = "degraded"  # Connected but no atoms
        else:
            health["status"] = "down"

        # Cache result
        self._last_health_check = datetime.now()
        self._health_status = health

        return health

    def query_atoms(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query atoms using keyword search.

        Searches across title, summary, content, and keywords fields.

        Args:
            topic: Topic keyword to search for
            limit: Maximum number of atoms to return

        Returns:
            List of atom dictionaries sorted by relevance

        Example:
            >>> client = VPSKBClient()
            >>> atoms = client.query_atoms("ControlLogix", limit=3)
            >>> for atom in atoms:
            ...     print(atom['title'])
        """
        try:
            conn = self._get_connection()

            with conn.cursor() as cur:
                query = """
                    SELECT atom_id, atom_type, vendor, product, title, summary,
                           content, code, symptoms, causes, fixes, pattern_type,
                           prerequisites, steps, keywords, difficulty,
                           source_url, source_pages, created_at
                    FROM knowledge_atoms
                    WHERE title ILIKE %s
                       OR summary ILIKE %s
                       OR content ILIKE %s
                       OR %s = ANY(keywords)
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                search_pattern = f'%{topic}%'
                cur.execute(query, (
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    topic.lower(),
                    limit
                ))

                atoms = [dict(row) for row in cur.fetchall()]

            self._return_connection(conn)

            logger.info(f"Keyword search '{topic}' returned {len(atoms)} atoms")
            return atoms

        except Exception as e:
            logger.error(f"Failed to query atoms for topic '{topic}': {e}")
            return []

    def search_by_equipment(
        self,
        equipment_type: Optional[str] = None,
        manufacturer: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search atoms by equipment type and/or manufacturer.

        Args:
            equipment_type: Type of equipment (motor, vfd, plc, etc.)
            manufacturer: Manufacturer name (allen_bradley, siemens, etc.)
            limit: Maximum number of atoms to return

        Returns:
            List of matching atoms

        Example:
            >>> atoms = client.search_by_equipment(
            ...     equipment_type="plc",
            ...     manufacturer="allen_bradley"
            ... )
        """
        if not equipment_type and not manufacturer:
            logger.warning("search_by_equipment called without filters")
            return []

        try:
            conn = self._get_connection()

            # Build dynamic query based on filters
            conditions = []
            params = []

            if equipment_type:
                conditions.append("title ILIKE %s OR content ILIKE %s OR %s = ANY(keywords)")
                eq_pattern = f'%{equipment_type}%'
                params.extend([eq_pattern, eq_pattern, equipment_type.lower()])

            if manufacturer:
                conditions.append("vendor = %s")
                params.append(manufacturer.lower())

            query = f"""
                SELECT atom_id, atom_type, vendor, product, title, summary,
                       content, code, symptoms, causes, fixes, pattern_type,
                       prerequisites, steps, keywords, difficulty,
                       source_url, source_pages, created_at
                FROM knowledge_atoms
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT %s
            """
            params.append(limit)

            with conn.cursor() as cur:
                cur.execute(query, params)
                atoms = [dict(row) for row in cur.fetchall()]

            self._return_connection(conn)

            logger.info(f"Equipment search (type={equipment_type}, mfr={manufacturer}) "
                       f"returned {len(atoms)} atoms")
            return atoms

        except Exception as e:
            logger.error(f"Failed to search by equipment: {e}")
            return []

    def query_atoms_semantic(
        self,
        query_text: str,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Query atoms using semantic search with pgvector embeddings.

        Uses Ollama on VPS to generate query embedding, then searches
        for similar atoms using cosine similarity.

        Args:
            query_text: Natural language query
            limit: Maximum number of atoms to return
            similarity_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of atoms sorted by similarity (highest first)

        Note:
            Requires Ollama running on VPS with nomic-embed-text model.
            Falls back to keyword search if embeddings fail.
        """
        try:
            import requests

            # Generate embedding for query using Ollama
            embedding_response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": query_text
                },
                timeout=10
            )

            if embedding_response.status_code != 200:
                logger.warning(f"Ollama embedding failed: {embedding_response.status_code}")
                # Fallback to keyword search
                return self.query_atoms(query_text, limit)

            query_embedding = embedding_response.json()["embedding"]

            # Search for similar atoms using pgvector
            conn = self._get_connection()

            with conn.cursor() as cur:
                query = """
                    SELECT atom_id, atom_type, vendor, product, title, summary,
                           content, code, symptoms, causes, fixes, pattern_type,
                           prerequisites, steps, keywords, difficulty,
                           source_url, source_pages, created_at,
                           1 - (embedding <=> %s::vector) as similarity
                    FROM knowledge_atoms
                    WHERE embedding IS NOT NULL
                      AND 1 - (embedding <=> %s::vector) >= %s
                    ORDER BY similarity DESC
                    LIMIT %s
                """

                # Convert embedding to PostgreSQL vector format
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

                cur.execute(query, (
                    embedding_str,
                    embedding_str,
                    similarity_threshold,
                    limit
                ))

                atoms = [dict(row) for row in cur.fetchall()]

            self._return_connection(conn)

            logger.info(f"Semantic search '{query_text[:50]}...' returned "
                       f"{len(atoms)} atoms (threshold={similarity_threshold})")
            return atoms

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            # Fallback to keyword search
            logger.info("Falling back to keyword search")
            return self.query_atoms(query_text, limit)

    def close(self):
        """Close all connections in pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("VPS KB connection pool closed")
