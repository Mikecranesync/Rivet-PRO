# SKILL: AI Routing Logic

## When to Load This Skill
Claude should read this when working on:
- Intent detection
- Confidence scoring
- Response routing
- Knowledge base queries

## The 4-Route Orchestrator

### Route 1: LOOKUP (Direct Answer)
**Trigger:** Confidence score >0.8 AND exact match in knowledge base
**Action:** Return answer with source citation
**Example:** "What's the torque spec for a Baldor M3538?" → Found in atom, return immediately

### Route 2: RESEARCH (Knowledge Gap)
**Trigger:** Confidence 0.4-0.8 OR partial match
**Action:** 
1. Log the gap (atom_id, query, confidence)
2. Search external sources (manuals, forums)
3. If found: Create new knowledge atom, return answer
4. If not found: Route to CLARIFY

**Example:** "Why is my VFD throwing F0021?" → Partial match, research Siemens fault codes

### Route 3: CLARIFY (Ambiguous Intent)
**Trigger:** Confidence <0.4 OR multiple interpretations
**Action:** Ask ONE clarifying question (never multiple)
**Example:** "It's making a noise" → "Can you describe the noise? (grinding, humming, clicking)"

### Route 4: ESCALATE (Safety/Unknown)
**Trigger:** 
- Safety-critical equipment mentioned
- Electrical work on live systems
- Unknown failure mode with injury risk
**Action:** 
1. Do NOT provide troubleshooting steps
2. Display safety warning
3. Recommend qualified technician
4. Log for human review within 10min SLA

## Confidence Scoring

```python
def calculate_confidence(query: str, matches: list[KnowledgeAtom]) -> float:
    if not matches:
        return 0.0
    
    top_match = matches[0]
    score = top_match.similarity_score  # 0-1 from vector search
    
    # Boost for exact manufacturer match
    if query_manufacturer in top_match.manufacturer:
        score += 0.1
    
    # Boost for exact model match  
    if query_model in top_match.model:
        score += 0.15
    
    # Penalty for old atoms (>2 years)
    if top_match.age_days > 730:
        score -= 0.1
    
    return min(score, 1.0)
```

## Knowledge Atom Structure

```python
class KnowledgeAtom(BaseModel):
    atom_id: str  # e.g., "fault:siemens:f0021"
    type: Literal["fault", "procedure", "spec", "part"]
    manufacturer: str
    model: str | None
    title: str
    content: str
    source: str  # URL or manual reference
    confidence: float  # How verified is this?
    created_at: datetime
    last_verified: datetime
```

## Gap Detection (Self-Healing Knowledge Base)

When RESEARCH route is triggered:
1. Create `KnowledgeGap` record
2. Queue for Research Agent (async)
3. Research Agent searches:
   - Official manufacturer documentation
   - Technical forums (Reddit, Stack Overflow)
   - YouTube transcripts from verified channels
4. If quality source found:
   - Create new `KnowledgeAtom`
   - Link to original gap
   - Mark gap as resolved
5. Track gap→resolution time for metrics
