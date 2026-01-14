# WORKING_CONFIG.md - FROZEN CONFIGURATION
# DO NOT MODIFY - This documents the KNOWN WORKING configuration
# Last verified: 2026-01-14 18:47:30

## Database Connections

### PRIMARY DATABASE: Neon PostgreSQL
- **Endpoint**: ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech
- **Database**: 
eondb
- **User**: 
eondb_owner
- **Tables**: 120+
- **Status**: PRODUCTION

> **WARNING**: There is another Neon endpoint ep-lingering-salad-ahbmzx98
> which has only 4 empty tables. DO NOT USE IT.

### BACKUP DATABASE: Supabase
- **Host**: db.mggqgrxwumnnujojndub.supabase.co
- **Database**: postgres
- **Status**: Legacy/Archive (1,985 knowledge atoms)

### FAILOVER ORDER
1. Neon (primary)
2. Turso (backup - to be configured)
3. Supabase (archive/read-only)

## Environment Variables

### Required in .env
```
DATABASE_URL=postgresql://neondb_owner:npg_c3UNa4KOlCeL@ep-purple-hall-ahimeyn0-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require
DATABASE_PROVIDER=neon
DATABASE_FAILOVER_ORDER=neon,turso,supabase
```

## Validation

On startup, the application MUST verify:
1. DATABASE_URL contains ep-purple-hall-ahimeyn0 (correct endpoint)
2. Database connection succeeds
3. Core tables exist (ralph_stories, knowledge_atoms, etc.)

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2026-01-14 | Initial frozen config | stabilize-rivet.ps1 |
