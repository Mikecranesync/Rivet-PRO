# RIVET Pro - LangGraph Workflow Layer
## Supplementary Specification (Works WITH RIVET_PRO_BUILD_SPEC.md)

---

## ⚠️ IMPORTANT: This is an ADDITIVE spec

**DO NOT** replace or break anything from RIVET_PRO_BUILD_SPEC.md.

This document adds a workflow orchestration layer using LangGraph. The existing structure, database schema, OCR pipeline, and adapters remain unchanged. We're adding a **graph-based workflow engine** on top.

---

## The Problem We're Solving

The original spec has an "Orchestrator" that's basically a big LLM prompt. That works for prototyping, but we want:

1. **Deterministic workflows** for things we CAN define (Photo → OCR → Match → Deliver)
2. **LLM as router** to decide WHICH workflow to trigger
3. **LLM as fallback** only when no workflow matches
4. **Visualizable** execution paths for debugging
5. **Testable** individual workflow steps

---

## New Directory Structure (Additive)

```
rivet_pro/
├── core/
│   ├── workflows/              # NEW: LangGraph workflow definitions
│   │   ├── __init__.py
│   │   ├── state.py            # Shared state definition
│   │   ├── router.py           # LLM intent router
│   │   ├── photo_to_manual.py  # Photo → Manual workflow
│   │   ├── chat_with_doc.py    # Chat with manual workflow
│   │   ├── feedback.py         # Feedback capture workflow
│   │   ├── escalation.py       # "I can't help" workflow
│   │   └── graph.py            # Main graph assembly
│   ├── nodes/                  # NEW: Individual workflow nodes
│   │   ├── __init__.py
│   │   ├── ocr.py              # OCR node (wraps existing pipeline)
│   │   ├── matching.py         # Equipment matching node
│   │   ├── knowledge.py        # KB search/retrieval nodes
│   │   ├── delivery.py         # Manual delivery node
│   │   └── response.py         # Response formatting nodes
│   ├── ocr/                    # EXISTING - no changes
│   ├── knowledge/              # EXISTING - no changes
│   ├── matching/               # EXISTING - no changes
│   └── models/                 # EXISTING - add workflow state models
├── adapters/                   # EXISTING - minor updates to call graph
└── ...
```

---

## Core Concept: Workflow State

All workflows share a common state object that flows through the graph:

```python
# rivet_pro/core/workflows/state.py

from typing import TypedDict, Optional, List, Literal
from pydantic import BaseModel

class Equipment(BaseModel):
    manufacturer: str
    model_number: str
    equipment_type: Optional[str]
    confidence: float

class Manual(BaseModel):
    id: str
    title: str
    file_url: str
    source: Literal["knowledge_base", "web_search", "user_upload"]

class UIElement(BaseModel):
    """Represents a button or interactive element"""
    type: Literal["button", "link", "confirm"]
    label: str
    callback_data: str

class RivetState(TypedDict):
    """
    Shared state that flows through all workflow nodes.
    Each node reads what it needs and adds what it produces.
    """
    # Input
    user_id: str
    message: str
    image_bytes: Optional[bytes]
    platform: Literal["telegram", "whatsapp"]
    
    # Routing
    intent: Optional[str]
    confidence: Optional[float]
    
    # OCR
    ocr_text: Optional[str]
    ocr_confidence: Optional[float]
    ocr_provider: Optional[str]
    
    # Matching
    equipment: Optional[Equipment]
    equipment_candidates: Optional[List[Equipment]]
    needs_clarification: bool
    
    # Knowledge
    manual: Optional[Manual]
    manual_chunks: Optional[List[str]]  # For RAG
    tribal_notes: Optional[List[str]]
    
    # Response
    response_text: str
    response_attachments: Optional[List[str]]
    response_buttons: Optional[List[UIElement]]
    
    # Meta
    workflow_path: List[str]  # Track which nodes we've visited
    error: Optional[str]
```

---

## The Router: LLM as Traffic Cop

The router is the ONLY place non-deterministic LLM logic decides flow:

