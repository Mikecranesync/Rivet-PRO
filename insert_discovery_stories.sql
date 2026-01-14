-- Insert three discovery stories for Ralph to execute
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status, status_emoji) VALUES

(1, 'ORG-001', 'Create Project Status Snapshot',
'Create a single PROJECT_STATUS.md file that captures the current state of RIVET Pro. Read through the codebase and document what exists, what works, and what is incomplete. This becomes the source of truth for where the project stands today.',
'[
  "PROJECT_STATUS.md created in project root",
  "Section: What Works - list features that are functional",
  "Section: What Is Broken or Incomplete - list anything half-done with TODOs or NotImplementedError",
  "Section: Key Files - list the 5-10 most important files and what each does",
  "Section: Tech Stack - list languages, frameworks, databases, APIs used",
  "Section: Next Steps - suggest 3 high-priority things to build or fix",
  "Committed to git with message docs: project status snapshot"
]'::jsonb,
1, 'todo', '⬜'),

(1, 'ORG-002', 'Map All n8n Workflow Connections',
'Document every n8n workflow that exists for RIVET Pro. For each workflow, note its ID, name, trigger type, and what it does. This creates a map of the automation layer.',
'[
  "N8N_WORKFLOWS.md created in docs folder",
  "Lists each workflow by name and ID",
  "Shows trigger type for each (webhook, schedule, manual)",
  "One sentence description of what each workflow does",
  "Notes which workflows call other workflows",
  "Identifies the main Photo Bot workflow (7LMKcMmldZsu1l6g)",
  "Committed to git"
]'::jsonb,
2, 'todo', '⬜'),

(1, 'ORG-003', 'Create Quick Reference Card',
'Create a single-page QUICK_REFERENCE.md that a developer can read in 2 minutes to understand how to work on this project. Include URLs, credentials locations, and common commands.',
'[
  "QUICK_REFERENCE.md created in project root",
  "Section: URLs - VPS IP, n8n URL, Telegram bot name",
  "Section: Credentials - where env files live, what keys are needed (do NOT include actual secrets)",
  "Section: Common Commands - how to start services, run tests, trigger workflows",
  "Section: Folder Structure - one-liner for each top-level folder",
  "Fits on one printed page - no fluff",
  "Committed to git"
]'::jsonb,
3, 'todo', '⬜');
