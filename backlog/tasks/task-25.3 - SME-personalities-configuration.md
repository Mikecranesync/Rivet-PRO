---
id: task-25.3
title: 'SME-CHAT-003: SME personalities configuration'
status: To Do
assignee: []
created_date: '2026-01-16'
labels:
  - sme-chat
  - personalities
  - prompts
dependencies: []
parent_task_id: task-25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create rivet/prompts/sme/personalities.py with distinct voice/personality for 6 vendor SMEs plus generic.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

- [ ] SME_PERSONALITIES dict with siemens, rockwell, abb, schneider, mitsubishi, fanuc, generic keys
- [ ] Each personality has name, tagline, voice dict (style, greeting, thinking_phrases, closing_phrases)
- [ ] Each personality has expertise_areas list and response_format preferences
- [ ] Each personality has system_prompt_additions for LLM prompt injection
- [ ] Siemens=Hans German precision, Rockwell=Mike American practical, ABB=Erik safety-focused, etc.

## Personalities

| Vendor | Name | Style |
|--------|------|-------|
| Siemens | Hans | German precision, methodical, formal |
| Rockwell | Mike | American practical, friendly, solution-focused |
| ABB | Erik | Swiss/Swedish analytical, safety-conscious |
| Schneider | Pierre | French elegance, global perspective |
| Mitsubishi | Takeshi | Japanese precision, thorough |
| FANUC | Ken | CNC expert, production-focused |
| Generic | Alex | Neutral, helpful, general maintenance |

## Files

- `rivet/prompts/sme/personalities.py`
