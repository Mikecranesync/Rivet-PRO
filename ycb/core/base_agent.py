"""
BaseAgent class with Supabase integration for YCB agents.

Provides common functionality for all YCB agents including:
- Supabase client initialization
- Agent status registration
- Heartbeat mechanism
- Abstract run() method
- Logging setup
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from supabase import create_client, Client
from ycb.config import settings


class BaseAgent(ABC):
    """
    Abstract base class for all YCB agents with Supabase integration.
    
    Provides common functionality:
    - Supabase client initialization
    - Agent status registration and heartbeat
    - Logging setup
    - Abstract run() method that must be implemented by subclasses
    
    Usage:
        class MyAgent(BaseAgent):
            async def run(self):
                await self.log_info("Agent running...")
                # Agent-specific logic here
                
        agent = MyAgent("my_agent")
        await agent.start()
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize the base agent.
        
        Args:
            agent_name: Unique identifier for this agent instance
        """
        self.agent_name = agent_name
        self.supabase_client: Optional[Client] = None
        self.is_running = False
        self.logger = self._setup_logging()
        
        # Initialize Supabase client
        self._init_supabase_client()
        
        # Register agent status
        asyncio.create_task(self._register_status())
    
    def _setup_logging(self) -> logging.Logger:
        """
        Set up logging for the agent.
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"ycb.{self.agent_name}")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _init_supabase_client(self) -> None:
        """
        Initialize the Supabase client.
        
        Raises:
            ValueError: If Supabase configuration is missing
            Exception: If client initialization fails
        """
        try:
            if not settings.supabase_url or not settings.supabase_key:
                raise ValueError(
                    "Supabase configuration missing. "
                    "Please set SUPABASE_URL and SUPABASE_KEY environment variables."
                )
            
            self.supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            
            self.logger.info(f"Supabase client initialized for agent: {self.agent_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    async def _register_status(self) -> None:
        """
        Register agent status in Supabase.
        
        Creates or updates agent record in the agent_status table.
        """
        try:
            if not self.supabase_client:
                self.logger.warning("Supabase client not initialized, skipping status registration")
                return
            
            status_data = {
                "agent_name": self.agent_name,
                "status": "initializing",
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "version": "1.0.0",
                    "capabilities": self._get_capabilities()
                }
            }
            
            # Upsert agent status (insert or update if exists)
            result = self.supabase_client.table("agent_status").upsert(
                status_data,
                on_conflict="agent_name"
            ).execute()
            
            self.logger.info(f"Agent status registered: {self.agent_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to register agent status: {e}")
            # Don't raise - status registration failure shouldn't stop agent
    
    def _get_capabilities(self) -> Dict[str, Any]:
        """
        Get agent capabilities for metadata.
        
        Can be overridden by subclasses to provide specific capabilities.
        
        Returns:
            Dict containing agent capabilities
        """
        return {
            "base_agent": True,
            "heartbeat": True,
            "logging": True,
            "supabase_integration": True
        }
    
    async def heartbeat(self) -> None:
        """
        Send heartbeat to update agent status in Supabase.
        
        Updates the last_heartbeat timestamp and status.
        """
        try:
            if not self.supabase_client:
                return
            
            update_data = {
                "status": "running" if self.is_running else "idle",
                "last_heartbeat": datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase_client.table("agent_status").update(
                update_data
            ).eq("agent_name", self.agent_name).execute()
            
            self.logger.debug(f"Heartbeat sent for agent: {self.agent_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to send heartbeat: {e}")
    
    async def log_info(self, message: str, extra_data: Optional[Dict] = None) -> None:
        """
        Log info message and optionally store in Supabase.
        
        Args:
            message: Log message
            extra_data: Optional additional data to store
        """
        self.logger.info(message)
        await self._store_log("info", message, extra_data)
    
    async def log_error(self, message: str, extra_data: Optional[Dict] = None) -> None:
        """
        Log error message and optionally store in Supabase.
        
        Args:
            message: Log message
            extra_data: Optional additional data to store
        """
        self.logger.error(message)
        await self._store_log("error", message, extra_data)
    
    async def log_warning(self, message: str, extra_data: Optional[Dict] = None) -> None:
        """
        Log warning message and optionally store in Supabase.
        
        Args:
            message: Log message
            extra_data: Optional additional data to store
        """
        self.logger.warning(message)
        await self._store_log("warning", message, extra_data)
    
    async def _store_log(self, level: str, message: str, extra_data: Optional[Dict] = None) -> None:
        """
        Store log entry in Supabase (optional).
        
        Args:
            level: Log level (info, warning, error)
            message: Log message
            extra_data: Optional additional data
        """
        try:
            if not self.supabase_client:
                return
            
            log_data = {
                "agent_name": self.agent_name,
                "level": level,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "extra_data": extra_data or {}
            }
            
            # Only store important logs (warning and error) to avoid clutter
            if level in ["warning", "error"]:
                result = self.supabase_client.table("agent_logs").insert(log_data).execute()
            
        except Exception as e:
            # Don't log this error to avoid recursion
            pass
    
    async def start(self) -> None:
        """
        Start the agent.
        
        Marks agent as running and starts the main run loop with heartbeat.
        """
        try:
            self.is_running = True
            await self.log_info(f"Starting agent: {self.agent_name}")
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Start main agent task
            run_task = asyncio.create_task(self.run())
            
            # Wait for either task to complete
            done, pending = await asyncio.wait(
                [heartbeat_task, run_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            await self.log_error(f"Agent start failed: {e}")
            raise
        finally:
            self.is_running = False
            await self.log_info(f"Agent stopped: {self.agent_name}")
    
    async def stop(self) -> None:
        """
        Stop the agent gracefully.
        """
        self.is_running = False
        await self.log_info(f"Stopping agent: {self.agent_name}")
        
        # Update status in Supabase
        try:
            if self.supabase_client:
                self.supabase_client.table("agent_status").update(
                    {"status": "stopped"}
                ).eq("agent_name", self.agent_name).execute()
        except Exception as e:
            await self.log_error(f"Failed to update stop status: {e}")
    
    async def _heartbeat_loop(self) -> None:
        """
        Background heartbeat loop.
        
        Sends heartbeat every 30 seconds while agent is running.
        """
        while self.is_running:
            await self.heartbeat()
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
    
    @abstractmethod
    async def run(self) -> None:
        """
        Abstract method that must be implemented by subclasses.
        
        This is where the main agent logic should be implemented.
        """
        pass
    
    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"BaseAgent(name='{self.agent_name}', running={self.is_running})"