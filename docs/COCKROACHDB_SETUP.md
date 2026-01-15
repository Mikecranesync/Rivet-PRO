# CockroachDB Setup Guide

> Emergency failover database for Rivet Pro. Only used when both Neon and Supabase are down.

## Why CockroachDB?

- **5GB free tier** (vs Supabase's 500MB)
- **PostgreSQL wire compatible** - works with existing code
- **Scale-to-zero** - no cost when idle
- **99.99% SLA** on serverless tier
- **No credit card required**

## Setup Steps

### Step 1: Create Account

1. Go to https://cockroachlabs.com/
2. Click **"Get Started Free"**
3. Sign up with GitHub, Google, or email

### Step 2: Create Serverless Cluster

1. After login, click **"Create Cluster"**
2. Select **"Serverless"** (free tier)
3. Choose cloud provider:
   - **AWS** (recommended) or **GCP**
4. Choose region closest to your users:
   - `us-east-1` for US East Coast
   - `us-west-2` for US West Coast
   - `eu-central-1` for Europe
5. Name your cluster: `rivet-pro-emergency`
6. Click **"Create Cluster"**

### Step 3: Create SQL User

1. Go to **SQL Users** tab
2. Click **"Add User"**
3. Username: `rivet_admin`
4. Generate password (save it!)
5. Click **"Create"**

### Step 4: Get Connection String

1. Click **"Connect"** button on your cluster
2. Select **"Connection string"** tab
3. Choose **"General connection string"**
4. Copy the connection string - it looks like:

```
postgresql://rivet_admin:YOUR_PASSWORD@free-tier14.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full
```

### Step 5: Update .env

Replace the placeholder in `.env`:

```bash
# Before (placeholder)
COCKROACH_DB_URL=postgresql://your_user:your_password@free-tier.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full

# After (your actual connection string)
COCKROACH_DB_URL=postgresql://rivet_admin:YOUR_ACTUAL_PASSWORD@free-tier14.aws-us-east-1.cockroachlabs.cloud:26257/defaultdb?sslmode=verify-full
```

### Step 6: Test Connection

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python scripts/test_failover.py --simulate
```

Expected output:
```
Configured providers: ['neon', 'supabase', 'cockroachdb']
TEST 2: Simulated Neon Failure -> Supabase Failover
✓ Failover successful! Connected to: supabase
```

## Database Schema Sync

CockroachDB needs the same tables as Neon. To sync:

### Option 1: Manual Schema Creation

1. Go to CockroachDB Console > SQL Shell
2. Run the migrations from `rivet_pro/migrations/`

### Option 2: Use pg_dump (Recommended)

```bash
# Export schema from Neon
pg_dump $DATABASE_URL --schema-only > schema.sql

# Import to CockroachDB (may need minor adjustments)
psql $COCKROACH_DB_URL < schema.sql
```

### Known CockroachDB Differences

| Feature | PostgreSQL | CockroachDB | Notes |
|---------|------------|-------------|-------|
| SERIAL | Native | Emulated | Works, but uses sequences differently |
| JSONB | Full support | Full support | ✓ Compatible |
| Arrays | Full support | Full support | ✓ Compatible |
| Full-text search | Native | Limited | May need adjustments |
| Extensions | Many | Few | pgvector NOT supported |

**Important:** CockroachDB does NOT support `pgvector`. If your app uses vector embeddings, those queries will fail on CockroachDB. This is acceptable for emergency failover since core CMMS functionality will still work.

## Free Tier Limits

| Resource | Limit |
|----------|-------|
| Storage | 5 GB |
| Request Units | 50M/month |
| Clusters | Unlimited |
| Regions | 1 per cluster |

## Monitoring

1. Go to CockroachDB Console
2. Click your cluster
3. View **Metrics** tab for:
   - Request Units usage
   - Storage usage
   - Query latency

## Troubleshooting

### "Connection refused"
- Check if cluster is active (may be paused after inactivity)
- Verify IP allowlist includes your server

### "SSL certificate error"
- Ensure `sslmode=verify-full` is in connection string
- Download root cert if needed: https://cockroachlabs.com/docs/cockroachcloud/connect-to-a-serverless-cluster

### "Relation does not exist"
- Schema not synced - run migrations on CockroachDB

## Links

- [CockroachDB Docs](https://www.cockroachlabs.com/docs/)
- [PostgreSQL Compatibility](https://www.cockroachlabs.com/docs/stable/postgresql-compatibility)
- [Serverless FAQ](https://www.cockroachlabs.com/docs/cockroachcloud/serverless-faqs)
