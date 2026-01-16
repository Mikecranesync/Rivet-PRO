---
id: task-25.5
title: 'SME-CHAT-005: SME chat service core'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - service
  - orchestration
dependencies:
  - task-25.1
  - task-25.2
  - task-25.3
  - task-25.4
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create rivet/services/sme_chat_service.py that orchestrates chat sessions with personality, RAG, and LLM.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] SMEChatService class with start_session, chat, close_session methods
- [ ] start_session creates DB session, adds system message with personality
- [ ] chat method: load session, get history, RAG context, build prompt, generate LLM response
- [ ] Prompt combines personality voice + RAG context + conversation history + equipment context
- [ ] Extract safety warnings from response text
- [ ] Calculate confidence based on RAG hit quality
- [ ] Store assistant message with rag_atoms_used metadata
- [ ] Uses existing LLMRouter.generate with ModelCapability.MODERATE

## Chat Flow

1. Load session context + personality
2. Store user message
3. Get conversation history (last 10)
4. RAG: Retrieve relevant knowledge atoms
5. Build prompt: personality + RAG + history + equipment
6. Generate LLM response
7. Extract safety warnings
8. Calculate confidence from RAG quality
9. Store assistant message with metadata
10. Return formatted response

## Files

- `rivet/services/sme_chat_service.py`
