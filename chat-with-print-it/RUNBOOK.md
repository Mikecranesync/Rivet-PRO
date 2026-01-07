# Chat with Print - Operations Runbook

Day-to-day operational procedures for running Chat with Print in production.

## Quick Reference

| Resource | Location |
|----------|----------|
| n8n Dashboard | http://72.60.175.144:5678 |
| Neon Database | https://console.neon.tech |
| Stripe Dashboard | https://dashboard.stripe.com |
| Slack Alerts | #chat-with-print-alerts |
| VPS SSH | `ssh root@72.60.175.144` |

---

## Daily Operations

### Morning Routine (5 minutes)

1. **Check Slack for overnight alerts**
   - Review #chat-with-print-alerts
   - Note any errors or issues

2. **Run health check**
   ```bash
   ssh root@72.60.175.144
   cd /opt/rivet-pro/chat-with-print-it
   ./scripts/healthcheck.sh
   ```
   - All checks should be green
   - If any failures, see Troubleshooting section

3. **Review daily summary**
   - Check Slack for midnight summary message
   - Note metrics: new users, lookups, revenue
   - Compare to previous days for trends

### Weekly Routine (15 minutes)

1. **Review n8n execution logs**
   - Open http://72.60.175.144:5678
   - Click "Executions"
   - Filter by "Last 7 days"
   - Check for failure patterns

2. **Database health check**
   ```sql
   -- Check table sizes
   SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

   -- Check user growth
   SELECT DATE(created_at), COUNT(*)
   FROM users
   WHERE created_at > NOW() - INTERVAL '7 days'
   GROUP BY DATE(created_at)
   ORDER BY DATE(created_at);
   ```

3. **Revenue reconciliation**
   - Stripe Dashboard: Check total revenue
   - Database query:
     ```sql
     SELECT SUM(amount_cents)/100 AS total_revenue_usd
     FROM payments
     WHERE status = 'complete';
     ```
   - Should match Stripe (accounting for test payments)

---

## Common Operations

### Restart n8n Workflows

**When:** After making configuration changes or if workflows are stuck

**Steps:**
1. SSH to VPS: `ssh root@72.60.175.144`
2. Restart n8n service:
   ```bash
   systemctl restart n8n
   # or if using pm2:
   pm2 restart n8n
   ```
3. Wait 30 seconds
4. Verify: http://72.60.175.144:5678/healthz
5. Check workflows are Active in UI

### Check n8n Logs

**When:** Debugging workflow issues or errors

**Steps:**
1. SSH to VPS
2. View logs:
   ```bash
   # If using systemd:
   journalctl -u n8n -n 100 -f

   # If using pm2:
   pm2 logs n8n --lines 100
   ```
3. Look for ERROR or WARN messages
4. Note timestamp and error details

### Query User Data

**When:** User support requests or data lookups

**Common queries:**

```sql
-- Find user by Telegram ID
SELECT * FROM users WHERE telegram_id = 123456789;

-- Find user by username
SELECT * FROM users WHERE telegram_username = 'username';

-- Get user's recent lookups
SELECT l.*
FROM lookups l
JOIN users u ON l.user_id = u.id
WHERE u.telegram_id = 123456789
ORDER BY l.created_at DESC
LIMIT 10;

-- Check user's Pro status
SELECT
    telegram_username,
    is_pro,
    pro_expires_at,
    lookup_count,
    created_at
FROM users
WHERE telegram_id = 123456789;
```

### Manually Upgrade User to Pro

**When:** Customer service request, promotional upgrade, or payment issue resolution

**Steps:**
1. Connect to database:
   ```bash
   psql "$DATABASE_URL"
   ```

2. Update user:
   ```sql
   UPDATE users
   SET
       is_pro = TRUE,
       pro_expires_at = NOW() + INTERVAL '30 days'
   WHERE telegram_id = 123456789;
   ```

3. Verify:
   ```sql
   SELECT telegram_username, is_pro, pro_expires_at
   FROM users
   WHERE telegram_id = 123456789;
   ```

4. Notify user via Telegram bot manually (as admin)

### Reset User's Free Tier Lookups

**When:** Testing, customer goodwill, or error correction

**Steps:**
1. Connect to database
2. Reset count:
   ```sql
   UPDATE users
   SET lookup_count = 0
   WHERE telegram_id = 123456789;
   ```

3. Verify:
   ```sql
   SELECT telegram_username, lookup_count FROM users WHERE telegram_id = 123456789;
   ```

### Process Refund

**When:** Customer requests refund, service issue, or billing dispute

