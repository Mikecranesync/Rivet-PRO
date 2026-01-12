"""
Manual search service for equipment manuals.
Caches manual URLs in database and searches via n8n Manual Hunter webhook.
"""

from typing import Optional, Dict, Any
import httpx
from datetime import datetime
from rivet_pro.infra.observability import get_logger
from rivet_pro.config.settings import settings

logger = get_logger(__name__)


class ManualService:
    """
    Service for searching and caching equipment manuals.

    Flow:
    1. Check database cache first (instant)
    2. If not cached, call n8n Manual Hunter webhook
    3. Cache successful results for future lookups
    """

    def __init__(self, db):
        """
        Initialize manual service.

        Args:
            db: Database connection pool
        """
        self.db = db
        self.tavily_api_key = settings.tavily_api_key
        self.use_tavily_direct = bool(self.tavily_api_key)

        if not self.use_tavily_direct:
            # Fallback to n8n webhook if no Tavily key
            self.manual_hunter_url = getattr(
                settings,
                'n8n_manual_hunter_url',
                'http://localhost:5678/webhook/manual-hunter'
            )
            logger.warning("Tavily API key not configured - will use n8n Manual Hunter webhook")

    async def search_manual(
        self,
        manufacturer: str,
        model: str,
        timeout: int = 15
    ) -> Optional[Dict[str, Any]]:
        """
        Search for equipment manual. Checks cache first, then external search.

        Args:
            manufacturer: Equipment manufacturer name
            model: Equipment model number
            timeout: Max seconds to wait for external search (default: 15)

        Returns:
            Dict with manual info if found:
            {
                'url': 'https://...',
                'title': 'Manual title',
                'source': 'tavily' | 'cache',
                'cached': bool
            }
            Returns None if not found.
        """
        if not manufacturer or not model:
            logger.warning(f"Missing manufacturer or model | mfr={manufacturer} | model={model}")
            return None

        # Normalize inputs for cache lookup
        mfr_clean = manufacturer.strip()
        model_clean = model.strip()

        # 1. Check cache first
        cached = await self.get_cached_manual(mfr_clean, model_clean)
        if cached:
            logger.info(f"Manual cache HIT | {mfr_clean} {model_clean} | url={cached.get('url')}")
            return {
                'url': cached.get('manual_url'),
                'title': cached.get('manual_title'),
                'source': cached.get('source', 'cache'),
                'cached': True
            }

        # 2. Cache miss - search via n8n
        logger.info(f"Manual cache MISS | {mfr_clean} {model_clean} | Searching via n8n...")

        try:
            result = await self._search_external(mfr_clean, model_clean, timeout)

            if result and result.get('url'):
                # 3. Cache successful result
                await self.cache_manual(
                    manufacturer=mfr_clean,
                    model=model_clean,
                    manual_url=result['url'],
                    manual_title=result.get('title'),
                    source=result.get('source', 'tavily')
                )

                result['cached'] = False
                logger.info(f"Manual found and cached | {mfr_clean} {model_clean}")
                return result

            logger.info(f"Manual not found | {mfr_clean} {model_clean}")
            return None

        except Exception as e:
            logger.error(f"Manual search failed | {mfr_clean} {model_clean} | error={e}")
            return None

    async def get_cached_manual(
        self,
        manufacturer: str,
        model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check database cache for manual.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model number

        Returns:
            Dict with cached manual info or None if not found
        """
        try:
            row = await self.db.fetchrow(
                """
                SELECT
                    manual_url,
                    manual_title,
                    source,
                    verified,
                    found_at,
                    access_count
                FROM manual_cache
                WHERE LOWER(manufacturer) = LOWER($1)
                  AND LOWER(model) = LOWER($2)
                """,
                manufacturer,
                model
            )

            if row:
                # Update access tracking
                await self.db.execute(
                    """
                    UPDATE manual_cache
                    SET last_accessed = NOW(),
                        access_count = access_count + 1
                    WHERE LOWER(manufacturer) = LOWER($1)
                      AND LOWER(model) = LOWER($2)
                    """,
                    manufacturer,
                    model
                )

                return dict(row)

            return None

        except Exception as e:
            logger.error(f"Cache lookup failed | {manufacturer} {model} | error={e}")
            return None

    async def cache_manual(
        self,
        manufacturer: str,
        model: str,
        manual_url: Optional[str],
        manual_title: Optional[str] = None,
        source: str = 'tavily',
        verified: bool = False
    ) -> bool:
        """
        Store manual in database cache.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model number
            manual_url: URL to PDF manual (None if not found)
            manual_title: Title/description of manual
            source: Where manual was found (tavily, manual site, etc)
            verified: Whether URL has been verified to work

        Returns:
            True if cached successfully
        """
        try:
            await self.db.execute(
                """
                INSERT INTO manual_cache
                    (manufacturer, model, manual_url, manual_title, source, verified)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (manufacturer, model)
                DO UPDATE SET
                    manual_url = EXCLUDED.manual_url,
                    manual_title = EXCLUDED.manual_title,
                    source = EXCLUDED.source,
                    verified = EXCLUDED.verified,
                    found_at = NOW(),
                    last_accessed = NOW(),
                    access_count = manual_cache.access_count + 1
                """,
                manufacturer,
                model,
                manual_url,
                manual_title,
                source,
                verified
            )

            logger.info(f"Manual cached | {manufacturer} {model} | url={manual_url}")
            return True

        except Exception as e:
            logger.error(f"Cache write failed | {manufacturer} {model} | error={e}")
            return False

    async def _search_external(
        self,
        manufacturer: str,
        model: str,
        timeout: int
    ) -> Optional[Dict[str, Any]]:
        """
        Search for manual using Tavily API directly or n8n webhook fallback.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model number
            timeout: Request timeout in seconds

        Returns:
            Dict with manual info if found, None otherwise
        """
        if self.use_tavily_direct:
            return await self._search_tavily_direct(manufacturer, model, timeout)
        else:
            return await self._search_via_n8n(manufacturer, model, timeout)

    async def _search_tavily_direct(
        self,
        manufacturer: str,
        model: str,
        timeout: int
    ) -> Optional[Dict[str, Any]]:
        """
        Call Tavily API directly to search for equipment manual.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model number
            timeout: Request timeout in seconds

        Returns:
            Dict with manual info if found, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Build search query optimized for PDF manuals
                query = f"{manufacturer} {model} manual PDF filetype:pdf"

                response = await client.post(
                    "https://api.tavily.com/search",
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": self.tavily_api_key,
                        "query": query,
                        "search_depth": "advanced",
                        "max_results": 5,
                        "include_domains": [
                            "manualslib.com",
                            "siemens.com",
                            "abb.com",
                            "rockwellautomation.com",
                            "schneider-electric.com",
                            "emerson.com",
                            "ge.com",
                            "automation.com"
                        ]
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    # Find first PDF result
                    for result in results:
                        url = result.get('url', '')
                        title = result.get('title', '')

                        # Check if URL is a PDF or contains "manual"
                        is_pdf = url.lower().endswith('.pdf') or 'manual' in url.lower()

                        if is_pdf:
                            logger.info(f"Tavily found manual | {manufacturer} {model} | url={url}")
                            return {
                                'url': url,
                                'title': title or f"{manufacturer} {model} Manual",
                                'source': 'tavily'
                            }

                    logger.info(f"Tavily search returned no PDF results | {manufacturer} {model}")
                    return None

                logger.warning(f"Tavily API returned {response.status_code} | {manufacturer} {model}")
                return None

        except httpx.TimeoutException:
            logger.error(f"Tavily search timeout | {manufacturer} {model} | timeout={timeout}s")
            return None
        except Exception as e:
            logger.error(f"Tavily search failed | {manufacturer} {model} | error={e}")
            return None

    async def _search_via_n8n(
        self,
        manufacturer: str,
        model: str,
        timeout: int
    ) -> Optional[Dict[str, Any]]:
        """
        Call n8n Manual Hunter webhook to search for manual (fallback).

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model number
            timeout: Request timeout in seconds

        Returns:
            Dict with manual info if found, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.manual_hunter_url,
                    json={
                        'manufacturer': manufacturer,
                        'model': model,
                        'query': f"{manufacturer} {model} manual PDF"
                    }
                )

                if response.status_code == 200:
                    data = response.json()

                    # n8n Manual Hunter expected response format:
                    # {
                    #     'found': bool,
                    #     'url': str,
                    #     'title': str,
                    #     'source': str
                    # }

                    if data.get('found') and data.get('url'):
                        return {
                            'url': data['url'],
                            'title': data.get('title', f"{manufacturer} {model} Manual"),
                            'source': data.get('source', 'n8n')
                        }

                    return None

                logger.warning(f"n8n search returned {response.status_code} | {manufacturer} {model}")
                return None

        except httpx.TimeoutException:
            logger.error(f"n8n search timeout | {manufacturer} {model} | timeout={timeout}s")
            return None
        except Exception as e:
            logger.error(f"n8n search failed | {manufacturer} {model} | error={e}")
            return None

    async def get_cache_stats(self) -> Dict[str, int]:
        """
        Get statistics about manual cache.

        Returns:
            Dict with cache statistics
        """
        try:
            stats = await self.db.fetchrow(
                """
                SELECT
                    COUNT(*) as total_cached,
                    COUNT(*) FILTER (WHERE manual_url IS NOT NULL) as manuals_found,
                    COUNT(*) FILTER (WHERE manual_url IS NULL) as not_found,
                    SUM(access_count) as total_accesses
                FROM manual_cache
                """
            )

            return dict(stats) if stats else {}

        except Exception as e:
            logger.error(f"Failed to get cache stats | error={e}")
            return {}
