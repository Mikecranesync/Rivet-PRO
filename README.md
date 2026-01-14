# RIVET Debug Harness

**Agent 3 Deliverable** - Automated testing and monitoring infrastructure for RIVET

## Overview

The RIVET Debug Harness is a production-ready testing framework that monitors and validates RIVET infrastructure health. It provides:

- **Health Checks** - Quick infrastructure status verification  
- **Real-Time Dashboard** - Continuous monitoring with live updates
- **Automated Test Suite** - Comprehensive tests with retry logic
- **Test Fixtures** - Validation helpers and mock data

## Quick Start

### 1. Installation

\`\`\`bash
# Navigate to the repository
cd rivet-agent3-harness

# Install dependencies
pip install -r harness/requirements.txt
\`\`\`

### 2. Configuration

Set environment variables:

\`\`\`bash
export NEON_DATABASE_URL="postgresql://user:pass@host/rivet_pro"
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TEST_CHAT_ID="your_telegram_chat_id"
\`\`\`

### 3. Run Health Check

\`\`\`bash
python -m harness.health_check
\`\`\`

## Components

- \`health_check.py\` - Infrastructure health checks
- \`test_dashboard.py\` - Real-time monitoring
- \`test_suite.py\` - Automated testing with retry logic
- \`test_fixtures.py\` - Validation and helpers
- \`n8n_test_client.py\` - MCP test tools

See AGENT3_COMPLETE.md for complete documentation.

## Contributing

We follow trunk-based development with short-lived feature branches and use feature flags for safe rollouts. Before contributing:

- Read the [Branching & Merge Workflow Guide](docs/BRANCHING_GUIDE.md)
- Understand our [Feature Flag Lifecycle](docs/FEATURE_FLAGS.md)
- Follow the PR template when creating pull requests

All changes to `main` require PR approval and passing CI checks.
