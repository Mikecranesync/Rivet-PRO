"""
Manual search service for equipment manuals.
Caches manual URLs in database and searches via n8n Manual Hunter webhook.
"""

from typing import Optional, Dict, Any
import httpx
import json
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

        # LLM configuration for URL validation
        self.anthropic_api_key = settings.anthropic_api_key
        self.openai_api_key = settings.openai_api_key
        self.groq_api_key = settings.groq_api_key
        self.deepseek_api_key = settings.deepseek_api_key

        if not any([self.anthropic_api_key, self.openai_api_key, self.groq_api_key, self.deepseek_api_key]):
            logger.warning("No LLM API keys configured - URL validation will be disabled")

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

        # 2. Cache miss - search externally (Tavily or n8n fallback)
        search_method = "Tavily" if self.use_tavily_direct else "n8n"
        logger.info(f"Manual cache MISS | {mfr_clean} {model_clean} | Searching via {search_method}...")

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

    async def _validate_manual_url(
        self,
        url: str,
        manufacturer: str,
        model: str,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Use LLM to validate if URL is a direct PDF manual link or search page.

        Args:
            url: URL to validate
            manufacturer: Equipment manufacturer
            model: Equipment model number
            timeout: LLM API timeout in seconds (default: 5)

        Returns:
            Dict with validation results:
            {
                'is_direct_pdf': bool,
                'confidence': float (0.0-1.0),
                'reasoning': str,
                'likely_pdf_extension': bool
            }

        If LLM validation fails, returns safe default (reject URL):
            {'is_direct_pdf': False, 'confidence': 0.0, 'reasoning': 'LLM validation failed'}
        """
        # Log API key availability (without exposing keys)
        logger.info(
            f"URL validation starting | url={url[:100]} | "
            f"has_claude_key={bool(self.anthropic_api_key)} | "
            f"has_openai_key={bool(self.openai_api_key)} | "
            f"has_groq_key={bool(self.groq_api_key)} | "
            f"has_deepseek_key={bool(self.deepseek_api_key)}"
        )

        # Safety first: if no LLM configured, reject all URLs
        if not any([self.anthropic_api_key, self.openai_api_key, self.groq_api_key, self.deepseek_api_key]):
            logger.warning(f"URL validation skipped (no LLM) | {url}")
            return {
                'is_direct_pdf': False,
                'confidence': 0.0,
                'reasoning': 'LLM validation not available'
            }

        # Build validation prompt (optimized for speed)
        prompt = f"""Is this URL a direct PDF manual link for {manufacturer} {model}?
URL: {url}

Return JSON only: {{"is_direct_pdf":true/false,"confidence":0.0-1.0,"reasoning":"brief","likely_pdf_extension":true/false}}

PDF indicators: .pdf extension, /manuals/, /documents/, /literature/ paths
NOT PDF: /search?, /results, catalog pages, homepages, shopping carts"""

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Try Anthropic Claude first (preferred)
                if self.anthropic_api_key:
                    logger.info(f"Attempting Claude API validation | url={url[:80]}")
                    try:
                        response = await client.post(
                            "https://api.anthropic.com/v1/messages",
                            headers={
                                "x-api-key": self.anthropic_api_key,
                                "anthropic-version": "2023-06-01",
                                "content-type": "application/json"
                            },
                            json={
                                "model": "claude-3-5-sonnet-20241022",
                                "max_tokens": 200,
                                "messages": [
                                    {"role": "user", "content": prompt}
                                ]
                            }
                        )

                        logger.info(f"Claude API response | status={response.status_code}")

                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"Claude response data keys: {list(data.keys())}")

                            content = data.get('content', [{}])[0].get('text', '{}')
                            logger.info(f"Claude content (first 200 chars): {content[:200]}")

                            try:
                                result = json.loads(content)
                                logger.info(
                                    f"URL validation (Claude) SUCCESS | {manufacturer} {model} | "
                                    f"url={url} | is_direct_pdf={result.get('is_direct_pdf')} | "
                                    f"confidence={result.get('confidence'):.2f} | "
                                    f"reasoning={result.get('reasoning', 'N/A')[:100]}"
                                )
                                return result
                            except json.JSONDecodeError as json_err:
                                logger.error(
                                    f"Claude JSON parse failed | content={content[:300]} | "
                                    f"error={json_err}"
                                )
                                raise
                        else:
                            logger.error(
                                f"Claude API failed | status={response.status_code} | "
                                f"body={response.text[:500]}"
                            )

                    except httpx.HTTPStatusError as http_err:
                        logger.error(
                            f"Claude HTTP error | status={http_err.response.status_code} | "
                            f"body={http_err.response.text[:500]}"
                        )
                    except json.JSONDecodeError as json_err:
                        logger.error(f"Claude JSON decode error | error={json_err}")
                    except Exception as e:
                        logger.error(
                            f"Claude validation error | type={type(e).__name__} | "
                            f"error={e}",
                            exc_info=True
                        )

                # Fallback to OpenAI GPT-4o-mini
                if self.openai_api_key:
                    logger.info(f"Attempting OpenAI API validation | url={url[:80]}")
                    try:
                        response = await client.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.openai_api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "gpt-4o-mini",
                                "max_tokens": 200,
                                "temperature": 0.1,
                                "messages": [
                                    {"role": "user", "content": prompt}
                                ]
                            }
                        )

                        logger.info(f"OpenAI API response | status={response.status_code}")

                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"OpenAI response data keys: {list(data.keys())}")

                            content = data.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                            logger.info(f"OpenAI content (first 200 chars): {content[:200]}")

                            try:
                                result = json.loads(content)
                                logger.info(
                                    f"URL validation (GPT-4o-mini) SUCCESS | {manufacturer} {model} | "
                                    f"url={url} | is_direct_pdf={result.get('is_direct_pdf')} | "
                                    f"confidence={result.get('confidence'):.2f} | "
                                    f"reasoning={result.get('reasoning', 'N/A')[:100]}"
                                )
                                return result
                            except json.JSONDecodeError as json_err:
                                logger.error(
                                    f"OpenAI JSON parse failed | content={content[:300]} | "
                                    f"error={json_err}"
                                )
                                raise
                        else:
                            logger.error(
                                f"OpenAI API failed | status={response.status_code} | "
                                f"body={response.text[:500]}"
                            )

                    except httpx.HTTPStatusError as http_err:
                        logger.error(
                            f"OpenAI HTTP error | status={http_err.response.status_code} | "
                            f"body={http_err.response.text[:500]}"
                        )
                    except json.JSONDecodeError as json_err:
                        logger.error(f"OpenAI JSON decode error | error={json_err}")
                    except Exception as e:
                        logger.error(
                            f"OpenAI validation error | type={type(e).__name__} | "
                            f"error={e}",
                            exc_info=True
                        )

                # Fallback to Groq
                if self.groq_api_key:
                    logger.info(f"Attempting Groq API validation | url={url[:80]}")
                    try:
                        response = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.groq_api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "llama-3.3-70b-versatile",
                                "max_tokens": 200,
                                "temperature": 0.1,
                                "messages": [
                                    {"role": "user", "content": prompt}
                                ]
                            }
                        )

                        logger.info(f"Groq API response | status={response.status_code}")

                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"Groq response data keys: {list(data.keys())}")

                            content = data.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                            logger.info(f"Groq content (first 200 chars): {content[:200]}")

                            try:
                                result = json.loads(content)
                                logger.info(
                                    f"URL validation (Groq) SUCCESS | {manufacturer} {model} | "
                                    f"url={url} | is_direct_pdf={result.get('is_direct_pdf')} | "
                                    f"confidence={result.get('confidence'):.2f} | "
                                    f"reasoning={result.get('reasoning', 'N/A')[:100]}"
                                )
                                return result
                            except json.JSONDecodeError as json_err:
                                logger.error(
                                    f"Groq JSON parse failed | content={content[:300]} | "
                                    f"error={json_err}"
                                )
                                raise
                        else:
                            logger.error(
                                f"Groq API failed | status={response.status_code} | "
                                f"body={response.text[:500]}"
                            )

                    except httpx.HTTPStatusError as http_err:
                        logger.error(
                            f"Groq HTTP error | status={http_err.response.status_code} | "
                            f"body={http_err.response.text[:500]}"
                        )
                    except json.JSONDecodeError as json_err:
                        logger.error(f"Groq JSON decode error | error={json_err}")
                    except Exception as e:
                        logger.error(
                            f"Groq validation error | type={type(e).__name__} | "
                            f"error={e}",
                            exc_info=True
                        )

                # Final fallback to DeepSeek
                if self.deepseek_api_key:
                    logger.info(f"Attempting DeepSeek API validation | url={url[:80]}")
                    try:
                        response = await client.post(
                            "https://api.deepseek.com/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.deepseek_api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "deepseek-chat",
                                "max_tokens": 200,
                                "temperature": 0.1,
                                "messages": [
                                    {"role": "user", "content": prompt}
                                ]
                            }
                        )

                        logger.info(f"DeepSeek API response | status={response.status_code}")

                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"DeepSeek response data keys: {list(data.keys())}")

                            content = data.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                            logger.info(f"DeepSeek content (first 200 chars): {content[:200]}")

                            try:
                                result = json.loads(content)
                                logger.info(
                                    f"URL validation (DeepSeek) SUCCESS | {manufacturer} {model} | "
                                    f"url={url} | is_direct_pdf={result.get('is_direct_pdf')} | "
                                    f"confidence={result.get('confidence'):.2f} | "
                                    f"reasoning={result.get('reasoning', 'N/A')[:100]}"
                                )
                                return result
                            except json.JSONDecodeError as json_err:
                                logger.error(
                                    f"DeepSeek JSON parse failed | content={content[:300]} | "
                                    f"error={json_err}"
                                )
                                raise
                        else:
                            logger.error(
                                f"DeepSeek API failed | status={response.status_code} | "
                                f"body={response.text[:500]}"
                            )

                    except httpx.HTTPStatusError as http_err:
                        logger.error(
                            f"DeepSeek HTTP error | status={http_err.response.status_code} | "
                            f"body={http_err.response.text[:500]}"
                        )
                    except json.JSONDecodeError as json_err:
                        logger.error(f"DeepSeek JSON decode error | error={json_err}")
                    except Exception as e:
                        logger.error(
                            f"DeepSeek validation error | type={type(e).__name__} | "
                            f"error={e}",
                            exc_info=True
                        )

        except httpx.TimeoutException as timeout_err:
            logger.error(
                f"URL validation timeout | {url} | timeout={timeout}s | error={timeout_err}",
                exc_info=True
            )
        except Exception as e:
            logger.error(
                f"URL validation outer exception | type={type(e).__name__} | "
                f"{url} | error={e}",
                exc_info=True
            )

        # Safety default: reject URL if validation failed
        logger.warning(
            f"URL rejected (validation failed) | {url} | "
            f"claude_attempted={bool(self.anthropic_api_key)} | "
            f"openai_attempted={bool(self.openai_api_key)} | "
            f"groq_attempted={bool(self.groq_api_key)} | "
            f"deepseek_attempted={bool(self.deepseek_api_key)}"
        )
        return {
            'is_direct_pdf': False,
            'confidence': 0.0,
            'reasoning': 'All LLM providers failed - rejecting for safety'
        }

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

                    logger.info(f"Tavily returned {len(results)} results | {manufacturer} {model}")

                    # Validate each result with LLM judge
                    for result in results:
                        url = result.get('url', '')
                        title = result.get('title', '')

                        # Quick pre-filter: URLs likely to be documentation
                        url_lower = url.lower()
                        is_likely_pdf = (
                            url_lower.endswith('.pdf') or
                            'manual' in url_lower or
                            'document' in url_lower or
                            'literature' in url_lower or
                            'support' in url_lower or
                            'download' in url_lower
                        )

                        if is_likely_pdf:
                            # Validate with LLM before returning
                            validation = await self._validate_manual_url(
                                url=url,
                                manufacturer=manufacturer,
                                model=model,
                                timeout=5
                            )

                            is_valid = validation.get('is_direct_pdf', False)
                            confidence = validation.get('confidence', 0.0)
                            reasoning = validation.get('reasoning', 'No reasoning provided')

                            if is_valid and confidence >= 0.7:
                                # URL passed validation
                                logger.info(
                                    f"Tavily manual validated | {manufacturer} {model} | "
                                    f"url={url} | confidence={confidence:.2f}"
                                )
                                return {
                                    'url': url,
                                    'title': title or f"{manufacturer} {model} Manual",
                                    'source': 'tavily',
                                    'confidence': confidence
                                }
                            else:
                                # URL rejected by LLM judge
                                logger.warning(
                                    f"URL rejected by LLM judge | {manufacturer} {model} | "
                                    f"url={url} | confidence={confidence:.2f} | reason={reasoning}"
                                )
                                # Continue checking next result

                    logger.info(f"Tavily search: no valid PDF results after LLM validation | {manufacturer} {model}")
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
                        url = data['url']

                        # Validate URL with LLM before returning
                        validation = await self._validate_manual_url(
                            url=url,
                            manufacturer=manufacturer,
                            model=model,
                            timeout=5
                        )

                        is_valid = validation.get('is_direct_pdf', False)
                        confidence = validation.get('confidence', 0.0)
                        reasoning = validation.get('reasoning', 'No reasoning provided')

                        if is_valid and confidence >= 0.7:
                            # URL passed validation
                            logger.info(
                                f"n8n manual validated | {manufacturer} {model} | "
                                f"url={url} | confidence={confidence:.2f}"
                            )
                            return {
                                'url': url,
                                'title': data.get('title', f"{manufacturer} {model} Manual"),
                                'source': data.get('source', 'n8n'),
                                'confidence': confidence
                            }
                        else:
                            # URL rejected by LLM judge
                            logger.warning(
                                f"n8n URL rejected by LLM judge | {manufacturer} {model} | "
                                f"url={url} | confidence={confidence:.2f} | reason={reasoning}"
                            )
                            return None

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
