#!/usr/bin/env python
"""
PDF Manual Q&A CLI

Interactive command-line interface for querying PDF manuals.

Usage:
    # Index and query a new PDF
    python -m rivet_pro.cli.manual_qa_cli --manual path/to/manual.pdf --index

    # Query an already-indexed manual by ID
    python -m rivet_pro.cli.manual_qa_cli --manual-id <uuid>

    # Search all indexed manuals
    python -m rivet_pro.cli.manual_qa_cli

Commands in interactive mode:
    /quit, /exit    - Exit the CLI
    /stats          - Show session statistics
    /clear          - Clear conversation history
    /help           - Show help
"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.prompt import Prompt
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    print("Note: Install 'rich' and 'click' for enhanced CLI experience")
    print("  pip install rich click")

import asyncpg

# Import services
from rivet_pro.core.services.manual_qa_service import ManualQAService
from rivet_pro.core.services.manual_indexing_service import ManualIndexingService, index_pdf_directly


console = Console() if HAS_RICH else None


def print_output(text: str, style: str = None):
    """Print output with optional styling."""
    if console:
        console.print(text, style=style)
    else:
        print(text)


def print_panel(content: str, title: str = None):
    """Print content in a panel."""
    if console:
        console.print(Panel(Markdown(content), title=title, border_style="blue"))
    else:
        if title:
            print(f"\n=== {title} ===")
        print(content)
        print()


def print_error(message: str):
    """Print error message."""
    print_output(f"Error: {message}", style="bold red")


def print_success(message: str):
    """Print success message."""
    print_output(f"{message}", style="bold green")


async def get_db_pool() -> asyncpg.Pool:
    """Create database connection pool."""
    # Try to get DATABASE_URL from environment or .env file
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        # Try loading from .env
        env_paths = [
            project_root / ".env",
            project_root / "rivet_pro" / ".env",
        ]
        for env_path in env_paths:
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("DATABASE_URL="):
                            database_url = line.strip().split("=", 1)[1].strip('"\'')
                            break
                if database_url:
                    break

    if not database_url:
        raise ValueError(
            "DATABASE_URL not found. Set it in environment or .env file."
        )

    return await asyncpg.create_pool(database_url, min_size=1, max_size=5)


async def index_manual_cli(pdf_path: str, db_pool: asyncpg.Pool) -> UUID:
    """Index a PDF manual and return its ID."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print_output(f"Indexing: {path.name}...", style="yellow")

    result = await index_pdf_directly(
        db_pool=db_pool,
        pdf_path=str(path.absolute()),
        title=path.stem,
        source="user_upload"
    )

    if not result.success:
        raise RuntimeError(f"Indexing failed: {result.error}")

    print_success(
        f"Indexed {result.chunks_created} chunks in {result.duration_seconds:.1f}s"
    )
    print_output(f"Manual ID: {result.manual_id}")

    return result.manual_id


async def interactive_session(
    db_pool: asyncpg.Pool,
    manual_id: UUID = None,
    title: str = "PDF Manual"
):
    """Run interactive Q&A session."""
    qa_service = ManualQAService(db_pool)

    # Welcome message
    welcome = f"""
# PDF Manual Q&A System

**Manual:** {title if manual_id else 'All indexed manuals'}
**Commands:** /help, /stats, /clear, /quit

Type your question and press Enter.
"""
    print_panel(welcome, title="Welcome")

    # Create session
    import uuid
    session_id = uuid.uuid4()
    session = qa_service._get_or_create_session(session_id, manual_id, None)

    while True:
        try:
            # Get user input
            if console:
                query = Prompt.ask("\n[bold cyan]Your question[/bold cyan]")
            else:
                query = input("\nYour question: ")

            query = query.strip()

            if not query:
                continue

            # Handle commands
            if query.startswith("/"):
                cmd = query.lower()

                if cmd in ("/quit", "/exit", "/q"):
                    print_output("Goodbye!", style="bold green")
                    break

                elif cmd == "/help":
                    help_text = """
## Available Commands

- `/quit`, `/exit` - Exit the CLI
- `/stats` - Show session statistics
- `/clear` - Clear conversation history
- `/help` - Show this help

## Tips

- Ask specific questions about the manual content
- Reference page numbers if you know them
- Use technical terminology for better results
"""
                    print_panel(help_text, title="Help")
                    continue

                elif cmd == "/stats":
                    stats = Table(title="Session Statistics")
                    stats.add_column("Metric", style="cyan")
                    stats.add_column("Value", style="green")
                    stats.add_row("Messages", str(len(session.messages)))
                    stats.add_row("Total Cost", f"${session.total_cost_usd:.4f}")
                    stats.add_row("Manual ID", str(manual_id) if manual_id else "All")

                    if console:
                        console.print(stats)
                    else:
                        print(f"Messages: {len(session.messages)}")
                        print(f"Total Cost: ${session.total_cost_usd:.4f}")
                    continue

                elif cmd == "/clear":
                    session.messages.clear()
                    print_success("Conversation history cleared.")
                    continue

                else:
                    print_error(f"Unknown command: {query}")
                    continue

            # Process question
            print_output("\nSearching manual...", style="dim")

            response = await qa_service.ask(
                query=query,
                manual_id=manual_id,
                session_id=session_id
            )

            # Display response
            response_panel = f"""
{response.answer}

---
**Confidence:** {response.confidence:.0%} | **Sources:** {response.sources_used} | **Cost:** ${response.cost_usd:.4f} | **Model:** {response.model_used}
"""
            print_panel(response_panel, title="Answer")

        except KeyboardInterrupt:
            print_output("\n\nInterrupted. Type /quit to exit.", style="yellow")

        except Exception as e:
            print_error(str(e))


