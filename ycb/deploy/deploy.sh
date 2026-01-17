#!/bin/bash
# YCB VPS Deployment Script
# Usage: ./deploy.sh [start|stop|restart|status|logs|update]

set -e

# Configuration
DEPLOY_DIR="/opt/ycb"
REPO_URL="https://github.com/Mikecranesync/Rivet-PRO.git"
BRANCH="feature/youtube-channel-builder"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root or with sudo"
        exit 1
    fi
}

# Install prerequisites
install_prereqs() {
    log_info "Installing prerequisites..."
    apt-get update
    apt-get install -y docker.io docker-compose git curl
    systemctl enable docker
    systemctl start docker
}

# Clone/update repository
update_repo() {
    log_info "Updating repository..."
    if [ -d "$DEPLOY_DIR" ]; then
        cd "$DEPLOY_DIR"
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    else
        git clone -b "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
        cd "$DEPLOY_DIR"
    fi
}

# Setup environment
setup_env() {
    log_info "Setting up environment..."
    if [ ! -f "$DEPLOY_DIR/.env" ]; then
        log_warn ".env file not found!"
        log_info "Creating template .env file..."
        cat > "$DEPLOY_DIR/.env" << 'EOF'
# YCB Environment Configuration
# Fill in your API keys

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_API_KEY=your-api-key

# OpenAI
OPENAI_API_KEY=sk-your-key

# YouTube (optional for uploads)
YOUTUBE_CLIENT_ID=your-client-id
YOUTUBE_CLIENT_SECRET=your-secret
YOUTUBE_CHANNEL_ID=your-channel-id

# ElevenLabs (optional for voice)
ELEVENLABS_API_KEY=your-key
ELEVENLABS_VOICE_ID=your-voice-id

# YCB Settings
YCB_OUTPUT_DIR=/app/ycb_output
YCB_MAX_VIDEOS_PER_DAY=5
YCB_DEFAULT_PRIVACY=private
YCB_AUTO_PUBLISH=false
YCB_LOG_LEVEL=INFO
EOF
        log_warn "Please edit $DEPLOY_DIR/.env with your API keys"
        exit 1
    fi
}

# Build containers
build() {
    log_info "Building Docker containers..."
    cd "$DEPLOY_DIR/ycb/deploy"
    docker-compose build --no-cache
}

# Start services
start() {
    log_info "Starting YCB services..."
    cd "$DEPLOY_DIR/ycb/deploy"
    docker-compose up -d
    log_info "Services started!"
    docker-compose ps
}

# Stop services
stop() {
    log_info "Stopping YCB services..."
    cd "$DEPLOY_DIR/ycb/deploy"
    docker-compose down
    log_info "Services stopped."
}

# Restart services
restart() {
    stop
    start
}

# Show status
status() {
    log_info "YCB Service Status:"
    cd "$DEPLOY_DIR/ycb/deploy"
    docker-compose ps
    echo ""
    log_info "Recent logs:"
    docker-compose logs --tail=20
}

# Show logs
logs() {
    cd "$DEPLOY_DIR/ycb/deploy"
    docker-compose logs -f
}

# Full update
update() {
    log_info "Performing full update..."
    stop
    update_repo
    build
    start
    log_info "Update complete!"
}

# Initial setup
setup() {
    check_root
    install_prereqs
    update_repo
    setup_env
    build
    start
    log_info "YCB deployment complete!"
    log_info "Run 'deploy.sh logs' to view logs"
}

# Run database migrations
migrate() {
    log_info "Running database migrations..."
    cd "$DEPLOY_DIR"

    # Check if psql is available
    if ! command -v psql &> /dev/null; then
        log_info "Installing PostgreSQL client..."
        apt-get install -y postgresql-client
    fi

    # Run schema
    if [ -f "$DEPLOY_DIR/ycb/sql/schema.sql" ]; then
        source "$DEPLOY_DIR/.env"
        log_info "Applying YCB schema to database..."
        # Extract connection details from SUPABASE_URL or DATABASE_URL
        # This is a simplified example - adjust based on your .env format
        log_warn "Please run the schema manually in Supabase SQL Editor:"
        log_info "  $DEPLOY_DIR/ycb/sql/schema.sql"
    fi
}

# Main
case "${1:-}" in
    setup)
        setup
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    update)
        update
        ;;
    build)
        build
        ;;
    migrate)
        migrate
        ;;
    *)
        echo "YCB Deployment Script"
        echo ""
        echo "Usage: $0 {setup|start|stop|restart|status|logs|update|build|migrate}"
        echo ""
        echo "Commands:"
        echo "  setup    - Initial setup (install prereqs, clone repo, build, start)"
        echo "  start    - Start services"
        echo "  stop     - Stop services"
        echo "  restart  - Restart services"
        echo "  status   - Show service status and recent logs"
        echo "  logs     - Follow service logs"
        echo "  update   - Pull latest code and restart"
        echo "  build    - Rebuild Docker containers"
        echo "  migrate  - Run database migrations"
        exit 1
        ;;
esac
