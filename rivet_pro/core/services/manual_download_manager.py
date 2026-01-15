"""
Manual Download Manager - AUTO-KB-006

Service to download equipment manuals from URLs and store locally.
Supports concurrent downloads, retry logic, and integrity verification.
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import aiohttp
import asyncpg

logger = logging.getLogger(__name__)

# Default storage path
DEFAULT_STORAGE_PATH = Path("/opt/Rivet-PRO/manuals")
# Windows fallback
if os.name == 'nt':
    DEFAULT_STORAGE_PATH = Path.home() / "Rivet-PRO" / "manuals"


class ManualDownloadManager:
    """
    Service for downloading and storing equipment manuals.

    Features:
    - Stream downloads for large files
    - Concurrent downloads (configurable)
    - Retry with exponential backoff
    - Checksum verification
    - Metadata storage in database
    """

    MAX_CONCURRENT = 5
    DOWNLOAD_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    CHUNK_SIZE = 8192  # 8KB chunks

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        storage_path: Optional[Path] = None
    ):
        """
        Initialize download manager.

        Args:
            db_pool: Database connection pool
            storage_path: Base path for storing manuals
        """
        self.db_pool = db_pool
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)

    async def download_manual(
        self,
        url: str,
        manufacturer: str,
        model: str,
        manual_type: str = "user_manual"
    ) -> Optional[Dict[str, Any]]:
        """
        Download a manual from URL and store locally.

        Args:
            url: URL to download from
            manufacturer: Equipment manufacturer
            model: Equipment model number
            manual_type: Type of manual (user_manual, service_manual, etc.)

        Returns:
            Dict with file_path, checksum, size, etc. or None on failure
        """
        async with self._semaphore:
            return await self._download_with_retry(
                url, manufacturer, model, manual_type
            )

    async def _download_with_retry(
        self,
        url: str,
        manufacturer: str,
        model: str,
        manual_type: str
    ) -> Optional[Dict[str, Any]]:
        """Download with exponential backoff retry."""
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                result = await self._download_file(
                    url, manufacturer, model, manual_type
                )
                if result:
                    # Store metadata in database
                    await self._store_metadata(result)
                    return result

            except Exception as e:
                last_error = e
                backoff = 2 ** attempt
                logger.warning(
                    f"Download attempt {attempt + 1} failed for {url}: {e}. "
                    f"Retrying in {backoff}s..."
                )
                await asyncio.sleep(backoff)

        logger.error(f"All download attempts failed for {url}: {last_error}")
        return None

    async def _download_file(
        self,
        url: str,
        manufacturer: str,
        model: str,
        manual_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Download a single file with streaming.

        Args:
            url: URL to download
            manufacturer: Equipment manufacturer
            model: Equipment model
            manual_type: Type of manual

        Returns:
            Dict with download result or None
        """
        # Sanitize paths
        safe_manufacturer = self._sanitize_path(manufacturer)
        safe_model = self._sanitize_path(model)

        # Create storage directory
        dir_path = self.storage_path / safe_manufacturer / safe_model
        dir_path.mkdir(parents=True, exist_ok=True)

        # Determine filename from URL
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name or f"{manual_type}.pdf"

        # Ensure .pdf extension
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'

        file_path = dir_path / filename

        # Download with streaming
        timeout = aiohttp.ClientTimeout(total=self.DOWNLOAD_TIMEOUT)
        hasher = hashlib.sha256()
        total_size = 0

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.error(
                            f"HTTP {response.status} downloading {url}"
                        )
                        return None

                    # Get content length if available
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        content_length = int(content_length)

                    # Stream to file
                    with open(file_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(
                            self.CHUNK_SIZE
                        ):
                            f.write(chunk)
                            hasher.update(chunk)
                            total_size += len(chunk)

                            # Progress logging for large files
                            if content_length and total_size % (1024 * 1024) < self.CHUNK_SIZE:
                                progress = (total_size / content_length) * 100
                                logger.debug(
                                    f"Download progress: {progress:.1f}% "
                                    f"({total_size / 1024 / 1024:.1f}MB)"
                                )

            checksum = hasher.hexdigest()

            logger.info(
                f"Downloaded manual | manufacturer={manufacturer} | "
                f"model={model} | size={total_size} | checksum={checksum[:16]}..."
            )

            return {
                'url': url,
                'manufacturer': manufacturer,
                'model': model,
                'manual_type': manual_type,
                'file_path': str(file_path),
                'filename': filename,
                'size_bytes': total_size,
                'checksum_sha256': checksum,
                'downloaded_at': datetime.utcnow()
            }

        except asyncio.TimeoutError:
            logger.error(f"Timeout downloading {url}")
            # Clean up partial file
            if file_path.exists():
                file_path.unlink()
            raise

        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            # Clean up partial file
            if file_path.exists():
                file_path.unlink()
            raise

    async def _store_metadata(self, result: Dict[str, Any]) -> None:
        """Store download metadata in database."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO manual_files (
                        url,
                        manufacturer,
                        model,
                        manual_type,
                        file_path,
                        filename,
                        size_bytes,
                        checksum_sha256,
                        downloaded_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (manufacturer, model, manual_type)
                    DO UPDATE SET
                        url = EXCLUDED.url,
                        file_path = EXCLUDED.file_path,
                        filename = EXCLUDED.filename,
                        size_bytes = EXCLUDED.size_bytes,
                        checksum_sha256 = EXCLUDED.checksum_sha256,
                        downloaded_at = EXCLUDED.downloaded_at
                    """,
                    result['url'],
                    result['manufacturer'],
                    result['model'],
                    result['manual_type'],
                    result['file_path'],
                    result['filename'],
                    result['size_bytes'],
                    result['checksum_sha256'],
                    result['downloaded_at']
                )
        except Exception as e:
            logger.error(f"Failed to store metadata: {e}")
            # Don't fail the download if metadata storage fails

    async def download_batch(
        self,
        manuals: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Download multiple manuals concurrently.

        Args:
            manuals: List of dicts with url, manufacturer, model, manual_type

        Returns:
            List of successful download results
        """
        tasks = [
            self.download_manual(
                url=m['url'],
                manufacturer=m['manufacturer'],
                model=m['model'],
                manual_type=m.get('manual_type', 'user_manual')
            )
            for m in manuals
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        successful = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Batch download failed for {manuals[i]['url']}: {result}"
                )
            elif result:
                successful.append(result)

        logger.info(
            f"Batch download complete: {len(successful)}/{len(manuals)} succeeded"
        )
        return successful

    async def verify_file(self, file_path: str, expected_checksum: str) -> bool:
        """
        Verify file integrity by comparing checksum.

        Args:
            file_path: Path to file
            expected_checksum: Expected SHA256 checksum

        Returns:
            True if checksum matches
        """
        path = Path(file_path)
        if not path.exists():
            return False

        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(self.CHUNK_SIZE), b''):
                hasher.update(chunk)

        actual_checksum = hasher.hexdigest()
        return actual_checksum == expected_checksum

    async def get_local_path(
        self,
        manufacturer: str,
        model: str,
        manual_type: str = "user_manual"
    ) -> Optional[str]:
        """
        Get local file path for a manual if it exists.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model
            manual_type: Type of manual

        Returns:
            Local file path or None
        """
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT file_path, checksum_sha256
                    FROM manual_files
                    WHERE LOWER(manufacturer) = LOWER($1)
                      AND LOWER(model) = LOWER($2)
                      AND manual_type = $3
                    """,
                    manufacturer,
                    model,
                    manual_type
                )

                if not row:
                    return None

                # Verify file still exists and is valid
                file_path = row['file_path']
                if Path(file_path).exists():
                    if await self.verify_file(file_path, row['checksum_sha256']):
                        return file_path
                    else:
                        logger.warning(
                            f"Checksum mismatch for {file_path}, re-download needed"
                        )

                return None

        except Exception as e:
            logger.error(f"Error getting local path: {e}")
            return None

    @staticmethod
    def _sanitize_path(name: str) -> str:
        """Sanitize string for use in file path."""
        # Replace dangerous characters
        safe = name.replace('/', '_').replace('\\', '_')
        safe = safe.replace('..', '_').replace(':', '_')
        # Remove other problematic chars
        safe = ''.join(c for c in safe if c.isalnum() or c in '._- ')
        return safe.strip()
