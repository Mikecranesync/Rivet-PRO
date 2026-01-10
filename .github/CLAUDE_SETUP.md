# Claude Code GitHub Actions Setup

This repository is configured to use Claude Code in pull requests and issues via GitHub Actions.

## How It Works

When you mention `@claude` in:
- PR comments
- PR review comments
- Issue comments or descriptions

Claude Code will automatically:
1. Read the PR diff and full context
2. Understand your request
3. Make code changes directly
4. Push commits to the PR branch

## Setup Instructions

### 1. Add Anthropic API Key

1. Get an API key from: https://console.anthropic.com/
2. Go to your repo: **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Name: `ANTHROPIC_API_KEY`
5. Value: Your Anthropic API key
6. Click **Add secret**

### 2. Verify Workflow Permissions

The workflow needs these permissions (already configured in `claude.yml`):
- ✅ `contents: write` - Push commits to PR branches
- ✅ `pull-requests: write` - Comment on PRs
- ✅ `issues: write` - Comment on issues

These are granted via the `GITHUB_TOKEN` automatically.

## Usage Examples

### Example 1: Fix a Bug

In a PR comment:
```
@claude there's a bug in the manual hunter workflow - it stops at the cache check.
Can you update the Extract Webhook Data node to handle both field name conventions
(manufacturer/make, model_number/model)?
```

Claude will:
- Read the PR diff
- Understand the workflow structure
- Make the necessary changes
- Push a commit with the fix

### Example 2: Add Tests

In a PR review comment (on specific code):
```
@claude add unit tests for this function. Cover edge cases like empty input,
null values, and invalid data formats.
```

### Example 3: Refactor Code

In an issue:
```
@claude refactor the n8n workflow validation logic to use a shared utility function.
The validation code is duplicated across 3 workflows.
```

### Example 4: Documentation

```
@claude add JSDoc comments to all functions in this file. Include parameter types,
return types, and usage examples.
```

### Example 5: Code Review

```
@claude review this PR and suggest improvements for:
- Performance optimization
- Error handling
- Code readability
```

## What Claude Can Do

✅ **Code Changes:**
- Fix bugs
- Add features
- Refactor code
- Update dependencies
- Improve performance

✅ **Documentation:**
- Add comments
- Write README files
- Create API docs
- Update changelog

✅ **Testing:**
- Write unit tests
- Add integration tests
- Create test fixtures

✅ **Code Review:**
- Identify issues
- Suggest improvements
- Check best practices

## Workflow Triggers

The workflow runs when:

```yaml
on:
  issue_comment:
    types: [created]           # When someone comments on an issue/PR
  pull_request_review_comment:
    types: [created]           # When someone comments on a PR review
  issues:
    types: [opened, edited]    # When an issue is created or edited
```

Only triggers if the comment/issue contains `@claude`.

## Configuration

Current configuration (`.github/workflows/claude.yml`):

```yaml
model: claude-sonnet-4-5-20250929  # Sonnet 4.5 (recommended for code)
max-tokens: 8192                    # Maximum response length
runs-on: ubuntu-latest              # Execution environment
```

### Alternative Models

You can change the model in the workflow file:

```yaml
model: claude-opus-4-5-20251101     # Opus 4.5 (more powerful, slower)
model: claude-sonnet-4-5-20250929   # Sonnet 4.5 (balanced, recommended)
model: claude-haiku-4-5-20251101    # Haiku 4.5 (faster, simpler tasks)
```

## Troubleshooting

### Claude doesn't respond

**Check:**
1. API key is set correctly in repository secrets
2. Workflow has proper permissions
3. Comment contains `@claude` (case-sensitive)
4. GitHub Actions is enabled for the repository

**View logs:**
- Go to **Actions** tab in GitHub
- Click the failed workflow run
- Check the "Run Claude Code" step

### Permission errors

