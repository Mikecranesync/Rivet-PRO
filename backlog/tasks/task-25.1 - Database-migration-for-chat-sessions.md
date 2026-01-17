---
id: task-25.1
title: 'SME-CHAT-001: Database migration for chat sessions'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - database
  - migration
dependencies: []
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create migration 026_sme_chat_sessions.sql with tables for sme_chat_sessions and sme_chat_messages. Include auto-update triggers and session timeout functions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] sme_chat_sessions table with telegram_chat_id, sme_vendor, status, equipment_context JSONB
- [ ] sme_chat_messages table with session_id FK, role, content, confidence, rag_atoms_used UUID array
- [ ] Auto-update last_message_at trigger on message insert
- [ ] close_inactive_sessions() function for 30-min timeout
- [ ] Indexes on telegram_chat_id, session status, and message timestamps

## Files

- `rivet_pro/migrations/026_sme_chat_sessions.sql`
