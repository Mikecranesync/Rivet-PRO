# VPS Crash Diagnosis & Fix Plan

**Status:** CRITICAL - System in crash loop
**Date:** 2026-01-12 07:40 UTC
**Load Average:** 7.61 (15-min) on 1-CPU system (760% overload)

---

## ROOT CAUSE IDENTIFIED

### The Smoking Gun

**rivet-worker.service has crashed and restarted 14,535 times**

```
Scheduled restart job, restart counter is at 14535
```

This service is in a perpetual crash loop, consuming resources every 10 seconds:
1. Starts → 2. Begins ingestion → 3. Crashes → 4. Restarts → Repeat

Each restart spikes CPU, creating cascading failures across all services.

---

## Critical Issues

### Issue #1: CPU Starvation (PRIMARY CAUSE)
- **1 CPU** handling 10+ concurrent services
- **Load Average: 7.61** (should be < 1.0 for healthy system)
- Services timing out waiting for CPU time

**Current CPU Consumers:**
| Process | CPU % | RAM | Status |
|---------|-------|-----|--------|
| rivet_worker.py | 45.5% | 216MB | **Crash loop - 14,535 restarts** |
| fast_worker.py | 4.2% | 177MB | Running 8 days continuously |
| n8n | 0.5% | 299MB | Spikes higher under load |
| Ollama | 0.3% | 32MB | AI model server (just restarted) |
| Java Spring Boot | 0.3% | 330MB | Running |
| langgraph_app.worker | 0.2% | 143MB | Running since Jan 04 |
| Docker/Containerd | 0.3% | - | Container runtime |
| Redis | 0.3% | 5MB | Database |

**Total: >50% CPU baseline, spikes to 100%+ during ingestion**

### Issue #2: No Swap Space
- **0 bytes swap configured**
- When RAM fills, system has nowhere to overflow
- Leads to process kills and crashes

### Issue #3: Resource Conflict
**Two ingestion workers running simultaneously:**
- `rivet-worker.service` (systemd managed, crash looping)
- `fast_worker.py` (running standalone for 8 days)

Both are competing for the same CPU/memory resources.

### Issue #4: Failed Services
```
● nginx.service - FAILED
● rivet-scheduler.service - FAILED (every 4 hours)
● unattended-upgrades.service - FAILED
```

nginx failure means web traffic routing is broken.

---

## Resource Analysis

### CPU (1 core)
- **Current Load:** 7.61 (760% overload)
- **Healthy Load:** < 1.0
- **Status:** CRITICAL - severe starvation

### Memory (3.8GB total)
- **Used:** 1.8GB (47%)
- **Available:** 2.0GB
- **Status:** OK currently, but no safety margin

### Disk
- **Used:** 37GB / 48GB (78%)
- **Status:** WARN - getting full

### Swap
- **Configured:** 0 bytes
- **Status:** CRITICAL - no overflow capacity

---

## Fix Plan

### IMMEDIATE ACTIONS (Stop the bleeding)

#### 1. Stop the Crash Loop
```bash
# Stop rivet-worker service
ssh root@72.60.175.144 "systemctl stop rivet-worker.service && systemctl disable rivet-worker.service"
```

#### 2. Stop Duplicate Workers
```bash
# Kill fast_worker.py (running 8 days)
ssh root@72.60.175.144 "pkill -f fast_worker.py"

# Kill duplicate rivet_worker processes
ssh root@72.60.175.144 "pkill -f rivet_worker.py"
```

#### 3. Stop Non-Essential Services
```bash
# Stop Ollama (AI model server - not needed for core functionality)
ssh root@72.60.175.144 "systemctl stop ollama && systemctl disable ollama"

# Stop langgraph worker
ssh root@72.60.175.144 "pkill -f langgraph_app.worker"
```

#### 4. Restart nginx (if needed)
```bash
ssh root@72.60.175.144 "systemctl restart nginx"
```

### SHORT-TERM FIXES (Next 24 hours)

