# Database Connection Fix Applied

## Problem Identified

**Error You Were Seeing:**
```
Could not open JPA EntityManager for transaction
nested exception is org.hibernate.exception.JDBCConnectionException:
Unable to acquire JDBC Connection
```

**Root Cause:**
The database URL in `docker-compose.yml` was incorrectly formatted.

## What Was Wrong

**File:** `C:\Users\hharp\OneDrive\Desktop\grashjs-cmms\docker-compose.yml`
**Line:** 23

**BEFORE (Incorrect):**
```yaml
DB_URL: postgres/atlas
```

**AFTER (Fixed):**
```yaml
DB_URL: jdbc:postgresql://postgres:5432/atlas
```

## Why This Matters

Spring Boot (the Java framework running the CMMS backend) requires a full JDBC connection URL in this format:

```
jdbc:postgresql://[hostname]:[port]/[database_name]
```

The shortened format `postgres/atlas` is not valid for JDBC and caused the backend to fail when trying to connect to the database.

## How to Apply the Fix

### Option 1: Run the Restart Script (Easiest)

Double-click this file:
```
C:\Users\hharp\OneDrive\Desktop\grashjs-cmms\restart_cmms.bat
```

This will:
1. Stop all CMMS containers
2. Start them with the fixed configuration
3. Wait for services to be ready

### Option 2: Manual Restart

```bash
cd C:\Users\hharp\OneDrive\Desktop\grashjs-cmms
docker-compose down
docker-compose up -d
```

Then wait 30 seconds for services to start.

## Verify the Fix

### Step 1: Check Backend Logs

```bash
docker logs atlas-cmms-backend --tail 50
```

**Look for:**
- "Hikari CP connection pool started" (GOOD)
- "Database connection successful" (GOOD)
- No more "Unable to acquire JDBC Connection" (GOOD)

### Step 2: Test the Web UI

1. Open: http://localhost:3001
2. Try to create a new account OR
3. Try to login with: mike@cranesync.com

You should no longer see the JPA/JDBC error.

### Step 3: Test Login from Bot

After restart, try the login test:

```bash
cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
python test_login.py
```

## If You Still Have Issues

### Database Container Not Running

```bash
# Check if postgres container is up
docker ps | findstr atlas_db

# If not running, check logs
docker logs atlas_db
```

### Backend Container Crashes

```bash
# Check backend logs for errors
docker logs atlas-cmms-backend

# Look for:
# - Port conflicts (8080 already in use)
# - Missing environment variables
# - Database connection timeout
```

### Account Already Exists Error

If you see "Email already registered":

1. Go to http://localhost:3001
2. Click "Forgot Password" (if available)
3. OR use a different email to create new account
4. OR reset the database:
   ```bash
   docker-compose down -v  # This deletes ALL data!
   docker-compose up -d
   ```

## Files Changed

1. `grashjs-cmms/docker-compose.yml` (line 23) - Fixed DB_URL
2. `grashjs-cmms/restart_cmms.bat` - Created restart script
3. `Rivet-PRO/DATABASE_FIX_APPLIED.md` - This documentation

## Next Steps After Fix

1. **Restart containers** - Run restart_cmms.bat
2. **Test login** - Go to http://localhost:3001
3. **Update bot credentials** - If password is different, run:
   ```bash
   cd C:\Users\hharp\OneDrive\Desktop\Rivet-PRO
   python fix_credentials.py
   ```
4. **Test bot** - Run START_RIVET.bat from Desktop

## Technical Details

**Database Configuration:**
- Container: atlas_db (postgres:16-alpine)
- Database Name: atlas
- Internal Port: 5432
- External Port: 5435
- Username: rivet_admin (from .env)
- Password: rivet_secure_password_2026 (from .env)

**Connection String Breakdown:**
- `jdbc:postgresql://` - JDBC protocol for PostgreSQL
- `postgres` - Hostname (Docker service name, containers on same network)
- `:5432` - Internal PostgreSQL port (not 5435, that's external)
- `/atlas` - Database name

**Why "postgres" and not "localhost"?**
The backend container connects to the database container via Docker's internal network. The service name "postgres" (from docker-compose.yml) is the hostname, not "localhost".

## Summary

**Problem:** Database URL was malformed
**Solution:** Changed to proper JDBC format
**Action Required:** Restart containers using restart_cmms.bat
**Expected Result:** Database connection works, no more JPA errors
**Time to Fix:** 2 minutes (just run the restart script)

---

**The fix has been applied to the file. You just need to restart the containers to make it active!**
