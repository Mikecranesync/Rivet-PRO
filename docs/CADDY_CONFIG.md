# Caddy Configuration for Atlas CMMS

**Last Updated:** January 18, 2026
**VPS:** 72.60.175.144
**Production URL:** https://cmms.maintnpc.com

## Critical Configuration Notes

### 1. API Endpoint Routing

Atlas CMMS (GrashJS) uses **direct API paths** (not under `/api/`). All these paths must be routed to the Java backend (port 8080):

```
/auth/*                    - Authentication endpoints
/companies/*               - Company data
/work-orders/*             - Work orders
/locations/*               - Locations
/assets/*                  - Assets/Equipment
/users/*                   - User management
/teams/*                   - Teams
/parts/*                   - Parts inventory
/meters/*                  - Meter readings
/preventive-maintenances/* - PM schedules
/requests/*                - Work requests
/files/*                   - File uploads
/notifications/*           - Notifications
/categories/*              - Categories
/vendors/*                 - Vendors
/customers/*               - Customers
```

### 2. Use `handle` NOT `handle_path`

**IMPORTANT:** Use `handle` to preserve the full path when proxying:

```caddy
# CORRECT - preserves /auth/signin path
handle /auth/* {
    reverse_proxy localhost:8080
}

# WRONG - strips /auth/ prefix, sends just /signin
handle_path /auth/* {
    reverse_proxy localhost:8080
}
```

### 3. Order Matters

API routes must come BEFORE the frontend catch-all:

```caddy
# 1. Backend API routes (specific paths first)
handle /auth/* {
    reverse_proxy localhost:8080
}
handle /companies/* {
    reverse_proxy localhost:8080
}
# ... other API routes ...

# 2. Frontend catch-all (LAST)
handle {
    reverse_proxy localhost:3000
}
```

## Complete Caddyfile for cmms.maintnpc.com

```caddy
cmms.maintnpc.com {
    # Backend API endpoints - ALL routes that need to go to Java backend
    handle /api/* {
        reverse_proxy localhost:8080
    }
    handle /auth/* {
        reverse_proxy localhost:8080
    }
    handle /companies/* {
        reverse_proxy localhost:8080
    }
    handle /work-orders/* {
        reverse_proxy localhost:8080
    }
    handle /locations/* {
        reverse_proxy localhost:8080
    }
    handle /assets/* {
        reverse_proxy localhost:8080
    }
    handle /users/* {
        reverse_proxy localhost:8080
    }
    handle /teams/* {
        reverse_proxy localhost:8080
    }
    handle /parts/* {
        reverse_proxy localhost:8080
    }
    handle /meters/* {
        reverse_proxy localhost:8080
    }
    handle /preventive-maintenances/* {
        reverse_proxy localhost:8080
    }
    handle /requests/* {
        reverse_proxy localhost:8080
    }
    handle /files/* {
        reverse_proxy localhost:8080
    }
    handle /notifications/* {
        reverse_proxy localhost:8080
    }
    handle /categories/* {
        reverse_proxy localhost:8080
    }
    handle /vendors/* {
        reverse_proxy localhost:8080
    }
    handle /customers/* {
        reverse_proxy localhost:8080
    }

    # Frontend (React app) - catch-all LAST
    handle {
        reverse_proxy localhost:3000
    }

    # WebSocket support
    @websockets {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    handle @websockets {
        reverse_proxy localhost:3000
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options nosniff
        X-Frame-Options SAMEORIGIN
        X-XSS-Protection "1; mode=block"
    }

    encode gzip zstd
}
```

## Deployment Commands

```bash
# SSH to VPS
ssh root@72.60.175.144

# Edit Caddyfile
nano /etc/caddy/Caddyfile

# Validate config
caddy validate --config /etc/caddy/Caddyfile

# Reload Caddy
systemctl reload caddy

# Check status
systemctl status caddy
```

## Troubleshooting

### API returning HTML instead of JSON
- **Cause:** API route not configured in Caddy, falls through to frontend
- **Fix:** Add the missing route to Caddyfile

### Login returns 403
- **Cause:** Using `handle_path` instead of `handle` (strips path prefix)
- **Fix:** Change `handle_path /auth/*` to `handle /auth/*`

### Test API routing
```bash
# Should return JSON
curl -s https://cmms.maintnpc.com/auth/signin -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test","type":"CLIENT"}'

# Should return JSON (with valid token)
curl -s https://cmms.maintnpc.com/companies/46 \
  -H "Authorization: Bearer <token>"
```
