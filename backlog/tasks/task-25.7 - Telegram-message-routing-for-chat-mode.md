---
id: task-25.7
title: 'SME-CHAT-007: Telegram message routing for chat mode'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - telegram
  - routing
dependencies:
  - task-25.5
  - task-25.6
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Update message_handler in telegram.py to route messages to SME chat when session is active.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] Check context.user_data.get('sme_chat_active') at start of message_handler
- [ ] If active, call handle_sme_chat_message instead of troubleshoot workflow
- [ ] handle_sme_chat_message loads session, calls SMEChatService.chat, formats response
- [ ] Response includes SME name badge, answer, safety warnings, sources, confidence indicator
- [ ] Typing indicator shown while processing
- [ ] Error handling with suggestion to /endchat if persistent failures

## Response Format

```
👨‍🔧 Hans (Siemens Expert)

[Response with personality voice]

⚠️ Safety:
• High voltage hazard

📚 Sources:
• Siemens S7-1200 Manual

🟢 High confidence
```

## Files

- `rivet/integrations/telegram.py` (update)
