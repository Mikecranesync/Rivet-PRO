---
id: task-25
title: 'PHASE 4: SME Chat with LLM Interaction'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - phase4
  - sme-chat
  - llm
  - orchestrator
dependencies:
  - task-10
parent_task_id: null
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add real LLM chat interaction to SME agents with distinct personalities and RAG-connected answers from product knowledge docs.

Users can start conversational chat sessions with vendor-specific SME agents (Siemens, Rockwell, ABB, Schneider, Mitsubishi, FANUC) via /chat command. Each SME has a distinct personality and voice. Responses are enhanced with RAG-retrieved knowledge atoms filtered by manufacturer.
<!-- SECTION:DESCRIPTION:END -->

## Key Features

- Multi-turn conversational chat with SME agents
- 6 vendor personalities (Hans/Siemens, Mike/Rockwell, Erik/ABB, Pierre/Schneider, Takeshi/Mitsubishi, Ken/FANUC)
- RAG-enhanced responses from knowledge_atoms table
- Confidence-based routing (direct KB / SME synthesis / clarifying questions)
- /chat and /endchat Telegram commands
- Session memory persists across messages

## Ralph Stories

Stories SME-CHAT-001 through SME-CHAT-010 in ralph_stories table.
Run: `psql $DATABASE_URL -f scripts/ralph/insert_sme_chat_stories.sql`

## Subtasks

- task-25.1: Database migration for chat sessions
- task-25.2: Pydantic models for SME chat
- task-25.3: SME personalities configuration
- task-25.4: RAG service for SME context
- task-25.5: SME chat service core
- task-25.6: Telegram /chat command handler
- task-25.7: Telegram message routing for chat mode
- task-25.8: Confidence-based routing in orchestrator
- task-25.9: Unit tests for SME chat
- task-25.10: Integration test for full chat flow