```python
# rivet_pro/core/workflows/router.py

from typing import Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

INTENT_TYPES = Literal[
    "photo_lookup",      # User sent a photo, wants manual
    "chat_with_manual",  # User asking about equipment already identified
    "general_question",  # User asking something we might know
    "feedback",          # User providing feedback/tribal knowledge
    "greeting",          # Just saying hi
    "unclear",           # Can't determine intent
]

ROUTER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a routing classifier for an industrial maintenance bot.

Analyze the user's message and determine their intent. Consider:
- Did they send an image? (image_present flag)
- Are they asking about equipment we've already discussed? (context)
- Are they providing feedback or tribal knowledge?
- Is this a greeting or small talk?

Respond with ONLY one of these intents:
- photo_lookup: User sent a photo and wants equipment info/manual
- chat_with_manual: User asking about equipment already in context
- general_question: Technical question we might answer from knowledge
- feedback: User providing tips, corrections, or tribal knowledge
- greeting: Hello, thanks, goodbye, etc.
- unclear: Cannot determine what user wants

Also provide confidence 0.0-1.0 and a one-line reason."""),
    ("human", """
Image present: {image_present}
Recent equipment in context: {equipment_context}
User message: {message}

Respond as JSON: {{"intent": "...", "confidence": 0.X, "reason": "..."}}
""")
])

class IntentRouter:
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-3-5-haiku-20241022")
        self.chain = ROUTER_PROMPT | self.llm
    
    async def classify(
        self, 
        message: str, 
        image_present: bool,
        equipment_context: Optional[str] = None
    ) -> tuple[str, float]:
        """Returns (intent, confidence)"""
        result = await self.chain.ainvoke({
            "message": message,
            "image_present": image_present,
            "equipment_context": equipment_context or "None"
        })
        
        # Parse JSON response
        data = json.loads(result.content)
        return data["intent"], data["confidence"]


def route_by_intent(state: RivetState) -> str:
    """
    LangGraph conditional edge function.
    Returns the name of the next node based on intent.
    """
    intent = state.get("intent")
    
    routing_map = {
        "photo_lookup": "ocr_node",
        "chat_with_manual": "rag_search_node",
        "general_question": "knowledge_search_node",
        "feedback": "capture_feedback_node",
        "greeting": "greeting_response_node",
        "unclear": "clarification_node",
    }
    
    return routing_map.get(intent, "fallback_node")
```

---

## Workflow: Photo → Manual (Deterministic Path)

Once the router says "photo_lookup", this is a fixed sequence:

```python
# rivet_pro/core/workflows/photo_to_manual.py

from langgraph.graph import StateGraph, END
from rivet_pro.core.workflows.state import RivetState
from rivet_pro.core.nodes import ocr, matching, knowledge, delivery

def create_photo_to_manual_subgraph() -> StateGraph:
    """
    Deterministic workflow:
    OCR → Match → (Clarify if needed) → Find Manual → Deliver
    """
    
    graph = StateGraph(RivetState)
    
    # Nodes
    graph.add_node("ocr", ocr.extract_from_image)
    graph.add_node("match", matching.find_equipment)
    graph.add_node("clarify", matching.ask_clarification)
    graph.add_node("find_manual", knowledge.search_manual)
    graph.add_node("web_search", knowledge.web_search_manual)
    graph.add_node("deliver", delivery.send_manual)
    graph.add_node("not_found", delivery.manual_not_found)
    
    # Flow
    graph.set_entry_point("ocr")
    graph.add_edge("ocr", "match")
    
    # Conditional: Do we need clarification?
    graph.add_conditional_edges(
        "match",
        matching.needs_clarification_check,
        {
            "confident": "find_manual",
            "needs_clarification": "clarify",
            "no_match": "web_search"
        }
    )
    
    graph.add_edge("clarify", "match")  # Loop back after user clarifies
    
    # Conditional: Found in KB or need web search?
    graph.add_conditional_edges(
        "find_manual",
        knowledge.manual_found_check,
        {
            "found": "deliver",
            "not_found": "web_search"
        }
    )
    
    # Conditional: Web search success?
    graph.add_conditional_edges(
        "web_search",
        knowledge.web_search_success_check,
        {
            "found": "deliver",
            "not_found": "not_found"
        }
    )
    
    graph.add_edge("deliver", END)
    graph.add_edge("not_found", END)
    
    return graph.compile()
```

---

## Individual Nodes (Deterministic Functions)

Each node is a pure function: takes state, returns state updates.

```python
# rivet_pro/core/nodes/ocr.py

from rivet_pro.core.ocr.pipeline import OCRPipeline
from rivet_pro.core.workflows.state import RivetState

ocr_pipeline = OCRPipeline()

async def extract_from_image(state: RivetState) -> dict:
    """
    OCR node: Extract text from image.
    This is DETERMINISTIC - same image = same text (from same provider).
    """
    if not state.get("image_bytes"):
        return {
            "error": "No image provided",
            "workflow_path": state["workflow_path"] + ["ocr:no_image"]
        }
    
    result = await ocr_pipeline.extract(state["image_bytes"])
    
    return {
        "ocr_text": result.text,
        "ocr_confidence": result.confidence,
        "ocr_provider": result.provider,
        "workflow_path": state["workflow_path"] + ["ocr:success"]
    }
```