**Steps:**
1. **In Stripe Dashboard:**
   - Payments → Find payment
   - Click "..." menu → "Refund payment"
   - Select full or partial refund
   - Add reason (for records)
   - Confirm refund

2. **In database:**
   ```sql
   -- Find payment
   SELECT * FROM payments WHERE stripe_customer_id = 'cus_xxx';

   -- Update payment status
   UPDATE payments
   SET status = 'refunded'
   WHERE stripe_session_id = 'cs_xxx';

   -- Downgrade user to free tier
   UPDATE users
   SET
       is_pro = FALSE,
       pro_expires_at = NULL
   WHERE stripe_customer_id = 'cus_xxx';
   ```

3. **Notify user** (optional - Stripe sends email automatically)

---

## Incident Response

### Bot Not Responding

**Symptoms:** Users report bot not responding to messages

**Diagnosis:**
1. Check Telegram webhook status:
   ```bash
   curl "https://api.telegram.org/bot$TOKEN/getWebhookInfo"
   ```
   - `pending_update_count` should be 0
   - `url` should match n8n webhook

2. Check n8n health:
   ```bash
   curl http://72.60.175.144:5678/healthz
   ```
   - Should return `{"status":"ok"}`

3. Check workflow status in n8n UI
   - "Chat with Print - Core Bot" should be "Active"

**Resolution:**
1. If webhook issue:
   ```bash
   ./scripts/set_telegram_webhook.sh
   ```

2. If n8n down:
   ```bash
   systemctl restart n8n
   ```

3. If workflow inactive:
   - Open n8n UI
   - Activate workflow manually

4. Test with your personal account

### Payments Not Processing

**Symptoms:** Users complete Stripe checkout but not upgraded to Pro

**Diagnosis:**
1. Check Stripe Dashboard → Webhooks
   - Recent deliveries should show "succeeded"
   - If failed, see error details

2. Check n8n "Stripe Webhook" workflow
   - Should be "Active"
   - Check recent executions for errors

3. Query database:
   ```sql
   SELECT * FROM payments ORDER BY created_at DESC LIMIT 5;
   ```

**Resolution:**
1. If webhook signature mismatch:
   - Verify `STRIPE_WEBHOOK_SECRET` in n8n Variables
   - Should match Stripe Dashboard webhook signing secret

2. If workflow error:
   - Check execution log in n8n
   - Fix code/configuration issue
   - Re-activate workflow

3. Manual fix for affected users:
   - See "Manually Upgrade User to Pro" above
   - Record payment manually in database

### Analysis Not Working (Claude API)

**Symptoms:** Users send photos but get error or timeout

**Diagnosis:**
1. Check n8n execution log for Claude API errors
2. Check Claude API status: https://status.anthropic.com
3. Verify `ANTHROPIC_API_KEY` in n8n Variables

**Resolution:**
1. If API key issue:
   - Regenerate key at https://console.anthropic.com
   - Update in n8n Variables

2. If rate limit hit:
   - Wait for limit reset (check error message)
   - Consider upgrading Claude API tier

3. If timeout:
   - Check if photo is unusually large
   - Increase timeout in workflow (HTTP Request node)

### Database Connection Lost

**Symptoms:** All workflows failing with database errors

**Diagnosis:**
1. Check Neon dashboard - database should be "Active"
2. Test connection:
   ```bash
   psql "$DATABASE_URL" -c "SELECT 1;"
   ```

**Resolution:**
1. If Neon database suspended:
   - Check Neon email for notices
   - Upgrade plan if needed
   - Database should auto-resume

2. If connection string changed:
   - Get new connection string from Neon
   - Update `DATABASE_URL` environment variable
   - Update credentials in n8n workflows

3. If SSL issue:
   - Ensure `?sslmode=require` in `DATABASE_URL`
   - Update PostgreSQL credentials in n8n

---

## Performance Monitoring

### Response Time Tracking

**Query average analysis time:**
```sql
SELECT
    DATE(created_at) AS date,
    AVG(processing_time_ms)/1000 AS avg_seconds,
    MAX(processing_time_ms)/1000 AS max_seconds,
    COUNT(*) AS total_analyses
FROM lookups
WHERE created_at > NOW() - INTERVAL '7 days'
    AND success = TRUE
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**Target:** < 30 seconds average

### Error Rate Tracking

**Query daily error rate:**
```sql
SELECT
    DATE(created_at) AS date,
    COUNT(*) FILTER (WHERE success = FALSE) AS failures,
    COUNT(*) AS total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE success = FALSE) / COUNT(*), 2) AS error_rate_pct
FROM lookups
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**Target:** < 5% error rate

