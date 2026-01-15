"""Update Ralph stories in database."""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require')

    # Insert/update stories using upsert
    stories = [
        (1, 'NEON-MCP-001', 'Setup Neon MCP Server in Claude Code', 'done', 1),
        (1, 'NEON-MCP-002', 'Add Neon API Key to Environment', 'todo', 2),
        (1, 'NEON-BRANCH-001', 'GitHub PR Auto-Branching with Neon', 'done', 3),
        (1, 'NEON-BRANCH-002', 'PR Branch Cleanup Workflow', 'done', 4),
        (1, 'N8N-NEON-001', 'n8n Workflow for Database Monitoring', 'todo', 5),
        (1, 'N8N-NEON-002', 'Auto-Wake Neon on Bot Start', 'todo', 6),
        (1, 'GITHUB-NEON-001', 'Schema Migration PR Workflow', 'done', 7),
        (1, 'CODERABBIT-001', 'Enable CodeRabbit for PR Reviews', 'done', 8),
        (1, 'LANGFUSE-NEON-001', 'Track LLM Costs with Langfuse', 'done', 9),
        (1, 'RAILWAY-BACKUP-001', 'Railway as Neon Failover', 'done', 10),
    ]

    for project_id, story_id, title, status, priority in stories:
        await conn.execute(
            '''INSERT INTO ralph_stories (project_id, story_id, title, status, priority)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (project_id, story_id) DO UPDATE SET status = EXCLUDED.status, title = EXCLUDED.title''',
            project_id, story_id, title, status, priority
        )
    print(f'Upserted {len(stories)} stories')

    # Show current TODO stories
    print('\nCurrent TODO stories:')
    rows = await conn.fetch("SELECT story_id, title FROM ralph_stories WHERE status = 'todo' ORDER BY priority LIMIT 10")
    for row in rows:
        print(f'  {row["story_id"]:20} | {row["title"][:50]}')

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
