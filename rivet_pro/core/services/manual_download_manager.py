"""
Manual Download Manager - AUTO-KB-006

Service to download equipment manuals from URLs and store locally.
Supports concurrent downloads, retry logic, and integrity verification.
Also supports S3 backup storage (AUTO-KB-010).
"""

import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import aiohttp
import asyncpg

# PDF text extraction
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    logging.warning("PyPDF2 not installed - PDF text extraction disabled")

# S3 backup (AUTO-KB-010)
try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    logging.info("boto3 not installed - S3 backup disabled")

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
    - S3 backup storage (AUTO-KB-010)
    """

    MAX_CONCURRENT = 5
    DOWNLOAD_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    CHUNK_SIZE = 8192  # 8KB chunks

    # S3 configuration (AUTO-KB-010)
    S3_BUCKET = "rivet-kb-manuals"
    S3_PREFIX = "manuals"

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        storage_path: Optional[Path] = None,
        s3_bucket: Optional[str] = None,
        enable_s3_backup: bool = False
    ):
        """
        Initialize download manager.

        Args:
            db_pool: Database connection pool
            storage_path: Base path for storing manuals
            s3_bucket: S3 bucket name for backup (AUTO-KB-010)
            enable_s3_backup: Enable S3 backup storage (default: False)
        """
        self.db_pool = db_pool
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)

        # S3 backup configuration (AUTO-KB-010)
        self.s3_bucket = s3_bucket or self.S3_BUCKET
        self.enable_s3_backup = enable_s3_backup and HAS_BOTO3
        self._s3_client = None

        if self.enable_s3_backup:
            self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3 client (AUTO-KB-010)."""
        if not HAS_BOTO3:
            logger.warning("boto3 not installed - S3 backup disabled")
            self.enable_s3_backup = False
            return

        try:
            self._s3_client = boto3.client('s3')
            # Verify bucket access
            self._s3_client.head_bucket(Bucket=self.s3_bucket)
            logger.info(f"S3 backup enabled | bucket={self.s3_bucket}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.enable_s3_backup = False
            self._s3_client = None

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

                    # AUTO-KB-010: Upload to S3 backup (async, non-blocking)
                    if self.enable_s3_backup:
                        s3_key = await self.upload_to_s3(result['file_path'])
                        if s3_key:
                            result['s3_key'] = s3_key
                            await self._update_s3_metadata(result)

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

    # AUTO-KB-007: Text extraction methods

    async def extract_text(
        self,
        pdf_path: str,
        max_pages: int = 50
    ) -> Optional[str]:
        """
        Extract text content from a PDF file.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to extract (default 50)

        Returns:
            Extracted text content or None on failure
        """
        if not HAS_PYPDF2:
            logger.error("PyPDF2 not installed - cannot extract text")
            return None

        path = Path(pdf_path)
        if not path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return None

        try:
            text_parts = []

            with open(path, 'rb') as f:
                try:
                    reader = PyPDF2.PdfReader(f)

                    # Check if encrypted
                    if reader.is_encrypted:
                        # Try empty password
                        try:
                            reader.decrypt('')
                        except Exception:
                            logger.warning(f"PDF is encrypted: {pdf_path}")
                            return None

                    num_pages = min(len(reader.pages), max_pages)

                    for page_num in range(num_pages):
                        try:
                            page = reader.pages[page_num]
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                        except Exception as e:
                            logger.warning(
                                f"Failed to extract page {page_num}: {e}"
                            )
                            continue

                except PyPDF2.errors.PdfReadError as e:
                    logger.error(f"PDF read error for {pdf_path}: {e}")
                    return None

            if not text_parts:
                logger.warning(f"No text extracted from {pdf_path}")
                return None

            # Combine and clean text
            full_text = '\n\n'.join(text_parts)
            cleaned_text = self._clean_extracted_text(full_text)

            logger.info(
                f"Extracted text | file={pdf_path} | "
                f"pages={num_pages} | chars={len(cleaned_text)}"
            )

            return cleaned_text

        except Exception as e:
            logger.error(f"Text extraction failed for {pdf_path}: {e}")
            return None

    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean extracted PDF text.

        - Remove excessive whitespace
        - Normalize line breaks
        - Remove common headers/footers patterns
        """
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)

        # Normalize line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove page numbers (common patterns)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        text = re.sub(r'\n\s*Page \d+ of \d+\s*\n', '\n', text, flags=re.I)

        # Remove common footer patterns
        text = re.sub(r'\n\s*©.*?\n', '\n', text)
        text = re.sub(r'\n\s*All rights reserved.*?\n', '\n', text, flags=re.I)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    async def extract_and_store_text(
        self,
        manufacturer: str,
        model: str,
        manual_type: str = "user_manual"
    ) -> Optional[str]:
        """
        Extract text from a stored manual and save to database.

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model
            manual_type: Type of manual

        Returns:
            Extracted text or None
        """
        # Get local file path
        file_path = await self.get_local_path(manufacturer, model, manual_type)
        if not file_path:
            logger.warning(
                f"No local file for {manufacturer} {model} {manual_type}"
            )
            return None

        # Extract text
        text_content = await self.extract_text(file_path)
        if not text_content:
            return None

        # Store in database
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE manual_files
                    SET text_content = $1,
                        text_extracted_at = NOW()
                    WHERE LOWER(manufacturer) = LOWER($2)
                      AND LOWER(model) = LOWER($3)
                      AND manual_type = $4
                    """,
                    text_content,
                    manufacturer,
                    model,
                    manual_type
                )

            logger.info(
                f"Stored extracted text | manufacturer={manufacturer} | "
                f"model={model} | chars={len(text_content)}"
            )
            return text_content

        except Exception as e:
            logger.error(f"Failed to store extracted text: {e}")
            return text_content  # Return text even if storage fails

    # AUTO-KB-010: S3 Backup Storage Methods

    async def upload_to_s3(self, file_path: str) -> Optional[str]:
        """
        Upload file to S3 backup storage (AUTO-KB-010).

        Args:
            file_path: Local path to the file

        Returns:
            S3 key if successful, None otherwise
        """
        if not self.enable_s3_backup or not self._s3_client:
            return None

        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found for S3 upload: {file_path}")
            return None

        try:
            # Build S3 key from file path structure
            # e.g., manuals/Siemens/SINAMICS_G120/user_manual.pdf
            relative_path = path.relative_to(self.storage_path)
            s3_key = f"{self.S3_PREFIX}/{relative_path}".replace("\\", "/")

            # Upload file
            await asyncio.to_thread(
                self._s3_client.upload_file,
                str(path),
                self.s3_bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'StorageClass': 'STANDARD_IA'  # Infrequent access for cost savings
                }
            )

            logger.info(f"Uploaded to S3 | key={s3_key} | bucket={self.s3_bucket}")
            return s3_key

        except Exception as e:
            logger.error(f"S3 upload failed for {file_path}: {e}")
            return None

    async def _update_s3_metadata(self, result: Dict[str, Any]) -> None:
        """Update database with S3 key after upload (AUTO-KB-010)."""
        if not result.get('s3_key'):
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE manual_files
                    SET s3_key = $1,
                        s3_uploaded_at = NOW()
                    WHERE LOWER(manufacturer) = LOWER($2)
                      AND LOWER(model) = LOWER($3)
                      AND manual_type = $4
                    """,
                    result['s3_key'],
                    result['manufacturer'],
                    result['model'],
                    result['manual_type']
                )
        except Exception as e:
            logger.error(f"Failed to update S3 metadata: {e}")

    async def download_from_s3(
        self,
        manufacturer: str,
        model: str,
        manual_type: str = "user_manual"
    ) -> Optional[str]:
        """
        Download file from S3 backup if local copy missing (AUTO-KB-010).

        Args:
            manufacturer: Equipment manufacturer
            model: Equipment model
            manual_type: Type of manual

        Returns:
            Local file path if successful, None otherwise
        """
        if not self.enable_s3_backup or not self._s3_client:
            return None

        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT s3_key, file_path
                    FROM manual_files
                    WHERE LOWER(manufacturer) = LOWER($1)
                      AND LOWER(model) = LOWER($2)
                      AND manual_type = $3
                      AND s3_key IS NOT NULL
                    """,
                    manufacturer,
                    model,
                    manual_type
                )

            if not row or not row['s3_key']:
                return None

            file_path = Path(row['file_path'])

            # Check if local file already exists
            if file_path.exists():
                return str(file_path)

            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Download from S3
            await asyncio.to_thread(
                self._s3_client.download_file,
                self.s3_bucket,
                row['s3_key'],
                str(file_path)
            )

            logger.info(
                f"Downloaded from S3 | key={row['s3_key']} | path={file_path}"
            )
            return str(file_path)

        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return None

    async def sync_to_s3(self) -> Dict[str, int]:
        """
        Sync all local manuals to S3 backup (AUTO-KB-010).

        Returns:
            Dict with success and failure counts
        """
        if not self.enable_s3_backup:
            logger.warning("S3 backup not enabled")
            return {'success': 0, 'failed': 0, 'skipped': 0}

        try:
            async with self.db_pool.acquire() as conn:
                # Get manuals without S3 backup
                rows = await conn.fetch(
                    """
                    SELECT manufacturer, model, manual_type, file_path
                    FROM manual_files
                    WHERE file_path IS NOT NULL
                      AND s3_key IS NULL
                    """
                )

            success = 0
            failed = 0
            skipped = 0

            for row in rows:
                file_path = row['file_path']
                if not Path(file_path).exists():
                    skipped += 1
                    continue

                s3_key = await self.upload_to_s3(file_path)
                if s3_key:
                    await self._update_s3_metadata({
                        's3_key': s3_key,
                        'manufacturer': row['manufacturer'],
                        'model': row['model'],
                        'manual_type': row['manual_type']
                    })
                    success += 1
                else:
                    failed += 1

            logger.info(
                f"S3 sync complete | success={success} | "
                f"failed={failed} | skipped={skipped}"
            )
            return {'success': success, 'failed': failed, 'skipped': skipped}

        except Exception as e:
            logger.error(f"S3 sync failed: {e}")
            return {'success': 0, 'failed': 0, 'error': str(e)}

    async def get_s3_backup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about S3 backup storage (AUTO-KB-010).

        Returns:
            Dict with S3 backup statistics
        """
        try:
            async with self.db_pool.acquire() as conn:
                stats = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as total_manuals,
                        COUNT(*) FILTER (WHERE s3_key IS NOT NULL) as backed_up,
                        COUNT(*) FILTER (WHERE s3_key IS NULL AND file_path IS NOT NULL) as not_backed_up,
                        COALESCE(SUM(size_bytes) FILTER (WHERE s3_key IS NOT NULL), 0) as backed_up_bytes
                    FROM manual_files
                    """
                )

            result = dict(stats) if stats else {}
            result['s3_enabled'] = self.enable_s3_backup
            result['s3_bucket'] = self.s3_bucket if self.enable_s3_backup else None

            return result

        except Exception as e:
            logger.error(f"Failed to get S3 backup stats: {e}")
            return {'s3_enabled': self.enable_s3_backup, 'error': str(e)}
