---
id: task-25.10
title: 'SME-CHAT-010: Integration test for full chat flow'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - testing
  - integration-tests
dependencies:
  - task-25.5
  - task-25.6
  - task-25.7
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create integration test that exercises the full SME chat flow from Telegram to response.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] tests/integration/test_sme_chat_flow.py with real DB connection
- [ ] Test: /chat siemens -> ask question -> verify Hans personality in response
- [ ] Test: multi-turn conversation preserves context
- [ ] Test: RAG atoms are retrieved and formatted in context
- [ ] Test: safety warnings extracted correctly
- [ ] Test: session closes on /endchat
- [ ] Can run with: uv run pytest tests/integration/test_sme_chat_flow.py -v

## Test Scenarios

1. Start session with /chat siemens
2. Ask: "What causes F0002 fault on S7-1200?"
3. Verify Hans personality in response
4. Ask follow-up to test context memory
5. /endchat to close
6. Verify session marked closed in DB

## Files

- `tests/integration/test_sme_chat_flow.py`
