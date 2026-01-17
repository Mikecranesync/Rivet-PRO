#!/usr/bin/env python3
"""
Ralph Gateway - HTTP API for Ralph autonomous coding agent.

Provides REST endpoints for:
- Story management (CRUD)
- Execution triggering
- Status monitoring
- Health checks

Usage:
    python -m src.ralph_gateway
    # or via CLI:
    ralph-server --port 8765
"""

import os
import sys
import json
import asyncio
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    UVICORN_AVAILABLE = False


# Version info
__version__ = "1.0.0"


# Pydantic models for API
if FASTAPI_AVAILABLE:
    class StoryCreate(BaseModel):
        story_id: str
        title: str
        description: str
        acceptance_criteria: List[str]
        priority: int = 0
        ai_model: str = "claude-sonnet-4-20250514"

    class StoryUpdate(BaseModel):
        title: Optional[str] = None
        description: Optional[str] = None
        acceptance_criteria: Optional[List[str]] = None
        priority: Optional[int] = None
        status: Optional[str] = None

    class ExecutionRequest(BaseModel):
        max_stories: int = 5
        prefix: Optional[str] = None
        story_id: Optional[str] = None
        model: str = "claude-sonnet-4-20250514"
        project_root: Optional[str] = None


@dataclass
class Execution:
    """Tracks an execution run."""
    id: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stories_completed: int = 0
    stories_failed: int = 0
    current_story: Optional[str] = None
    error: Optional[str] = None