### User Growth Tracking

```sql
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS new_users,
    SUM(COUNT(*)) OVER (ORDER BY DATE(created_at)) AS total_users
FROM users
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;
```

---

## Scheduled Maintenance

### Weekly Tasks

**Sunday nights, off-peak hours:**

1. **Backup verification**
   - Check Neon automated backups
   - Verify latest backup timestamp
   - Test restore if possible (to staging)

2. **Workflow export**
   ```bash
   # Export workflows from n8n UI
   # Save to git
   git add n8n-workflows/*.json
   git commit -m "Weekly workflow backup $(date +%Y-%m-%d)"
   git push
   ```

3. **Log rotation** (if needed)
   ```bash
   ssh root@72.60.175.144
   # If logs are large
   journalctl --vacuum-time=7d
   ```

### Monthly Tasks

1. **Database cleanup** (optional, if tables very large)
   ```sql
   -- Archive lookups older than 90 days
   -- (Only if table size becomes an issue)
   DELETE FROM lookups WHERE created_at < NOW() - INTERVAL '90 days';
   ```

2. **SSL certificate renewal** (if using custom domain)
   - Check expiration: `certbot certificates`
   - Renew if needed: `certbot renew`

3. **Dependency updates** (if applicable)
   - Update n8n: `npm install -g n8n@latest`
   - Restart: `systemctl restart n8n`

---

## User Support

### Common User Questions

**Q: "Why am I not getting responses?"**
1. Check if bot is online (health check)
2. Check if user hit free tier limit:
   ```sql
   SELECT lookup_count, is_pro FROM users WHERE telegram_id = xxx;
   ```
3. Check recent lookups for errors:
   ```sql
   SELECT error_message FROM lookups
   WHERE telegram_id = xxx
   ORDER BY created_at DESC LIMIT 5;
   ```

**Q: "I paid but still can't use unlimited"**
1. Check payment in Stripe Dashboard
2. Check user's Pro status in database
3. If payment succeeded but not upgraded:
   - Manually upgrade (see above)
   - Investigate webhook issue

**Q: "Can I get a refund?"**
- Follow "Process Refund" procedure above
- Document reason for records

**Q: "How do I cancel my subscription?"**
1. Users should email/contact support
2. Cancel in Stripe Dashboard:
   - Customers → Find customer → Subscriptions → Cancel
3. Stripe webhook will auto-downgrade user to free tier

---

## Alerts & Notifications

### Slack Alert Types

| Alert | Priority | Action Required |
|-------|----------|-----------------|
| 🚨 Database connection failed | CRITICAL | Immediate - check Neon status |
| ❌ Workflow execution failed | HIGH | Within 1 hour - check logs |
| 💳 New Pro subscriber | INFO | None - celebrate! |
| 👤 New user signup | INFO | None - monitor growth |
| 📊 Daily summary | INFO | Review metrics |

### Alert Response Times

- **CRITICAL:** Respond within 15 minutes
- **HIGH:** Respond within 1 hour
- **INFO:** Review daily

---

## Backup & Disaster Recovery

### Daily Automated Backups

- **Database:** Neon automatic backups (check Neon dashboard)
- **Workflows:** Exported to git weekly
- **Configuration:** Environment variables documented in `.env.production`

### Restore Procedure

1. **Database restore:**
   - Neon dashboard → Backups → Restore to point in time
   - Or create new branch from backup

2. **Workflow restore:**
   ```bash
   git checkout main
   git pull
   # Import n8n-workflows/*.json via n8n UI
   ```

3. **Reconfigure credentials:**
   - Follow DEPLOYMENT.md Phase 3

### Disaster Scenarios

**Scenario: VPS completely down**
1. Spin up new VPS
2. Install n8n: `npm install -g n8n`
3. Import workflows from git
4. Configure environment variables
5. Run `./scripts/deploy.sh` for database
6. Update Telegram webhook to new IP
7. Update Stripe webhook to new IP

**Scenario: Database corrupted**
1. Restore from Neon backup (latest good state)
2. Test database connectivity
3. Restart n8n workflows
4. Verify with test transactions

---

## Contact & Escalation

**On-call contact:** [Your contact info]

**Escalation path:**
1. Check this runbook first
2. Review DEPLOYMENT.md troubleshooting
3. Check n8n execution logs
4. Check Slack for clues
5. If unresolved, contact [escalation contact]

**External dependencies support:**
- Neon Database: support@neon.tech
- Stripe: https://support.stripe.com
- n8n: https://community.n8n.io

---

**Last updated:** 2026-01-07
**Version:** 1.0
