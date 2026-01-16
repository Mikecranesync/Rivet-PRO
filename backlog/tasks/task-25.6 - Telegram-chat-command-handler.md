---
id: task-25.6
title: 'SME-CHAT-006: Telegram /chat command handler'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - telegram
  - commands
dependencies:
  - task-25.3
  - task-25.5
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add /chat and /endchat command handlers to rivet/integrations/telegram.py for starting SME chat sessions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] /chat [vendor] command starts SME session - vendor optional, auto-detects from recent equipment
- [ ] /endchat command closes active session and clears user_data
- [ ] Show vendor picker if no vendor specified and no recent equipment
- [ ] Store sme_session_id and sme_chat_active in context.user_data
- [ ] Send SME greeting with personality name and tagline
- [ ] Register both commands in setup_bot() with CommandHandler

## Usage

```
/chat siemens    - Start chat with Hans (Siemens expert)
/chat rockwell   - Start chat with Mike (Rockwell expert)
/chat            - Auto-detect or show picker
/endchat         - Close active session
```

## Files

- `rivet/integrations/telegram.py` (update)