@click.command()
@click.option(
    "--manual", "-m",
    type=click.Path(exists=True),
    help="Path to PDF manual to index and query"
)
@click.option(
    "--manual-id", "-i",
    type=str,
    help="UUID of already-indexed manual"
)
@click.option(
    "--index", "-x",
    is_flag=True,
    help="Index the manual before querying"
)
@click.option(
    "--query", "-q",
    type=str,
    help="Single question (non-interactive mode)"
)
def main(manual: str, manual_id: str, index: bool, query: str):
    """
    PDF Manual Q&A CLI - Ask questions about equipment manuals.

    Examples:

        # Index a new PDF and start interactive session
        python -m rivet_pro.cli.manual_qa_cli --manual manual.pdf --index

        # Query an existing manual
        python -m rivet_pro.cli.manual_qa_cli --manual-id abc-123

        # One-off question
        python -m rivet_pro.cli.manual_qa_cli -q "How to reset?"
    """
    asyncio.run(async_main(manual, manual_id, index, query))


async def async_main(manual: str, manual_id: str, index: bool, query: str):
    """Async entry point."""
    db_pool = None

    try:
        # Connect to database
        print_output("Connecting to database...", style="dim")
        db_pool = await get_db_pool()
        print_success("Connected!")

        target_manual_id = None
        title = "PDF Manual"

        # Handle manual path
        if manual:
            path = Path(manual)
            title = path.stem

            if index:
                # Index the PDF first
                target_manual_id = await index_manual_cli(manual, db_pool)
            else:
                # Check if already indexed by filename
                async with db_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT id FROM manuals WHERE title = $1 LIMIT 1",
                        path.stem
                    )
                    if row:
                        target_manual_id = row['id']
                        print_output(f"Found existing manual: {target_manual_id}")
                    else:
                        print_error(
                            f"Manual not indexed. Use --index flag to index first."
                        )
                        return

        # Handle manual ID
        elif manual_id:
            try:
                target_manual_id = UUID(manual_id)
            except ValueError:
                print_error(f"Invalid UUID: {manual_id}")
                return

            # Verify manual exists
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id, title FROM manuals WHERE id = $1",
                    target_manual_id
                )
                if not row:
                    print_error(f"Manual not found: {manual_id}")
                    return
                title = row['title'] or "PDF Manual"

        # Single query mode
        if query:
            qa_service = ManualQAService(db_pool)
            response = await qa_service.ask(
                query=query,
                manual_id=target_manual_id
            )
            print_panel(response.answer, title="Answer")
            print_output(
                f"Confidence: {response.confidence:.0%} | "
                f"Sources: {response.sources_used} | "
                f"Cost: ${response.cost_usd:.4f}",
                style="dim"
            )
        else:
            # Interactive mode
            await interactive_session(db_pool, target_manual_id, title)

    except Exception as e:
        print_error(str(e))
        raise

    finally:
        if db_pool:
            await db_pool.close()


if __name__ == "__main__":
    main()