#### 5. Add Swap Space
```bash
# Create 4GB swap file
ssh root@72.60.175.144 "
  fallocate -l 4G /swapfile && \
  chmod 600 /swapfile && \
  mkswap /swapfile && \
  swapon /swapfile && \
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
"
```

#### 6. Fix rivet-worker Service
The service needs to be redesigned to:
- Run only when triggered (not 24/7)
- Use job queue with rate limiting
- Have better resource constraints

**Temporary Fix - Lower resource limits:**
```bash
ssh root@72.60.175.144 "cat > /etc/systemd/system/rivet-worker.service << 'EOF'
[Unit]
Description=RIVET KB Ingestion Worker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Agent-Factory
Environment=PATH=/root/.local/bin:/usr/local/bin:/usr/bin
EnvironmentFile=/root/Agent-Factory/.env
ExecStart=/root/.local/bin/poetry run python scripts/rivet_worker.py

# More aggressive resource limits
MemoryMax=256M
CPUQuota=25%

# Don't restart on failure - let it fail and investigate
Restart=no
TimeoutStopSec=30
KillMode=process

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
"
```

#### 7. Clean Up Disk Space
```bash
# Remove old logs
ssh root@72.60.175.144 "journalctl --vacuum-time=7d"

# Clean up Docker
ssh root@72.60.175.144 "docker system prune -af"
```

### LONG-TERM FIXES (This week)

#### 8. Upgrade VPS Resources
**Current:** 1 CPU, 3.8GB RAM
**Minimum Needed:** 2 CPUs, 4GB RAM
**Recommended:** 4 CPUs, 8GB RAM

With current workload, you need more CPU capacity.

#### 9. Implement Job Queue System
Replace 24/7 workers with on-demand processing:
- Use Redis queue (already installed)
- Process jobs one at a time
- Rate limit to prevent overload

#### 10. Service Architecture Review
Split services across multiple VPS instances:
- **VPS 1:** Web API + Bot (user-facing)
- **VPS 2:** Workers + n8n (background processing)
- **VPS 3:** Ollama + AI models (heavy compute)

---

## Execution Order

### Phase 1: Emergency Stop (5 minutes)
1. Stop rivet-worker.service
2. Kill duplicate worker processes
3. Stop Ollama
4. Verify load drops below 2.0

### Phase 2: Stability (30 minutes)
5. Add swap space
6. Restart nginx
7. Verify all essential services running
8. Monitor for 1 hour

### Phase 3: Prevention (Next day)
9. Fix service configurations
10. Clean up disk space
11. Set up monitoring alerts

### Phase 4: Scale (This week)
12. Upgrade VPS or split services
13. Implement job queue
14. Load testing

---

## Monitoring Commands

### Check Load
```bash
ssh root@72.60.175.144 "uptime"
```

### Check Top Processes
```bash
ssh root@72.60.175.144 "ps aux --sort=-%cpu | head -15"
```

### Check Service Status
```bash
ssh root@72.60.175.144 "systemctl status rivet-bot rivet-api n8n"
```

### Check Crash Counter
```bash
ssh root@72.60.175.144 "systemctl status rivet-worker | grep 'restart counter'"
```

---

## Expected Results

### After Phase 1
- Load average drops from 7.61 to < 2.0
- CPU usage < 50%
- No crash loops
- Essential services stable

### After Phase 2
- Load average < 1.5
- Swap available for memory pressure
- nginx routing traffic properly
- System running smoothly for 24+ hours

### After Phase 4
- Load average < 1.0
- All services running reliably
- No crashes for 7+ days
- Ready for production load

---

## Risk Assessment

**What could go wrong?**
1. **Stopping rivet-worker might affect KB ingestion** - ACCEPTABLE: System stability is priority
2. **Killing processes might lose in-progress work** - ACCEPTABLE: Crash loop was losing work anyway
3. **Service restarts might cause brief downtime** - ACCEPTABLE: 5-10 seconds of downtime to fix 24/7 crashes

**Safe to proceed:** YES - Current state is worse than any temporary disruption

---

## Next Steps

Ready to execute fix? Run the commands in order or let me execute them for you.