```python
# rivet_pro/core/nodes/matching.py

from rivet_pro.core.matching.classifier import EquipmentClassifier
from rivet_pro.core.workflows.state import RivetState, Equipment, UIElement

classifier = EquipmentClassifier()

async def find_equipment(state: RivetState) -> dict:
    """
    Matching node: Identify manufacturer and model from OCR text.
    DETERMINISTIC - same text = same match results.
    """
    matches = await classifier.classify(state["ocr_text"])
    
    if len(matches) == 0:
        return {
            "equipment": None,
            "equipment_candidates": [],
            "needs_clarification": False,
            "workflow_path": state["workflow_path"] + ["match:no_match"]
        }
    
    if len(matches) == 1 and matches[0].confidence > 0.85:
        return {
            "equipment": matches[0],
            "equipment_candidates": matches,
            "needs_clarification": False,
            "workflow_path": state["workflow_path"] + ["match:confident"]
        }
    
    # Multiple candidates or low confidence
    return {
        "equipment": None,
        "equipment_candidates": matches[:5],  # Top 5
        "needs_clarification": True,
        "workflow_path": state["workflow_path"] + ["match:needs_clarification"]
    }


def needs_clarification_check(state: RivetState) -> str:
    """Conditional edge: Route based on match confidence"""
    if state.get("needs_clarification"):
        return "needs_clarification"
    if state.get("equipment"):
        return "confident"
    return "no_match"


async def ask_clarification(state: RivetState) -> dict:
    """
    Build clarification response with buttons for candidates.
    """
    candidates = state.get("equipment_candidates", [])
    
    buttons = [
        UIElement(
            type="button",
            label=f"{c.manufacturer} {c.model_number}",
            callback_data=f"select_equipment:{c.model_number}"
        )
        for c in candidates
    ]
    
    buttons.append(UIElement(
        type="button",
        label="None of these",
        callback_data="select_equipment:none"
    ))
    
    return {
        "response_text": "I found a few possibilities. Which one is it?",
        "response_buttons": buttons,
        "workflow_path": state["workflow_path"] + ["clarify:asking"]
    }
```

---

## Main Graph Assembly

```python
# rivet_pro/core/workflows/graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from rivet_pro.core.workflows.state import RivetState
from rivet_pro.core.workflows.router import IntentRouter, route_by_intent
from rivet_pro.core.workflows.photo_to_manual import create_photo_to_manual_subgraph
from rivet_pro.core.nodes import response

# Initialize router
intent_router = IntentRouter()

async def classify_intent_node(state: RivetState) -> dict:
    """Entry node: Classify user intent"""
    intent, confidence = await intent_router.classify(
        message=state["message"],
        image_present=state.get("image_bytes") is not None,
        equipment_context=state.get("equipment", {}).get("model_number")
    )
    return {
        "intent": intent,
        "confidence": confidence,
        "workflow_path": ["router"]
    }


def build_rivet_graph() -> StateGraph:
    """
    Main graph that routes to sub-workflows.
    """
    graph = StateGraph(RivetState)
    
    # Entry point: Classify intent
    graph.add_node("classify_intent", classify_intent_node)
    graph.set_entry_point("classify_intent")
    
    # Sub-workflows as nodes
    graph.add_node("photo_workflow", create_photo_to_manual_subgraph())
    graph.add_node("chat_workflow", create_chat_with_manual_subgraph())
    graph.add_node("feedback_workflow", create_feedback_subgraph())
    
    # Simple response nodes
    graph.add_node("greeting_response", response.greeting)
    graph.add_node("clarification_response", response.ask_for_clarity)
    graph.add_node("fallback_response", response.llm_fallback)
    
    # Routing from classifier
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "photo_lookup": "photo_workflow",
            "chat_with_manual": "chat_workflow",
            "feedback": "feedback_workflow",
            "greeting": "greeting_response",
            "unclear": "clarification_response",
            "general_question": "fallback_response",
        }
    )
    
    # All paths end
    graph.add_edge("photo_workflow", END)
    graph.add_edge("chat_workflow", END)
    graph.add_edge("feedback_workflow", END)
    graph.add_edge("greeting_response", END)
    graph.add_edge("clarification_response", END)
    graph.add_edge("fallback_response", END)
    
    # Add memory for conversation persistence
    memory = MemorySaver()
    
    return graph.compile(checkpointer=memory)


# Singleton graph instance
rivet_graph = build_rivet_graph()
```

---

## Adapter Integration

Update the Telegram adapter to call the graph:

