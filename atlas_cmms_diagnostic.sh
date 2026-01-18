#!/bin/bash
# =============================================================================
# ATLAS CMMS Authentication Diagnostic Script
# =============================================================================
# Purpose: Automatically diagnose login/authentication issues in Atlas CMMS
# Target: VPS deployment at 72.60.175.144
#         Frontend: https://cmms.maintnpc.com (or http://72.60.175.144:3000)
#         Java API: https://cmms.maintnpc.com/auth/* (proxied to localhost:8080)
# NOTE: Atlas CMMS uses /auth/signin NOT /api/auth/signin
#       Login requires "type" field: "SUPER_ADMIN" or "CLIENT" based on user role
# Usage: bash atlas_cmms_diagnostic.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0
WARN=0

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    ((PASS++))
}

check_fail() {
    echo -e "  ${RED}✗${NC} $1"
    ((FAIL++))
}

check_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    ((WARN++))
}

check_info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

# =============================================================================
# PHASE 1: Environment Variables
# =============================================================================
print_header "PHASE 1: Environment Variables"

# Check if .env file exists
if [ -f ".env" ]; then
    check_pass ".env file exists"

    # Check critical variables
    if grep -q "^JWT_SECRET=" .env 2>/dev/null; then
        JWT_SECRET=$(grep "^JWT_SECRET=" .env | cut -d'=' -f2)
        if [ ${#JWT_SECRET} -ge 32 ]; then
            check_pass "JWT_SECRET is set (${#JWT_SECRET} characters)"
        else
            check_warn "JWT_SECRET is short (${#JWT_SECRET} chars) - should be 32+"
        fi
    else
        check_fail "JWT_SECRET not found in .env"
    fi

    if grep -q "^MONGO_URI\|^MONGODB_URI\|^DATABASE_URL" .env 2>/dev/null; then
        check_pass "Database connection string found"
    else
        check_fail "Database connection string not found"
    fi

    if grep -q "^CORS\|^ALLOWED_ORIGINS\|^FRONTEND_URL" .env 2>/dev/null; then
        check_pass "CORS/Frontend URL configuration found"
    else
        check_warn "No explicit CORS configuration found"
    fi

    if grep -q "^PORT\|^BACKEND_PORT\|^API_PORT" .env 2>/dev/null; then
        check_pass "Backend port configured"
    else
        check_info "Using default backend port"
    fi
else
    check_fail ".env file not found"
fi

# =============================================================================
# PHASE 2: Docker Configuration
# =============================================================================
print_header "PHASE 2: Docker Configuration"

# Check docker-compose.yml
if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then
    check_pass "docker-compose.yml exists"

    COMPOSE_FILE=$(ls docker-compose.y*ml 2>/dev/null | head -1)

    # Check for required services
    if grep -q "frontend\|web\|client" "$COMPOSE_FILE" 2>/dev/null; then
        check_pass "Frontend service defined"
    else
        check_warn "No frontend service found in docker-compose"
    fi

    if grep -q "backend\|api\|server" "$COMPOSE_FILE" 2>/dev/null; then
        check_pass "Backend service defined"
    else
        check_fail "No backend service found in docker-compose"
    fi

    if grep -q "mongo\|postgres\|mysql\|database\|db" "$COMPOSE_FILE" 2>/dev/null; then
        check_pass "Database service defined"
    else
        check_warn "No database service found (may be external)"
    fi

    # Check for network configuration
    if grep -q "networks:" "$COMPOSE_FILE" 2>/dev/null; then
        check_pass "Docker networks configured"
    else
        check_warn "No explicit network configuration"
    fi

    # Check for volume mounts
    if grep -q "volumes:" "$COMPOSE_FILE" 2>/dev/null; then
        check_pass "Volume mounts configured"
    else
        check_info "No volume mounts (data may not persist)"
    fi
else
    check_fail "docker-compose.yml not found"
fi

# =============================================================================
# PHASE 3: Docker Container Status
# =============================================================================
print_header "PHASE 3: Docker Container Status"

# Check if Docker is running
if command -v docker &> /dev/null; then
    check_pass "Docker is installed"

    if docker info &> /dev/null; then
        check_pass "Docker daemon is running"

        # List running containers
        CONTAINERS=$(docker ps --format "{{.Names}}" 2>/dev/null)

        if [ -n "$CONTAINERS" ]; then
            check_pass "Docker containers are running:"
            echo "$CONTAINERS" | while read container; do
                STATUS=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)
                HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no healthcheck{{end}}' "$container" 2>/dev/null)
                echo -e "      - $container: ${GREEN}$STATUS${NC} (health: $HEALTH)"
            done
        else
            check_fail "No Docker containers running"
        fi

        # Check for recently exited containers
        EXITED=$(docker ps -a --filter "status=exited" --format "{{.Names}}: exited {{.Status}}" 2>/dev/null | head -5)
        if [ -n "$EXITED" ]; then
            check_warn "Recently exited containers:"
            echo "$EXITED" | while read line; do
                echo "      - $line"
            done
        fi
    else
        check_fail "Docker daemon not running"
    fi
else
    check_fail "Docker not installed"
fi

# =============================================================================
# PHASE 4: Network Connectivity
# =============================================================================
print_header "PHASE 4: Network Connectivity"

# Test localhost endpoints
echo "  Testing local endpoints..."

# Frontend (port 3000)
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null | grep -q "200\|301\|302"; then
    check_pass "Frontend (localhost:3000) is responding"
else
    check_fail "Frontend (localhost:3000) not responding"
fi

# Backend - Atlas CMMS uses port 8080 for Java API
# Note: Health check may return 403 (requires auth) but app still works
for PORT in 8080 5000 3001 4000; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/api/health 2>/dev/null || echo "000")
    if [ "$RESPONSE" != "000" ]; then
        if [ "$RESPONSE" = "200" ]; then
            check_pass "Backend health check (localhost:$PORT) returned 200 OK"
        elif [ "$RESPONSE" = "403" ]; then
            check_warn "Backend (localhost:$PORT) returned 403 Forbidden - health endpoint requires auth (app may still work)"
        else
            check_warn "Backend (localhost:$PORT) returned HTTP $RESPONSE"
        fi
        break
    fi
