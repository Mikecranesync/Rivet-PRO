# CLAUDE.md - Rivet Pro

## MISSION
Extract Atlas CMMS from Agent Factory → standalone product in rivet_pro/

## CURRENT OBJECTIVE
**Week 1:** Database models + Telegram bot running standalone

## USER STORY (The "AI Amazing" Part)
Field tech stands in front of broken pump → snaps nameplate photo → 
gets equipment history + likely failure modes + manual link in <10 seconds.
Every interaction trains the system. "I don't know" triggers research, not failure.

## Bash Commands
```bash
# Validate extraction
poetry run python -c "from rivet_pro.atlas.models import Equipment; print('OK')"

# Run bot locally  
poetry run python rivet_pro/bot/bot.py

# Find existing code in Agent Factory
grep -rn "class Equipment\|class WorkOrder" ~/Agent-Factory/ --include="*.py"
grep -rn "cmms" ~/Agent-Factory/migrations/ --include="*.sql"
```

## Code Style
- Python 3.10+, type hints on all functions
- Pydantic for data models
- No imports from agent_factory/ - fully extracted

## Data Schemas (Quick Reference)
```python
Equipment:
  id: UUID
  name: str
  manufacturer: str | None
  model: str | None  
  serial: str | None
  location: str | None
  metadata: dict  # OCR extracted fields
  created_at: datetime

WorkOrder:
  id: UUID
  equipment_id: UUID  # REQUIRED - always linked
  technician_id: UUID
  status: Literal["open", "in_progress", "closed"]
  priority: Literal["low", "medium", "high", "critical"]
  description: str
  created_at: datetime
```

## AI Routing Logic (4 Routes)
1. **LOOKUP** (confidence >0.8) → Direct answer from knowledge base
2. **RESEARCH** (confidence 0.4-0.8) → Trigger knowledge fetch, then answer
3. **CLARIFY** (confidence <0.4) → Ask user for more details
4. **ESCALATE** (safety/unknown) → Flag for human review

## Edge Cases (Handle These)
- OCR fails → Ask user to re-photograph or enter manually
- Equipment not found → Offer to create new entry
- Multiple matches → Show top 3, let user pick
- Network offline → Queue action, sync when back

## Acceptance Criteria
- [ ] Bot runs from rivet_pro/ directory (not agent_factory/)
- [ ] /equip commands work
- [ ] /wo commands work  
- [ ] Photo OCR creates equipment
- [ ] Zero imports from agent_factory/
- [ ] Can run 24 hours without crash

## Workflow
1. Extract one piece at a time
2. Test immediately after extraction
3. Commit working code: `git commit -m "CHECKPOINT: [what works]"`
4. Never build on broken code

## Red Flags - STOP and Report
- Same fix attempted 3+ times
- Changing files outside rivet_pro/
- "This should work" but doesn't