**Fix:**
1. Go to **Settings → Actions → General**
2. Under "Workflow permissions"
3. Select "Read and write permissions"
4. Check "Allow GitHub Actions to create and approve pull requests"
5. Save

### API rate limits

If you hit rate limits:
- Use a higher-tier API key
- Reduce `max-tokens` in the workflow
- Switch to `claude-haiku` for simpler tasks

## Best Practices

### 1. Be Specific

❌ **Bad:** "@claude fix this"
✅ **Good:** "@claude fix the cache flow issue in Manual Hunter workflow by adding field name normalization in the Extract Webhook Data node"

### 2. Provide Context

```
@claude the LLM Judge workflow is returning zeros. I suspect the parser expects
OpenAI format but we're using Gemini. Can you update the parser to handle both
formats? See ISSUE_2_LLM_JUDGE_RETURNS_ZEROS.md for details.
```

### 3. One Task at a Time

Instead of:
```
@claude fix the bugs, add tests, update docs, and refactor everything
```

Do:
```
@claude fix the Manual Hunter cache flow bug described in issue #1
```

Then in a follow-up comment:
```
@claude now add integration tests for the fixed workflow
```

### 4. Review Changes

Claude pushes commits directly, but you should:
- Review the changes
- Test locally if needed
- Request modifications if something isn't right

### 5. Use in Drafts First

Test Claude's changes in draft PRs before using on production-ready PRs.

## Security

### What Claude Can Access

✅ **Can access:**
- Public repository code
- PR diffs and comments
- Issue descriptions and comments
- Public files in the repository

❌ **Cannot access:**
- Repository secrets (except ANTHROPIC_API_KEY which it needs)
- Private environment variables
- External services without explicit configuration

### API Key Security

⚠️ **Important:**
- Never commit your API key to the repository
- Only add it via GitHub Secrets
- Rotate the key if accidentally exposed
- Use separate keys for different environments

### Rate Limiting

The workflow uses your Anthropic API quota. Monitor usage at:
https://console.anthropic.com/settings/usage

## Advanced Configuration

### Custom Prompts

You can customize the system prompt by modifying the workflow:

```yaml
- name: Run Claude Code
  uses: anthropics/claude-code-action@v1
  with:
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    github-token: ${{ secrets.GITHUB_TOKEN }}
    model: claude-sonnet-4-5-20250929
    system-prompt: |
      You are a senior n8n workflow engineer specializing in the RIVET project.
      Always follow the project's coding standards and test thoroughly.
```

### Restrict to Specific Files

Only trigger on certain file types:

```yaml
if: |
  (contains(github.event.comment.body, '@claude')) &&
  (contains(github.event.pull_request.files, '.json') ||
   contains(github.event.pull_request.files, '.py'))
```

### Multiple Workflows

Create separate workflows for different purposes:

- `.github/workflows/claude-review.yml` - Code review only
- `.github/workflows/claude-fix.yml` - Bug fixes only
- `.github/workflows/claude-docs.yml` - Documentation only

Each with different trigger phrases (`@claude-review`, `@claude-fix`, etc.)

## Cost Estimation

Approximate costs per task (at current Anthropic pricing):

| Task Type | Tokens | Cost (Sonnet 4.5) |
|-----------|--------|-------------------|
| Simple fix | ~2K | $0.006 |
| Add tests | ~5K | $0.015 |
| Refactor | ~8K | $0.024 |
| Full review | ~10K | $0.030 |

*Costs are estimates and may vary based on context size and model used.*

## Support

- **Anthropic Docs:** https://docs.anthropic.com/
- **Claude Code Docs:** https://docs.anthropic.com/claude/docs/claude-code
- **GitHub Actions:** https://docs.github.com/actions

## Examples from This Repo

See PRs #2, #3, and #4 for examples of issues documented with Claude Code:
- PR #2: Manual Hunter cache flow issue
- PR #3: LLM Judge parser issue
- PR #4: Database Health connection issue

You can use `@claude` to help resolve these issues!