done

# Test Atlas CMMS specific endpoints
# IMPORTANT: Atlas CMMS uses /auth/signin NOT /api/auth/signin
check_info "Testing Atlas CMMS Java API endpoints..."
SIGNIN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/auth/signin 2>/dev/null || echo "000")
if [ "$SIGNIN_RESPONSE" != "000" ]; then
    if [ "$SIGNIN_RESPONSE" = "400" ] || [ "$SIGNIN_RESPONSE" = "401" ] || [ "$SIGNIN_RESPONSE" = "405" ] || [ "$SIGNIN_RESPONSE" = "403" ]; then
        check_pass "Atlas CMMS signin endpoint exists (localhost:8080/auth/signin)"
        check_info "NOTE: 403 is expected for GET/empty POST - login requires email, password, and type fields"
    else
        check_info "Atlas CMMS signin endpoint returned HTTP $SIGNIN_RESPONSE"
    fi
fi

# Test inter-container communication (if Docker)
if command -v docker &> /dev/null && docker info &> /dev/null; then
    BACKEND_CONTAINER=$(docker ps --format "{{.Names}}" | grep -i "backend\|api\|server" | head -1)
    if [ -n "$BACKEND_CONTAINER" ]; then
        check_info "Testing from inside backend container..."
        docker exec "$BACKEND_CONTAINER" curl -s http://localhost:5000/api/health &>/dev/null && \
            check_pass "Backend internal health check works" || \
            check_warn "Backend internal health check failed"
    fi
fi

# =============================================================================
# PHASE 5: Database Connectivity
# =============================================================================
print_header "PHASE 5: Database Connectivity"

# Check MongoDB (if using Mongo)
if command -v mongosh &> /dev/null || command -v mongo &> /dev/null; then
    check_info "MongoDB client available"

    # Try to connect
    MONGO_CMD="mongosh"
    command -v mongosh &> /dev/null || MONGO_CMD="mongo"

    if $MONGO_CMD --eval "db.adminCommand('ping')" &>/dev/null; then
        check_pass "MongoDB is accessible"
    else
        check_warn "MongoDB connection failed (may need auth)"
    fi
elif docker ps --format "{{.Names}}" | grep -qi "mongo"; then
    MONGO_CONTAINER=$(docker ps --format "{{.Names}}" | grep -i "mongo" | head -1)
    check_info "MongoDB running in container: $MONGO_CONTAINER"

    if docker exec "$MONGO_CONTAINER" mongosh --eval "db.adminCommand('ping')" &>/dev/null; then
        check_pass "MongoDB container is healthy"
    else
        check_warn "MongoDB container health check failed"
    fi
fi

# Check PostgreSQL (if using Postgres)
if docker ps --format "{{.Names}}" | grep -qi "postgres"; then
    POSTGRES_CONTAINER=$(docker ps --format "{{.Names}}" | grep -i "postgres" | head -1)
    check_info "PostgreSQL running in container: $POSTGRES_CONTAINER"

    if docker exec "$POSTGRES_CONTAINER" pg_isready &>/dev/null; then
        check_pass "PostgreSQL is ready"
    else
        check_warn "PostgreSQL not ready"
    fi
fi

# =============================================================================
# PHASE 6: Application Logs
# =============================================================================
print_header "PHASE 6: Recent Error Logs"

