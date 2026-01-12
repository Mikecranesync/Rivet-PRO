# Official Ralph Wiggum Plugin Setup

## What is Ralph Wiggum?

Ralph Wiggum is the official Anthropic plugin for Claude Code that enables autonomous development loops. It allows Claude to work iteratively on tasks until a completion promise is met.

**Official GitHub:** https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum

## Installation

### Prerequisites
- Claude Code CLI installed
- Running in a git repository

### Install Command
```bash
/plugin install ralph-loop@claude-plugins-official
```

### Verify Installation
```bash
/plugin list
```

You should see `ralph-loop@claude-plugins-official` in the list.

## Basic Usage

```bash
/ralph-loop "task description" --completion-promise "success criteria" --max-iterations 10
```

### Example
```bash
/ralph-loop "Create a hello world function" --completion-promise "test passes" --max-iterations 5
```

## Cost Control

Ralph Wiggum will iterate autonomously until the completion promise is met or max iterations is reached. **Always set limits** to control costs:

```bash
--max-iterations 10      # Prevent runaway loops (REQUIRED)
--timeout 3600           # Max runtime in seconds (1 hour)
--model claude-3-5-sonnet  # Model to use (default)
--temperature 0.7        # Balance creativity vs consistency
```

### Recommended Limits

**Quick tasks (3-5 iterations):**
```bash
--max-iterations 5 --timeout 600
```

**Medium tasks (5-10 iterations):**
```bash
--max-iterations 10 --timeout 1800
```

**Complex tasks (10-20 iterations):**
```bash
--max-iterations 20 --timeout 3600
```

## Quick Start

1. **Install the plugin:**
   ```bash
   /plugin install ralph-loop@claude-plugins-official
   ```

2. **Run a simple test:**
   ```bash
   /ralph-loop "Create a file called test.txt with 'Hello Ralph'" --completion-promise "file created" --max-iterations 2
   ```

3. **Check the result:**
   ```bash
   cat test.txt
   ```

## Rivet Pro Usage

See [examples.md](./examples.md) for common Rivet Pro tasks.

Use [prd_template.md](./prd_template.md) to plan features.

Use the wrapper script for easier execution:
```bash
./run-ralph.sh "task description" "completion promise" 10
```

## Comparison with Custom scripts/ralph/

See [COMPARISON.md](./COMPARISON.md) for a detailed comparison between the custom Ralph system and the official plugin.

## Documentation

- **Examples:** [examples.md](./examples.md)
- **PRD Template:** [prd_template.md](./prd_template.md)
- **Comparison:** [COMPARISON.md](./COMPARISON.md)
- **Installation Guide:** [INSTALLATION_GUIDE.md](./INSTALLATION_GUIDE.md)

## Support

- Official docs: https://github.com/anthropics/claude-code/blob/main/plugins/README.md
- Plugin repository: https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum
- Blog post: https://paddo.dev/blog/ralph-wiggum-autonomous-loops/
