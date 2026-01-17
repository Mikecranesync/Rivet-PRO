---
id: task-25.9
title: 'SME-CHAT-009: Unit tests for SME chat'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - testing
  - unit-tests
dependencies:
  - task-25.5
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create comprehensive unit tests for SME chat service and personalities.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] tests/unit/test_sme_chat_service.py with mocked DB and LLM
- [ ] Test start_session creates session and adds system message
- [ ] Test chat returns properly formatted response with all fields
- [ ] Test close_session updates status
- [ ] tests/unit/test_sme_personalities.py verifies all 7 personalities load
- [ ] Test personality prompt generation includes voice elements
- [ ] All tests pass with pytest

## Test Commands

```bash
uv run pytest tests/unit/test_sme_chat_service.py -v
uv run pytest tests/unit/test_sme_personalities.py -v
```

## Files

- `tests/unit/test_sme_chat_service.py`
- `tests/unit/test_sme_personalities.py`
