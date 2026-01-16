---
id: task-25.2
title: 'SME-CHAT-002: Pydantic models for SME chat'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - models
  - pydantic
dependencies:
  - task-25.1
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create rivet/models/sme_chat.py with Pydantic models for chat sessions, messages, and responses.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] SMEChatSession model with session_id, telegram_chat_id, sme_vendor, status, equipment_context
- [ ] SMEChatMessage model with message_id, session_id, role, content, confidence, rag_atoms_used
- [ ] SMEChatResponse model with response, confidence, sources list, safety_warnings list, cost_usd
- [ ] All models have proper type hints and validation
- [ ] Export from rivet/models/__init__.py

## Files

- `rivet/models/sme_chat.py`
- `rivet/models/__init__.py` (update)
