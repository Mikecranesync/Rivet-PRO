"""
Memory Storage for YCB

Provides Supabase-based memory storage functionality compatible with
the Agent Factory memory interface.
"""

import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client
from ycb.config import settings

logger = logging.getLogger(__name__)


class SupabaseMemoryStorage:
    """
    Supabase memory storage compatible with Agent Factory interface.
    
    This provides the same interface as agent_factory.memory.storage.SupabaseMemoryStorage
    but adapted for the YCB namespace and configuration.
    """

    def __init__(self):
        """Initialize Supabase memory storage."""
        self.client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        """Initialize the Supabase client."""
        try:
            if not settings.supabase_url or not settings.supabase_key:
                raise ValueError(
                    "Supabase configuration missing. "
                    "Please set SUPABASE_URL and SUPABASE_KEY environment variables."
                )
            
            self.client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            
            logger.info("Supabase memory storage initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase memory storage: {e}")
            raise