class RalphGateway:
    """HTTP API gateway for Ralph."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.pool = None
        self.executions: Dict[str, Execution] = {}

        if FASTAPI_AVAILABLE:
            self.app = FastAPI(
                title="Ralph API Gateway",
                description="HTTP API for Ralph autonomous coding agent",
                version=__version__,
                docs_url="/docs",
                redoc_url="/redoc"
            )
            self._setup_routes()
        else:
            self.app = None

    async def connect_db(self) -> bool:
        """Initialize database connection pool."""
        if not ASYNCPG_AVAILABLE or not self.database_url:
            return False

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5
            )
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    async def close_db(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()

    def _setup_routes(self):
        """Set up FastAPI routes."""
        app = self.app

        @app.on_event("startup")
        async def startup():
            await self.connect_db()

        @app.on_event("shutdown")
        async def shutdown():
            await self.close_db()

        # Health & Info
        @app.get("/api/v1/health")
        async def health_check():
            """Health check endpoint."""
            db_status = "connected" if self.pool else "disconnected"
            return {
                "status": "healthy",
                "version": __version__,
                "database": db_status,
                "timestamp": datetime.utcnow().isoformat()
            }

        @app.get("/api/v1/version")
        async def get_version():
            """Get Ralph version."""
            return {
                "version": __version__,
                "name": "Ralph",
                "description": "Autonomous Coding Agent"
            }

        # Stories CRUD
        @app.get("/api/v1/stories")
        async def list_stories(
            status: Optional[str] = None,
            prefix: Optional[str] = None,
            limit: int = 50
        ):
            """List stories with optional filters."""
            if not self.pool:
                raise HTTPException(status_code=503, detail="Database not connected")

            async with self.pool.acquire() as conn:
                if status and prefix:
                    rows = await conn.fetch(
                        """
                        SELECT story_id, title, description, acceptance_criteria,
                               priority, status, ai_model, created_at, completed_at
                        FROM ralph_stories
                        WHERE status = $1 AND story_id LIKE $2
                        ORDER BY priority ASC
                        LIMIT $3
                        """,
                        status, f"{prefix}%", limit
                    )
                elif status:
                    rows = await conn.fetch(
                        """
                        SELECT story_id, title, description, acceptance_criteria,
                               priority, status, ai_model, created_at, completed_at
                        FROM ralph_stories
                        WHERE status = $1
                        ORDER BY priority ASC
                        LIMIT $2
                        """,
                        status, limit
                    )
                elif prefix:
                    rows = await conn.fetch(
                        """
                        SELECT story_id, title, description, acceptance_criteria,
                               priority, status, ai_model, created_at, completed_at
                        FROM ralph_stories
                        WHERE story_id LIKE $1
                        ORDER BY priority ASC
                        LIMIT $2
                        """,
                        f"{prefix}%", limit
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT story_id, title, description, acceptance_criteria,
                               priority, status, ai_model, created_at, completed_at
                        FROM ralph_stories
                        ORDER BY priority ASC
                        LIMIT $1
                        """,
                        limit
                    )

            return [dict(row) for row in rows]

        @app.post("/api/v1/stories")
        async def create_story(story: StoryCreate, project_id: int = 1):
            """Queue a new story."""
            if not self.pool:
                raise HTTPException(status_code=503, detail="Database not connected")

            async with self.pool.acquire() as conn:
                try:
                    await conn.execute(
                        """
                        INSERT INTO ralph_stories
                        (project_id, story_id, title, description, acceptance_criteria, priority, ai_model, status)
                        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, 'todo')
                        """,
                        project_id,
                        story.story_id,
                        story.title,
                        story.description,
                        json.dumps(story.acceptance_criteria),
                        story.priority,
                        story.ai_model
                    )
                    return {"status": "created", "story_id": story.story_id}
                except Exception as e:
                    raise HTTPException(status_code=400, detail=str(e))

        @app.get("/api/v1/stories/{story_id}")
        async def get_story(story_id: str):
            """Get story status and details."""
            if not self.pool:
                raise HTTPException(status_code=503, detail="Database not connected")

            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT story_id, title, description, acceptance_criteria,
                           priority, status, ai_model, commit_hash, error_message,
                           created_at, started_at, completed_at
                    FROM ralph_stories
                    WHERE story_id = $1
                    """,
                    story_id
                )

            if not row:
                raise HTTPException(status_code=404, detail="Story not found")

            return dict(row)

        @app.patch("/api/v1/stories/{story_id}")
        async def update_story(story_id: str, updates: StoryUpdate):
            """Update a story."""
            if not self.pool:
                raise HTTPException(status_code=503, detail="Database not connected")

            # Build dynamic update query
            set_clauses = []
            values = []
            idx = 1

            if updates.title is not None:
                set_clauses.append(f"title = ${idx}")
                values.append(updates.title)
                idx += 1

            if updates.description is not None:
                set_clauses.append(f"description = ${idx}")
                values.append(updates.description)
                idx += 1

            if updates.acceptance_criteria is not None:
                set_clauses.append(f"acceptance_criteria = ${idx}::jsonb")
                values.append(json.dumps(updates.acceptance_criteria))
                idx += 1

            if updates.priority is not None:
                set_clauses.append(f"priority = ${idx}")
                values.append(updates.priority)
                idx += 1

            if updates.status is not None:
                set_clauses.append(f"status = ${idx}")
                values.append(updates.status)
                idx += 1

            if not set_clauses:
                raise HTTPException(status_code=400, detail="No updates provided")

            values.append(story_id)

            query = f"""
                UPDATE ralph_stories
                SET {', '.join(set_clauses)}
                WHERE story_id = ${idx}
            """

            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *values)

            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Story not found")

            return {"status": "updated", "story_id": story_id}

        @app.delete("/api/v1/stories/{story_id}")
        async def delete_story(story_id: str):
            """Delete a story."""
            if not self.pool:
                raise HTTPException(status_code=503, detail="Database not connected")

            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM ralph_stories WHERE story_id = $1",
                    story_id
                )

            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Story not found")

            return {"status": "deleted", "story_id": story_id}

        # Executions
        @app.post("/api/v1/execute")
        async def start_execution(
            request: ExecutionRequest,
            background_tasks: BackgroundTasks
        ):
            """Start Ralph execution."""
            execution_id = str(uuid.uuid4())[:8]

            execution = Execution(
                id=execution_id,
                status="running",
                started_at=datetime.utcnow()
            )
            self.executions[execution_id] = execution

            # Run in background
            background_tasks.add_task(
                self._run_execution,
                execution_id,
                request
            )

            return {
                "execution_id": execution_id,
                "status": "started",
                "message": f"Execution {execution_id} started"
            }

        @app.get("/api/v1/executions")
        async def list_executions():
            """List all executions."""
            return [asdict(e) for e in self.executions.values()]

        @app.get("/api/v1/executions/{execution_id}")
        async def get_execution(execution_id: str):
            """Get execution details."""
            if execution_id not in self.executions:
                raise HTTPException(status_code=404, detail="Execution not found")

            return asdict(self.executions[execution_id])

    async def _run_execution(
        self,
        execution_id: str,
        request: "ExecutionRequest"
    ) -> None:
        """Run Ralph execution in background."""
        from .ralph_api import RalphAPI

        execution = self.executions[execution_id]
        execution.status = "running"

        project_root = Path(request.project_root) if request.project_root else Path.cwd()

        try:
            ralph = RalphAPI(project_root=project_root)

            stories = ralph.get_pending_stories(
                prefix=request.prefix,
                story_id=request.story_id,
                max_stories=request.max_stories
            )

            for story in stories:
                execution.current_story = story["story_id"]

                ralph.update_story_status(story["story_id"], 'in_progress')

                success, result = ralph.execute_story(
                    story["story_id"],
                    story["title"],
                    story["description"],
                    str(story["acceptance_criteria"]),
                    story["priority"],
                    model=request.model
                )

                if success:
                    commit_hash = result.get("commit_result", "")[:40] if result.get("commit_result") else None
                    ralph.update_story_status(story["story_id"], 'done', commit_hash)
                    execution.stories_completed += 1
                else:
                    ralph.update_story_status(story["story_id"], 'failed')
                    execution.stories_failed += 1

            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            execution.current_story = None

        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()


def create_app() -> Optional[FastAPI]:
    """Create FastAPI application instance."""
    if not FASTAPI_AVAILABLE:
        print("ERROR: FastAPI not installed. Run: pip install fastapi uvicorn")
        return None

    gateway = RalphGateway()
    return gateway.app


def main():
    """Start the Ralph API gateway server."""
    import argparse

    parser = argparse.ArgumentParser(description="Ralph API Gateway Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    if not FASTAPI_AVAILABLE:
        print("ERROR: FastAPI not installed. Run: pip install fastapi")
        sys.exit(1)

    if not UVICORN_AVAILABLE:
        print("ERROR: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)

    print(f"Starting Ralph API Gateway on http://{args.host}:{args.port}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "src.ralph_gateway:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
