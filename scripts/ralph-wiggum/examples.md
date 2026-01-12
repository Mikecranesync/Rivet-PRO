# Ralph Wiggum Examples for Rivet Pro

## Simple Features

### Add a Telegram Bot Command
```bash
/ralph-loop "Add a /ping command to the Telegram bot in rivet_pro/bot/ that replies with 'Pong!'. Test it manually." \
  --completion-promise "command works" \
  --max-iterations 5
```

### Create a Test Utility
```bash
/ralph-loop "Create a test utility function in rivet_pro/core/utils.py that validates equipment IDs. Include tests." \
  --completion-promise "tests pass" \
  --max-iterations 5
```

## Database Migrations

### Create a New Table
```bash
/ralph-loop "Create migration 013_add_user_preferences.sql with columns: user_id, theme (varchar), notifications_enabled (boolean), created_at. Include appropriate indexes." \
  --completion-promise "migration file created" \
  --max-iterations 3
```

### Add Columns to Existing Table
```bash
/ralph-loop "Create migration to add last_login_at (timestamp) and login_count (integer) columns to users table. Use IF NOT EXISTS pattern." \
  --completion-promise "migration ready" \
  --max-iterations 3
```

## Bug Fixes

### Fix Timeout Issue
```bash
/ralph-loop "Fix the photo upload timeout in rivet_pro/bot/handlers.py. Current timeout is 30 seconds, increase to 60 seconds. Test with a sample photo." \
  --completion-promise "timeout increased and tested" \
  --max-iterations 7
```

### Fix Error Handling
```bash
/ralph-loop "Improve error handling in the equipment lookup service. Add try-catch for database errors and return user-friendly messages." \
  --completion-promise "error handling improved" \
  --max-iterations 8
```

## Code Analysis

### Generate Documentation
```bash
/ralph-loop "Read all Telegram bot commands in rivet_pro/bot/ and create a markdown document bot_commands.md listing each command with description and usage." \
  --completion-promise "documentation complete" \
  --max-iterations 3
```

### Audit Configuration
```bash
/ralph-loop "Read rivet_pro/config/settings.py and create config_audit.md listing all environment variables needed with descriptions and whether they're required or optional." \
  --completion-promise "audit complete" \
  --max-iterations 3
```

## Refactoring

### Extract Duplicate Code
```bash
/ralph-loop "Find duplicate code in rivet_pro/bot/handlers.py and extract it into reusable functions in rivet_pro/bot/utils.py. Update handlers to use the new functions." \
  --completion-promise "refactoring complete and tested" \
  --max-iterations 10
```

### Optimize Database Queries
```bash
/ralph-loop "Review database queries in rivet_pro/atlas/services.py and optimize slow queries. Add indexes if needed. Document changes in optimization_notes.md." \
  --completion-promise "queries optimized" \
  --max-iterations 15
```

## Testing

### Add Unit Tests
```bash
/ralph-loop "Create unit tests for the UsageService in rivet_pro/core/services/usage_service.py. Test all methods including edge cases." \
  --completion-promise "tests written and passing" \
  --max-iterations 10
```

### Integration Test
```bash
/ralph-loop "Create an integration test for the photo upload flow: upload → OCR → equipment lookup → save to DB. Test with a sample image." \
  --completion-promise "integration test passes" \
  --max-iterations 12
```

## Complete Features

### User Preferences System
```bash
/ralph-loop "Implement user preferences system:
1. Create migration for user_preferences table
2. Add UserPreferencesService in rivet_pro/core/services/
3. Add /settings command to bot to view/update preferences
4. Test all functionality
Complete when all tests pass and bot command works." \
  --completion-promise "feature complete and tested" \
  --max-iterations 20
```

### Email Notifications
```bash
/ralph-loop "Add email notification feature:
1. Create EmailService using SMTP
2. Add email column to users table (new migration)
3. Send email when work order is created
4. Add /email_settings command to bot
5. Test with real email
Complete when emails are sent successfully." \
  --completion-promise "emails working" \
  --max-iterations 25
```

## Debugging

### Investigate Bug
```bash
/ralph-loop "Investigate why the equipment lookup sometimes returns null even when equipment exists. Check database queries, add logging, identify root cause, and create a fix proposal in bug_analysis.md." \
  --completion-promise "root cause identified" \
  --max-iterations 10
```

### Performance Analysis
```bash
/ralph-loop "Analyze the performance of the photo upload endpoint. Measure current response time, identify bottlenecks, and document findings in performance_report.md with specific optimization recommendations." \
  --completion-promise "analysis complete" \
  --max-iterations 8
```

## Data Operations

### Database Query
```bash
/ralph-loop "Connect to Supabase database and query the users table to count total users, active Pro users, and free users. Save results to user_stats.txt." \
  --completion-promise "stats saved" \
  --max-iterations 5
```

### Data Migration
```bash
/ralph-loop "Create a script to migrate old equipment data from equipment_old table to equipment table. Include validation and rollback capability. Document in migration_notes.md." \
  --completion-promise "migration script ready" \
  --max-iterations 15
```

## Tips for Writing Good Ralph Tasks

### Be Specific
❌ Bad: "Fix the bot"
✅ Good: "Fix the /equip command that returns 404 error when searching for motors"

### Define Clear Success Criteria
❌ Bad: --completion-promise "done"
✅ Good: --completion-promise "tests pass and bot responds correctly"

### Set Appropriate Iteration Limits
- Simple tasks: 3-5 iterations
- Medium tasks: 5-10 iterations
- Complex features: 15-25 iterations
- Never exceed 30 iterations without reviewing

### Include Context
✅ "In rivet_pro/bot/handlers.py, find the _handle_photo function and..."
✅ "The UsageService is in rivet_pro/core/services/usage_service.py..."

### Test Requirements
✅ "Test with a sample photo upload"
✅ "Run pytest on the new tests"
✅ "Manually test the /settings command in Telegram"

## Using the Wrapper Script

Instead of typing the full command, use the wrapper:

```bash
cd scripts/ralph-wiggum
./run-ralph.sh "Add /ping command to bot" "command works" 5
```

This automatically sets:
- Model: claude-3-5-sonnet
- Temperature: 0.7
- Custom iteration limit (default 10)

## Next Steps

1. Start with simple tasks to understand Ralph's behavior
2. Monitor token usage and cost
3. Gradually increase task complexity
4. Document learnings for future tasks

See [prd_template.md](./prd_template.md) for planning larger features.
