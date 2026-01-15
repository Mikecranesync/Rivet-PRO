"""
Request tracing system for end-to-end visibility.
Saves granular traces to traces/ folder AND database for debugging and analytics.

Usage:
    from rivet_pro.infra.tracer import get_tracer

    tracer = get_tracer()
    trace = tracer.start_trace(
        telegram_id=user.id,
        username=user.username,
        request_type="photo"
    )
    trace.add_step("message_received", "success", {"message_id": 123})
    trace.add_step("ocr_analysis", "success", {"provider": "gemini", "cost": 0.002})
    trace.complete(outcome="success", llm_cost=0.002)
    await tracer.save_trace(trace, db_pool)
"""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from rivet_pro.infra.observability import get_logger

logger = get_logger(__name__)


@dataclass
class TraceStep:
    """A single step in a request trace."""
    step: int
    name: str
    timestamp: str
    duration_ms: int
    status: str  # success, error, skipped, miss
    data: dict = field(default_factory=dict)


@dataclass
class RequestTrace:
    """
    Complete trace of a single request from receipt to response.
    Tracks every step with timing and status.
    """
    trace_id: str
    timestamp: str
    user: dict
    request: dict
    steps: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    # Internal tracking (not serialized)
    _step_count: int = field(default=0, repr=False)
    _start_time: datetime = field(default=None, repr=False)
    _last_step_time: datetime = field(default=None, repr=False)

    def add_step(self, name: str, status: str, data: dict = None) -> TraceStep:
        """
        Add a step to the trace with automatic timing.

        Args:
            name: Step name (e.g., 'ocr_analysis', 'kb_search')
            status: One of 'success', 'error', 'skipped', 'miss'
            data: Optional dict with step-specific data

        Returns:
            The created TraceStep
        """
        now = datetime.utcnow()
        self._step_count += 1

        # Calculate duration since last step
        duration_ms = 0
        if self._last_step_time:
            duration_ms = int((now - self._last_step_time).total_seconds() * 1000)

        step = TraceStep(
            step=self._step_count,
            name=name,
            timestamp=now.isoformat() + "Z",
            duration_ms=duration_ms,
            status=status,
            data=data or {}
        )
        self.steps.append(asdict(step))
        self._last_step_time = now

        # Log each step for real-time visibility
        logger.debug(f"Trace step | {self.trace_id} | {name} | {status} | {duration_ms}ms")

        return step

    def complete(self, outcome: str, llm_cost: float = 0.0) -> None:
        """
        Finalize the trace with summary statistics.

        Args:
            outcome: Final outcome (e.g., 'success', 'error', 'manual_not_found')
            llm_cost: Total LLM cost in USD
        """
        total_ms = int((datetime.utcnow() - self._start_time).total_seconds() * 1000)
        self.summary = {
            "total_duration_ms": total_ms,
            "outcome": outcome,
            "llm_cost_usd": llm_cost,
            "steps_completed": len([s for s in self.steps if s["status"] == "success"]),
            "steps_failed": len([s for s in self.steps if s["status"] == "error"]),
            "steps_skipped": len([s for s in self.steps if s["status"] == "skipped"])
        }

        logger.info(
            f"Trace complete | {self.trace_id} | {outcome} | "
            f"{total_ms}ms | ${llm_cost:.4f} | "
            f"{self.summary['steps_completed']} steps"
        )

    def to_dict(self) -> dict:
        """Convert trace to dictionary, excluding internal fields."""
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "user": self.user,
            "request": self.request,
            "steps": self.steps,
            "summary": self.summary
        }

    def save_to_file(self, traces_dir: Path) -> Path:
        """
        Save trace to JSON file in date-organized folder.

        Args:
            traces_dir: Base traces directory

        Returns:
            Path to the saved file
        """
        # Create date folder
        date_folder = traces_dir / datetime.utcnow().strftime("%Y-%m-%d")
        date_folder.mkdir(parents=True, exist_ok=True)

        # Generate filename: HH-MM-SS_user-ID_type.json
        ts = datetime.utcnow().strftime("%H-%M-%S")
        user_id = self.user.get("telegram_id", "unknown")
        req_type = self.request.get("type", "unknown")
        filename = f"{ts}_user-{user_id}_{req_type}.json"

        filepath = date_folder / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

        return filepath


class Tracer:
    """
    Factory for creating and saving request traces.
    Supports both file and database storage.
    """

    def __init__(self, traces_dir: str = None):
        """
        Initialize tracer with optional custom traces directory.

        Args:
            traces_dir: Path to traces folder. Defaults to project_root/traces
        """
        if traces_dir:
            self.traces_dir = Path(traces_dir)
        else:
            # Default to project root/traces
            self.traces_dir = Path(__file__).parent.parent.parent / "traces"

        self.traces_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Tracer initialized | traces_dir={self.traces_dir}")

    def start_trace(
        self,
        telegram_id: int,
        username: str,
        request_type: str,
        **request_data
    ) -> RequestTrace:
        """
        Start a new request trace.

        Args:
            telegram_id: User's Telegram ID
            username: User's Telegram username
            request_type: Type of request ('photo', 'text', 'command')
            **request_data: Additional request metadata

        Returns:
            New RequestTrace instance
        """
        now = datetime.utcnow()
        trace = RequestTrace(
            trace_id=f"tr_{uuid4().hex[:12]}",
            timestamp=now.isoformat() + "Z",
            user={"telegram_id": telegram_id, "username": username},
            request={"type": request_type, **request_data}
        )
        trace._start_time = now
        trace._last_step_time = now

        logger.debug(f"Trace started | {trace.trace_id} | user={telegram_id} | type={request_type}")

        return trace

    async def save_trace(self, trace: RequestTrace, db_pool=None) -> Path:
        """
        Save completed trace to file and optionally database.

        Args:
            trace: Completed RequestTrace
            db_pool: Optional asyncpg pool for database storage

        Returns:
            Path to saved file
        """
        # Save to file
        filepath = trace.save_to_file(self.traces_dir)
        logger.info(f"Trace saved to file | {trace.trace_id} | {filepath}")

        # Save to database if pool provided
        if db_pool:
            try:
                await self._save_to_db(trace, db_pool)
                logger.debug(f"Trace saved to DB | {trace.trace_id}")
            except Exception as e:
                # Don't fail the request if DB save fails
                logger.error(f"Failed to save trace to DB | {trace.trace_id} | {e}")

        return filepath

    async def _save_to_db(self, trace: RequestTrace, db_pool) -> None:
        """Save trace to request_traces table."""
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO request_traces (
                    trace_id, telegram_id, username, request_type,
                    steps, summary, outcome, total_duration_ms, llm_cost_usd
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                trace.trace_id,
                trace.user.get("telegram_id"),
                trace.user.get("username"),
                trace.request.get("type"),
                json.dumps(trace.steps),
                json.dumps(trace.summary),
                trace.summary.get("outcome"),
                trace.summary.get("total_duration_ms"),
                trace.summary.get("llm_cost_usd", 0)
            )


# Singleton instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get or create singleton Tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
