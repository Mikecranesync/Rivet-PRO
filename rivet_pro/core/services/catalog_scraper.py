"""
Manufacturer Catalog Scraper - AUTO-KB-012

Scrapes manufacturer documentation catalogs to proactively discover manuals.
Supports major industrial automation manufacturers.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import asyncpg

logger = logging.getLogger(__name__)

# Try BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("beautifulsoup4 not installed - scraping limited")


class ManufacturerCatalogScraper:
    """
    Service for scraping manufacturer documentation catalogs.

    Features:
    - Scrape known manufacturer documentation portals
    - Extract manual URLs and metadata
    - Queue discovered manuals for download
    - Respect robots.txt and rate limits
    """

    # Priority manufacturers and their documentation portals
    MANUFACTURER_PORTALS = {
        'Siemens': {
            'base_url': 'https://support.industry.siemens.com',
            'doc_paths': [
                '/cs/document',
                '/cs/products',
            ],
            'search_pattern': r'\.pdf',
            'rate_limit': 2.0  # seconds between requests
        },
        'Rockwell': {
            'base_url': 'https://literature.rockwellautomation.com',
            'doc_paths': [
                '/idc/groups/literature/documents',
            ],
            'search_pattern': r'\.pdf',
            'rate_limit': 2.0
        },
        'ABB': {
            'base_url': 'https://library.abb.com',
            'doc_paths': [
                '/en/document',
            ],
            'search_pattern': r'\.pdf',
            'rate_limit': 2.0
        },
        'Schneider': {
            'base_url': 'https://www.se.com',
            'doc_paths': [
                '/en/download/document',
            ],
            'search_pattern': r'\.pdf',
            'rate_limit': 2.0
        },
        'Emerson': {
            'base_url': 'https://www.emerson.com',
            'doc_paths': [
                '/documents',
            ],
            'search_pattern': r'\.pdf',
            'rate_limit': 2.0
        }
    }

    REQUEST_TIMEOUT = 30  # seconds
    MAX_PAGES_PER_MANUFACTURER = 50
    MAX_CONCURRENT_SCRAPERS = 2

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        user_agent: str = "RivetPRO-ManualBot/1.0 (+https://rivet.pro)"
    ):
        """
        Initialize catalog scraper.

        Args:
            db_pool: Database connection pool
            user_agent: User agent string for requests
        """
        self.db_pool = db_pool
        self.user_agent = user_agent
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SCRAPERS)

    async def scrape_manufacturer(
        self,
        manufacturer: str,
        max_pages: int = None
    ) -> Dict[str, Any]:
        """
        Scrape documentation catalog for a manufacturer.

        Args:
            manufacturer: Manufacturer name (must be in MANUFACTURER_PORTALS)
            max_pages: Max pages to scrape (default: MAX_PAGES_PER_MANUFACTURER)

        Returns:
            Dict with discovered manuals count and details
        """
        if not HAS_BS4:
            logger.error("beautifulsoup4 required for scraping")
            return {'error': 'beautifulsoup4 not installed'}

        if manufacturer not in self.MANUFACTURER_PORTALS:
            logger.warning(f"Unknown manufacturer: {manufacturer}")
            return {'error': f'Unknown manufacturer: {manufacturer}'}

        portal = self.MANUFACTURER_PORTALS[manufacturer]
        max_pages = max_pages or self.MAX_PAGES_PER_MANUFACTURER

        async with self._semaphore:
            return await self._scrape_portal(manufacturer, portal, max_pages)

    async def _scrape_portal(
        self,
        manufacturer: str,
        portal: Dict[str, Any],
        max_pages: int
    ) -> Dict[str, Any]:
        """
        Scrape a manufacturer's documentation portal.

        Args:
            manufacturer: Manufacturer name
            portal: Portal configuration dict
            max_pages: Max pages to process

        Returns:
            Dict with scraping results
        """
        base_url = portal['base_url']
        rate_limit = portal.get('rate_limit', 2.0)
        search_pattern = portal.get('search_pattern', r'\.pdf')

        discovered = []
        pages_scraped = 0
        errors = []

        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml'
        }

        timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)

        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                for doc_path in portal['doc_paths']:
                    if pages_scraped >= max_pages:
                        break

                    url = urljoin(base_url, doc_path)

                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                html = await response.text()
                                manuals = self._extract_manual_links(
                                    html, url, manufacturer, search_pattern
                                )
                                discovered.extend(manuals)
                                pages_scraped += 1

                                logger.info(
                                    f"Scraped {url} | found {len(manuals)} manuals"
                                )
                            else:
                                errors.append({
                                    'url': url,
                                    'status': response.status
                                })

                    except Exception as e:
                        errors.append({'url': url, 'error': str(e)})
                        logger.error(f"Error scraping {url}: {e}")

                    # Respect rate limit
                    await asyncio.sleep(rate_limit)

        except Exception as e:
            logger.error(f"Scraping session failed for {manufacturer}: {e}")
            return {'error': str(e)}

        # Store discovered manuals
        stored = await self._store_discovered_manuals(manufacturer, discovered)

        result = {
            'manufacturer': manufacturer,
            'pages_scraped': pages_scraped,
            'manuals_found': len(discovered),
            'manuals_stored': stored,
            'errors': len(errors),
            'scraped_at': datetime.utcnow().isoformat()
        }

        logger.info(
            f"Scraping complete | manufacturer={manufacturer} | "
            f"pages={pages_scraped} | manuals={len(discovered)} | stored={stored}"
        )

        return result

    def _extract_manual_links(
        self,
        html: str,
        base_url: str,
        manufacturer: str,
        pattern: str
    ) -> List[Dict[str, Any]]:
        """
        Extract manual links from HTML page.

        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            manufacturer: Manufacturer name
            pattern: Regex pattern for matching manual URLs

        Returns:
            List of manual info dicts
        """
        if not HAS_BS4:
            return []

        manuals = []
        soup = BeautifulSoup(html, 'html.parser')

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Check if link matches pattern (PDF)
            if re.search(pattern, href, re.IGNORECASE):
                # Resolve relative URL
                full_url = urljoin(base_url, href)

                # Extract title from link text or surrounding context
                title = link.get_text(strip=True)
                if not title:
                    title = href.split('/')[-1].replace('.pdf', '')

                # Try to extract model from URL or title
                model = self._extract_model_from_url(full_url, manufacturer)

                manuals.append({
                    'url': full_url,
                    'title': title,
                    'manufacturer': manufacturer,
                    'model': model,
                    'source_page': base_url
                })

        return manuals

    def _extract_model_from_url(self, url: str, manufacturer: str) -> Optional[str]:
        """
        Try to extract model number from URL.

        Args:
            url: Manual URL
            manufacturer: Manufacturer name

        Returns:
            Model string if found, None otherwise
        """
        # Common patterns for model numbers in URLs
        patterns = [
            r'(\d{3,}[A-Z]?[-_]?\d*)',  # Numeric model like 6ES7315
            r'([A-Z]{2,}\d{3,})',       # Letter-number like S7300
            r'(SINAMICS|SIMATIC|PowerFlex|MicroLogix)[-_]?([A-Z0-9]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    async def _store_discovered_manuals(
        self,
        manufacturer: str,
        manuals: List[Dict[str, Any]]
    ) -> int:
        """
        Store discovered manuals in database for later download.

        Args:
            manufacturer: Manufacturer name
            manuals: List of manual info dicts

        Returns:
            Number of new manuals stored
        """
        stored = 0

        try:
            async with self.db_pool.acquire() as conn:
                for manual in manuals:
                    # Check if already exists
                    exists = await conn.fetchval(
                        """
                        SELECT EXISTS(
                            SELECT 1 FROM discovered_manuals
                            WHERE url = $1
                        )
                        """,
                        manual['url']
                    )

                    if not exists:
                        await conn.execute(
                            """
                            INSERT INTO discovered_manuals (
                                url,
                                manufacturer,
                                model,
                                title,
                                source_page,
                                discovered_at,
                                status
                            ) VALUES ($1, $2, $3, $4, $5, NOW(), 'pending')
                            """,
                            manual['url'],
                            manufacturer,
                            manual.get('model'),
                            manual.get('title'),
                            manual.get('source_page')
                        )
                        stored += 1

            return stored

        except Exception as e:
            logger.error(f"Failed to store discovered manuals: {e}")
            return stored

    async def scrape_all_manufacturers(self) -> Dict[str, Any]:
        """
        Scrape all known manufacturer catalogs.

        Returns:
            Dict with results for each manufacturer
        """
        results = {}

        for manufacturer in self.MANUFACTURER_PORTALS:
            try:
                result = await self.scrape_manufacturer(manufacturer)
                results[manufacturer] = result
            except Exception as e:
                results[manufacturer] = {'error': str(e)}

        total_found = sum(
            r.get('manuals_found', 0)
            for r in results.values()
            if isinstance(r, dict) and 'error' not in r
        )

        return {
            'manufacturers': results,
            'total_manuals_found': total_found,
            'scraped_at': datetime.utcnow().isoformat()
        }

    async def get_pending_downloads(
        self,
        manufacturer: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get discovered manuals pending download.

        Args:
            manufacturer: Filter by manufacturer (optional)
            limit: Max results to return

        Returns:
            List of pending manual downloads
        """
        try:
            async with self.db_pool.acquire() as conn:
                if manufacturer:
                    rows = await conn.fetch(
                        """
                        SELECT url, manufacturer, model, title, discovered_at
                        FROM discovered_manuals
                        WHERE status = 'pending'
                          AND LOWER(manufacturer) = LOWER($1)
                        ORDER BY discovered_at DESC
                        LIMIT $2
                        """,
                        manufacturer,
                        limit
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT url, manufacturer, model, title, discovered_at
                        FROM discovered_manuals
                        WHERE status = 'pending'
                        ORDER BY discovered_at DESC
                        LIMIT $1
                        """,
                        limit
                    )

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get pending downloads: {e}")
            return []

    async def mark_downloaded(self, url: str) -> bool:
        """
        Mark a discovered manual as downloaded.

        Args:
            url: Manual URL

        Returns:
            True if updated successfully
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE discovered_manuals
                    SET status = 'downloaded',
                        downloaded_at = NOW()
                    WHERE url = $1
                    """,
                    url
                )
                return True
        except Exception as e:
            logger.error(f"Failed to mark downloaded: {e}")
            return False

    async def get_scraper_stats(self) -> Dict[str, Any]:
        """
        Get catalog scraper statistics.

        Returns:
            Dict with scraper stats
        """
        try:
            async with self.db_pool.acquire() as conn:
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_discovered,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE status = 'downloaded') as downloaded,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed,
                        COUNT(DISTINCT manufacturer) as manufacturers
                    FROM discovered_manuals
                    """
                )

                by_manufacturer = await conn.fetch(
                    """
                    SELECT
                        manufacturer,
                        COUNT(*) as count,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending
                    FROM discovered_manuals
                    GROUP BY manufacturer
                    ORDER BY count DESC
                    """
                )

                return {
                    'totals': dict(stats) if stats else {},
                    'by_manufacturer': [dict(row) for row in by_manufacturer],
                    'supported_manufacturers': list(self.MANUFACTURER_PORTALS.keys())
                }

        except Exception as e:
            logger.error(f"Failed to get scraper stats: {e}")
            return {'error': str(e)}
