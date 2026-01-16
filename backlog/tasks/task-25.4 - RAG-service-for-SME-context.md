---
id: task-25.4
title: 'SME-CHAT-004: RAG service for SME context'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - rag
  - embeddings
dependencies:
  - task-25.1
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create rivet/services/sme_rag_service.py that retrieves relevant knowledge atoms filtered by manufacturer.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] SMERagService class with get_relevant_context async method
- [ ] Accepts query, manufacturer, conversation_history, equipment_context, limit params
- [ ] Builds enhanced query from conversation context for better embedding
- [ ] Uses existing EmbeddingService for query embedding generation
- [ ] Uses existing KnowledgeService.vector_search with manufacturer filter
- [ ] Returns tuple of (atoms_list, formatted_context_string)
- [ ] Formats atoms as structured context for LLM prompt

## Flow

```
Query → Enhance with conversation context → Embed →
Vector search (filtered by manufacturer) → Top 5 atoms →
Format context → Return for LLM prompt
```

## Files

- `rivet/services/sme_rag_service.py`
