---
id: task-25.8
title: 'SME-CHAT-008: Confidence-based routing in orchestrator'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - orchestrator
  - routing
dependencies:
  - task-25.4
  - task-25.5
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement confidence-based routing: high (>0.85) direct KB, medium (0.7-0.85) SME synthesis, low (<0.7) clarifying questions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] route_chat_query function calculates RAG confidence from top result similarity
- [ ] High confidence (>=0.85): format_direct_kb_answer with SME voice styling
- [ ] Medium confidence (0.70-0.85): generate_sme_synthesis from RAG context
- [ ] Low confidence (<0.70): generate_clarifying_questions to ask user for more info
- [ ] Confidence calculation: (top_similarity * 0.6) + (avg_top3_similarity * 0.4)
- [ ] Integrate with SMEChatService.chat flow

## Routing Logic

| Confidence | Route | Action |
|------------|-------|--------|
| ≥0.85 | DIRECT | Format KB answer with SME voice |
| 0.70-0.85 | SYNTHESIZE | SME synthesizes from RAG context |
| <0.70 | CLARIFY | SME asks clarifying questions |

## Files

- `rivet/services/sme_chat_service.py` (update)