```python
# rivet_pro/adapters/telegram/handlers.py

from telegram import Update
from telegram.ext import ContextTypes
from rivet_pro.core.workflows.graph import rivet_graph
from rivet_pro.core.workflows.state import RivetState

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler - routes everything through the graph"""
    
    user = update.effective_user
    message = update.message
    
    # Build initial state
    state: RivetState = {
        "user_id": str(user.id),
        "message": message.text or message.caption or "",
        "image_bytes": None,
        "platform": "telegram",
        "intent": None,
        "confidence": None,
        "ocr_text": None,
        "ocr_confidence": None,
        "ocr_provider": None,
        "equipment": None,
        "equipment_candidates": None,
        "needs_clarification": False,
        "manual": None,
        "manual_chunks": None,
        "tribal_notes": None,
        "response_text": "",
        "response_attachments": None,
        "response_buttons": None,
        "workflow_path": [],
        "error": None,
    }
    
    # Get image if present
    if message.photo:
        photo = message.photo[-1]  # Highest resolution
        file = await photo.get_file()
        state["image_bytes"] = await file.download_as_bytearray()
    
    # Run the graph
    config = {"configurable": {"thread_id": str(user.id)}}
    result = await rivet_graph.ainvoke(state, config)
    
    # Send response
    await send_response(update, result)


async def send_response(update: Update, state: RivetState):
    """Convert graph output to Telegram response"""
    
    # Build keyboard if buttons present
    keyboard = None
    if state.get("response_buttons"):
        keyboard = build_inline_keyboard(state["response_buttons"])
    
    # Send attachments first
    if state.get("response_attachments"):
        for attachment in state["response_attachments"]:
            await update.message.reply_document(document=attachment)
    
    # Send text response
    await update.message.reply_text(
        text=state["response_text"],
        reply_markup=keyboard
    )
```

---

## Visualization & Debugging

### LangGraph Studio Setup

Create `langgraph.json` in project root:

```json
{
  "dependencies": ["."],
  "graphs": {
    "rivet": "./rivet_pro/core/workflows/graph.py:rivet_graph"
  },
  "env": ".env"
}
```

Run LangGraph Studio:
```bash
pip install langgraph-cli
langgraph dev
```

This gives you a visual debugger showing:
- Which nodes executed
- State at each step
- Conditional edge decisions
- Execution time per node

### LangSmith Integration

Already in your existing spec. Traces will now show the full graph execution path.

---

## Dependencies to Add

```bash
pip install langgraph langgraph-cli
```

Add to `requirements.txt`:
```
langgraph>=0.2.0
langgraph-checkpoint>=1.0.0
```

---

## Implementation Order (Additive to Original Phases)

### After Phase 2 (Photo → Text):
1. [ ] Install LangGraph dependencies
2. [ ] Create `workflows/state.py` with RivetState
3. [ ] Create `nodes/ocr.py` wrapping existing OCR pipeline
4. [ ] Test single node execution

### After Phase 3 (Equipment Matching):
1. [ ] Create `nodes/matching.py` wrapping existing classifier
2. [ ] Create `workflows/photo_to_manual.py` subgraph
3. [ ] Test subgraph in isolation
4. [ ] Set up LangGraph Studio for visualization

### After Phase 4 (Manual Delivery):
1. [ ] Create `nodes/knowledge.py` and `nodes/delivery.py`
2. [ ] Complete photo_to_manual workflow end-to-end
3. [ ] Create `workflows/router.py` with intent classification
4. [ ] Build main graph in `workflows/graph.py`
5. [ ] Update Telegram adapter to use graph

### After Phase 5 (Feedback):
1. [ ] Create `workflows/feedback.py` subgraph
2. [ ] Add feedback nodes
3. [ ] Wire into main graph

---

## Key Principles

1. **Nodes are PURE FUNCTIONS** - No side effects except state updates
2. **Conditional edges are DETERMINISTIC** - Same state = same routing decision
3. **Only the ROUTER uses LLM for decisions** - Everything else is code
4. **State is the single source of truth** - Pass it through, don't store elsewhere
5. **Subgraphs are composable** - Each workflow is its own testable unit
6. **Visualization is built-in** - Use LangGraph Studio during development

---

## Commands to Apply This Spec

```bash
cd rivet-pro

# Make sure you have the original spec
ls RIVET_PRO_BUILD_SPEC.md

# Add this spec alongside it
cp RIVET_PRO_LANGGRAPH_LAYER.md ./

# Tell Claude Code to integrate
claude --dangerously-skip-permissions "Read both RIVET_PRO_BUILD_SPEC.md and RIVET_PRO_LANGGRAPH_LAYER.md. The LangGraph layer is ADDITIVE. After completing the current phase, integrate the workflow architecture from the LangGraph spec. Start by creating the state.py and wrapping existing code in nodes."
```

---

## Why This Is Better

| Before (Original Spec) | After (With LangGraph) |
|------------------------|------------------------|
| Big LLM prompt decides everything | LLM only routes, workflows execute |
| Hard to test | Each node is unit testable |
| Hard to debug | Visual execution traces |
| Can't see what happened | workflow_path tracks every step |
| Unpredictable | Deterministic paths, predictable behavior |
| Expensive (LLM on every decision) | Cheap (LLM only at entry point) |
