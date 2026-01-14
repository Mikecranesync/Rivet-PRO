"""
Product Family Discoverer - AUTO-KB-002

Discovers related product models using LLM and pattern matching.
When user searches for "Siemens S7-1200", discovers entire S7 family.
"""

import asyncpg
import asyncio
import httpx
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import json

logger = logging.getLogger(__name__)


class ProductFamilyDiscoverer:
    """Service for discovering product families using LLM"""

    # Common manufacturer families (fallback patterns)
    KNOWN_FAMILIES = {
        'siemens': {
            'S7': ['S7-200', 'S7-300', 'S7-400', 'S7-1200', 'S7-1500'],
            'SIMATIC': ['SIMATIC S7', 'SIMATIC ET200', 'SIMATIC HMI'],
        },
        'allen_bradley': {
            'CompactLogix': ['1769', '5370', '5380'],
            'MicroLogix': ['1100', '1200', '1400', '1500'],
            'PowerFlex': ['520', '525', '753', '755'],
            '2080': ['2080-LC10', '2080-LC20', '2080-LC30', '2080-LC50'],
        },
        'abb': {
            'ACH': ['ACH550', 'ACH580'],
            'ACS': ['ACS550', 'ACS580', 'ACS880'],
        },
        'schneider': {
            'Modicon': ['M340', 'M580', 'M221'],
            'Altivar': ['ATV12', 'ATV312', 'ATV320', 'ATV630'],
        },
    }

    def __init__(self, db_pool: asyncpg.Pool, http_client: Optional[httpx.AsyncClient] = None):
        """
        Initialize discoverer with database pool and HTTP client

        Args:
            db_pool: asyncpg connection pool
            http_client: httpx async client for API calls
        """
        self.db_pool = db_pool
        self.http_client = http_client or httpx.AsyncClient(timeout=30.0)
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.tavily_api_key = os.getenv('TAVILY_API_KEY')

    async def discover_family(
        self,
        manufacturer: str,
        model: str
    ) -> Tuple[Optional[UUID], List[str]]:
        """
        Discover product family for a given manufacturer and model

        Args:
            manufacturer: Equipment manufacturer
            model: Specific model number

        Returns:
            Tuple of (family_id, list of family member models)
        """
        try:
            logger.info(f"Discovering product family for {manufacturer} {model}")

            # Step 1: Use LLM to identify product family
            family_name, family_pattern = await self._identify_family_with_llm(manufacturer, model)

            if not family_name:
                logger.warning(f"Could not identify family for {manufacturer} {model}")
                return None, []

            logger.info(f"Identified family: {family_name} with pattern: {family_pattern}")

            # Step 2: Generate list of potential family members
            family_members = await self._generate_family_members(
                manufacturer,
                family_name,
                family_pattern,
                model
            )

            logger.info(f"Generated {len(family_members)} potential family members")

            # Step 3: Store or update product family in database
            family_id = await self._store_product_family(
                manufacturer,
                family_name,
                family_pattern,
                len(family_members)
            )

            logger.info(f"Stored product family with ID: {family_id}")

            return family_id, family_members

        except Exception as e:
            logger.error(f"Failed to discover family: {e}", exc_info=True)
            return None, []

    async def _identify_family_with_llm(
        self,
        manufacturer: str,
        model: str
    ) -> Tuple[str, str]:
        """
        Use LLM to identify product family and pattern

        Args:
            manufacturer: Equipment manufacturer
            model: Specific model

        Returns:
            Tuple of (family_name, family_pattern)
        """
        try:
            prompt = f"""You are an industrial equipment expert. Analyze this equipment and identify its product family.

Manufacturer: {manufacturer}
Model: {model}

Identify:
1. **Product Family Name**: The series or family this model belongs to (e.g., "S7 Series", "CompactLogix Series", "PowerFlex Drives")
2. **Family Pattern**: A pattern to find related models (e.g., "S7-*", "1769-*", "PowerFlex 5*")

Respond in JSON format:
{{
  "family_name": "Product family name",
  "family_pattern": "Pattern to match family members",
  "explanation": "Brief explanation of this family"
}}

Examples:
- Siemens S7-1200 → {{"family_name": "S7 Series", "family_pattern": "S7-*", "explanation": "S7 programmable logic controllers"}}
- Allen Bradley 1769-L30ER → {{"family_name": "CompactLogix 1769", "family_pattern": "1769-*", "explanation": "CompactLogix controllers"}}
- ABB ACH580-01-02A6-4 → {{"family_name": "ACH580 Drives", "family_pattern": "ACH580*", "explanation": "HVAC drives"}}

Respond with JSON only, no other text."""

            response = await self.http_client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            )

            response.raise_for_status()
            result = response.json()

            content = result['choices'][0]['message']['content'].strip()

            # Parse JSON response
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0].strip()
            elif content.startswith('```'):
                content = content.split('```')[1].split('```')[0].strip()

            family_info = json.loads(content)

            family_name = family_info.get('family_name', '')
            family_pattern = family_info.get('family_pattern', '')

            logger.info(f"LLM identified family: {family_name} ({family_pattern})")

            return family_name, family_pattern

        except Exception as e:
            logger.error(f"LLM family identification failed: {e}", exc_info=True)

            # Fallback to known patterns
            return self._fallback_family_identification(manufacturer, model)

    def _fallback_family_identification(
        self,
        manufacturer: str,
        model: str
    ) -> Tuple[str, str]:
        """
        Fallback to known family patterns when LLM fails

        Args:
            manufacturer: Equipment manufacturer
            model: Specific model

        Returns:
            Tuple of (family_name, family_pattern)
        """
        manufacturer_key = manufacturer.lower().replace(' ', '_')

        if manufacturer_key not in self.KNOWN_FAMILIES:
            # Generic fallback - extract prefix
            prefix = ''.join([c for c in model if c.isalpha() or c == '-'])[:10]
            return f"{manufacturer} {prefix} Series", f"{prefix}*"

        # Search known families
        for family_name, patterns in self.KNOWN_FAMILIES[manufacturer_key].items():
            for pattern in patterns:
                if pattern in model or model.startswith(pattern.rstrip('*')):
                    return f"{manufacturer} {family_name}", f"{pattern}*"

        # Default fallback
        return f"{manufacturer} Equipment", f"{manufacturer}*"

    async def _generate_family_members(
        self,
        manufacturer: str,
        family_name: str,
        family_pattern: str,
        seed_model: str
    ) -> List[str]:
        """
        Generate list of potential family members using LLM

        Args:
            manufacturer: Equipment manufacturer
            family_name: Product family name
            family_pattern: Pattern for family members
            seed_model: Original model that triggered discovery

        Returns:
            List of family member model numbers
        """
        try:
            prompt = f"""You are an industrial equipment catalog expert. Generate a list of related product models.

Manufacturer: {manufacturer}
Product Family: {family_name}
Pattern: {family_pattern}
Known Model: {seed_model}

Generate a list of 10-20 related models in this product family. Include:
- Common models (popular, widely used)
- Different capacity/power ratings
- Different feature sets
- Recent models

Respond with a JSON array of model numbers only:
["model1", "model2", "model3", ...]

Example for Siemens S7 Series:
["S7-200", "S7-300", "S7-400", "S7-1200", "S7-1500", "S7-1200 CPU 1211C", "S7-1200 CPU 1214C", "S7-1500 CPU 1511-1 PN", ...]

Respond with JSON array only, no other text."""

            response = await self.http_client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 1000
                }
            )

            response.raise_for_status()
            result = response.json()

            content = result['choices'][0]['message']['content'].strip()

            # Parse JSON array
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0].strip()
            elif content.startswith('```'):
                content = content.split('```')[1].split('```')[0].strip()

            models = json.loads(content)

            # Ensure seed model is included
            if seed_model not in models:
                models.insert(0, seed_model)

            logger.info(f"Generated {len(models)} family members via LLM")
            return models

        except Exception as e:
            logger.error(f"Failed to generate family members with LLM: {e}", exc_info=True)

            # Fallback: return just the seed model
            return [seed_model]

    async def _store_product_family(
        self,
        manufacturer: str,
        family_name: str,
        family_pattern: str,
        member_count: int
    ) -> UUID:
        """
        Store or update product family in database

        Args:
            manufacturer: Equipment manufacturer
            family_name: Product family name
            family_pattern: Pattern for family members
            member_count: Number of family members discovered

        Returns:
            UUID of product family
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Check if family already exists
                existing = await conn.fetchrow(
                    """
                    SELECT id, member_count
                    FROM product_families
                    WHERE manufacturer = $1
                      AND family_name = $2
                    """,
                    manufacturer,
                    family_name
                )

                if existing:
                    # Update existing family
                    await conn.execute(
                        """
                        UPDATE product_families
                        SET member_count = $1,
                            family_pattern = $2,
                            discovered_at = NOW()
                        WHERE id = $3
                        """,
                        member_count,
                        family_pattern,
                        existing['id']
                    )

                    logger.info(f"Updated existing family: {family_name}")
                    return existing['id']

                # Create new family
                family_id = await conn.fetchval(
                    """
                    INSERT INTO product_families (
                        manufacturer,
                        family_name,
                        family_pattern,
                        member_count,
                        discovered_at
                    ) VALUES ($1, $2, $3, $4, NOW())
                    RETURNING id
                    """,
                    manufacturer,
                    family_name,
                    family_pattern,
                    member_count
                )

                logger.info(f"Created new product family: {family_name} (ID: {family_id})")
                return family_id

        except Exception as e:
            logger.error(f"Failed to store product family: {e}", exc_info=True)
            raise

    async def verify_family_member_exists(
        self,
        manufacturer: str,
        model: str
    ) -> bool:
        """
        Verify if a family member exists (via Tavily search)

        Args:
            manufacturer: Equipment manufacturer
            model: Model to verify

        Returns:
            True if manual found, False otherwise
        """
        try:
            # Quick Tavily search
            query = f"{manufacturer} {model} manual PDF"

            response = await self.http_client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 1
                }
            )

            response.raise_for_status()
            result = response.json()

            return len(result.get('results', [])) > 0

        except Exception as e:
            logger.error(f"Failed to verify family member {manufacturer} {model}: {e}")
            return False

    async def discover_and_verify_family(
        self,
        manufacturer: str,
        model: str,
        verify_count: int = 5
    ) -> Tuple[Optional[UUID], List[str], List[str]]:
        """
        Discover family and verify a subset of members exist

        Args:
            manufacturer: Equipment manufacturer
            model: Seed model
            verify_count: Number of family members to verify

        Returns:
            Tuple of (family_id, all_members, verified_members)
        """
        family_id, family_members = await self.discover_family(manufacturer, model)

        if not family_id or not family_members:
            return None, [], []

        # Verify subset of family members in parallel
        verify_members = family_members[:verify_count]

        verification_tasks = [
            self.verify_family_member_exists(manufacturer, member)
            for member in verify_members
        ]

        verification_results = await asyncio.gather(*verification_tasks, return_exceptions=True)

        verified_members = [
            member for member, verified in zip(verify_members, verification_results)
            if verified is True
        ]

        logger.info(
            f"Verified {len(verified_members)}/{len(verify_members)} family members exist"
        )

        return family_id, family_members, verified_members