# Check Docker logs for errors
if command -v docker &> /dev/null && docker info &> /dev/null; then
    BACKEND_CONTAINER=$(docker ps --format "{{.Names}}" | grep -i "backend\|api\|server" | head -1)

    if [ -n "$BACKEND_CONTAINER" ]; then
        check_info "Checking last 50 lines of backend logs..."

        ERRORS=$(docker logs "$BACKEND_CONTAINER" --tail 50 2>&1 | grep -i "error\|exception\|fail\|unauthorized\|cors\|jwt" | tail -10)

        if [ -n "$ERRORS" ]; then
            check_warn "Recent errors found in backend logs:"
            echo "$ERRORS" | while read line; do
                echo -e "      ${RED}$line${NC}"
            done
        else
            check_pass "No recent errors in backend logs"
        fi
    fi

    FRONTEND_CONTAINER=$(docker ps --format "{{.Names}}" | grep -i "frontend\|web\|client" | head -1)

    if [ -n "$FRONTEND_CONTAINER" ]; then
        ERRORS=$(docker logs "$FRONTEND_CONTAINER" --tail 50 2>&1 | grep -i "error\|fail\|cors\|unauthorized" | tail -5)

        if [ -n "$ERRORS" ]; then
            check_warn "Recent errors found in frontend logs:"
            echo "$ERRORS" | while read line; do
                echo -e "      ${RED}$line${NC}"
            done
        else
            check_pass "No recent errors in frontend logs"
        fi
    fi
fi

# =============================================================================
# PHASE 7: CORS Headers
# =============================================================================
print_header "PHASE 7: CORS Headers"

# Test CORS preflight request
for PORT in 5000 8080 3001 4000; do
    RESPONSE=$(curl -s -I -X OPTIONS http://localhost:$PORT/api/auth/login \
        -H "Origin: http://localhost:3000" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" 2>/dev/null)

    if [ -n "$RESPONSE" ]; then
        check_info "Testing CORS on port $PORT..."

        if echo "$RESPONSE" | grep -qi "access-control-allow-origin"; then
            ORIGIN=$(echo "$RESPONSE" | grep -i "access-control-allow-origin" | cut -d':' -f2 | tr -d ' \r')
            check_pass "CORS Allow-Origin header present: $ORIGIN"
        else
            check_fail "CORS Allow-Origin header MISSING"
        fi

        if echo "$RESPONSE" | grep -qi "access-control-allow-credentials"; then
            check_pass "CORS Allow-Credentials header present"
        else
            check_warn "CORS Allow-Credentials header missing"
        fi

        if echo "$RESPONSE" | grep -qi "access-control-allow-methods"; then
            check_pass "CORS Allow-Methods header present"
        else
            check_warn "CORS Allow-Methods header missing"
        fi

        break
    fi
done

# =============================================================================
# PHASE 8: Login Test
# =============================================================================
print_header "PHASE 8: Login Endpoint Test"

# Try to hit the login endpoint
# IMPORTANT: Atlas CMMS uses /auth/signin and requires "type" field
for PORT in 8080 5000 3001 4000; do
    LOGIN_RESPONSE=$(curl -s -X POST http://localhost:$PORT/auth/signin \
        -H "Content-Type: application/json" \
        -d '{"email":"test@test.com","password":"test","type":"CLIENT"}' 2>/dev/null)

    if [ -n "$LOGIN_RESPONSE" ]; then
        check_info "Login endpoint responding on port $PORT"

        if echo "$LOGIN_RESPONSE" | grep -qi "token\|jwt\|access"; then
            check_pass "Login endpoint returns token structure"
        elif echo "$LOGIN_RESPONSE" | grep -qi "invalid\|incorrect\|wrong\|unauthorized"; then
            check_pass "Login endpoint validates credentials (returned auth error)"
        elif echo "$LOGIN_RESPONSE" | grep -qi "error\|fail"; then
            check_warn "Login endpoint returned error: $(echo $LOGIN_RESPONSE | head -c 100)"
        else
            check_info "Login response: $(echo $LOGIN_RESPONSE | head -c 100)"
        fi
        break
    fi
done

# =============================================================================
# SUMMARY
# =============================================================================
print_header "DIAGNOSTIC SUMMARY"

echo ""
echo -e "  ${GREEN}Passed:${NC}  $PASS"
echo -e "  ${RED}Failed:${NC}  $FAIL"
echo -e "  ${YELLOW}Warnings:${NC} $WARN"
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ACTION REQUIRED: $FAIL critical issues found${NC}"
    echo -e "${RED}  Review atlas_cmms_auth_fixes.md for solutions${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
elif [ $WARN -gt 0 ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}  REVIEW RECOMMENDED: $WARN warnings found${NC}"
    echo -e "${YELLOW}  Check atlas_cmms_login_investigation.md for details${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ALL CHECKS PASSED${NC}"
    echo -e "${GREEN}  If login still fails, check browser console for client-side errors${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
fi
