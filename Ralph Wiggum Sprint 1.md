<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# okay, combine everything we've learned together over the last few prompts and create a comprehensive complete prompt for Claude code to build what we talked about using Ralph wiggum. if there are multiple features to be built, break them out into individual features or Ralph wiggum prompts. please only output plain text because I'm going to listen to it

Master prompt for Claude Code (Ralph Wiggum loop)

You are Ralph Wiggum, my autonomous engineering agent. You will design and iteratively build the backend for my “Rivet Pro” maintenance assistant. Rivet Pro runs primarily through a Telegram bot. Technicians in the field send photos of equipment, and Rivet Pro identifies the equipment, finds the correct manual, and lets them chat with the manual in natural language. You should plan and build this system end‑to‑end in small, verifiable increments.

Key constraints:

- I am not a developer; you must explain what you are doing in simple language, and produce ready‑to‑run code and n8n workflows.
- Prefer free or very low‑cost tools: Groq, DeepSeek, DuckDuckGo/Brave/search scraping, self‑hosted/open‑source components, and my existing VPS.
- Use deterministic matching and rule‑based filters first; use light LLM calls only as a final judge.
- Stack should be simple: Telegram bot + n8n + PostgreSQL + vector DB (Pinecone free tier or open‑source) + optional Neo4j for graphs. Avoid anything that needs heavy ops.
- Always check the code base first for code that may have Already have been built. use it if possible to speed development. 

Rivet Pro high‑level behavior:

1) Technician sends a photo of a nameplate (e.g., Allen‑Bradley Micro820) to Telegram.
2) System OCRs the image, extracts manufacturer, model, serial, and other key text.
3) System logs the user (Telegram chat ID) and the equipment into a user→equipment history table.
4) System checks a prebuilt knowledge base of manuals to see if we already have a high‑confidence manual match. If yes, immediately sends manual PDF link back to the user.
5) If manual not present, a 24/7 “knowledge factory” process continuously searches the web for manuals by product family and manufacturer, validates, downloads, and indexes them so that next time they are available instantly.
6) Over time, the system builds:
    - A per‑user “knowledge graph” of what equipment they work on and what questions they ask.
    - A product knowledge graph linking equipment, product families, manuals, fault codes, and related components (drives → contactors → fuses → motors).
7) Technicians can then “chat with the manual” in natural language (any language). The system uses RAG: vector search over manuals + (later) knowledge graph traversal, then generates an answer and an “expert judge” module scores whether it’s safe and correct before sending.

You will build this as several independent features (“Ralph Wiggum prompts”), each shippable and testable on its own. For each feature, do ALL of the following:

- Describe the goal in one paragraph in plain language.
- List dependencies on earlier features.
- Design the data model (PostgreSQL tables, indexes, key fields).
- Design the n8n workflow(s) step by step, naming nodes and data passing between them.
- Provide code snippets where needed (Telegram bot, webhooks, simple services).
- Explain how I can test it manually.
- Explain how it will be extended in later features.

Do NOT write pseudocode only. I want real, runnable examples, but keep them focused and minimal.

Break the work into the following Ralph Wiggum feature prompts (work on them sequentially; I will paste each one into you as we go):

FEATURE 1 – Telegram intake, OCR, and user/equipment logging

Goal:
Take a photo sent to the Telegram bot, extract manufacturer and model text from the nameplate, and log which user sent which equipment so we start building user memory.

Requirements:

- Telegram bot that accepts photo messages.
- Sends the image to an OCR service (can be an open‑source container, cloud OCR free tier, or a model from Groq/DeepSeek that can do vision; pick something practical and cheap).
- Extracts at least: manufacturer, model, serial (if present), plus any extra useful strings.
- Stores a record in PostgreSQL:
    - users: id, telegram_chat_id, first_seen_at, last_seen_at, metadata.
    - equipment: id, manufacturer, model, serial, raw_ocr_text, created_at.
    - user_equipment_events: id, user_id, equipment_id, timestamp, source_message_id, notes.
- n8n workflow design:
    - Trigger on Telegram webhook.
    - Download photo.
    - Call OCR.
    - Parse text to identify manufacturer and model (with deterministic regex + fuzzy matching, not heavy LLM).
    - Upsert user in users table.
    - Insert or upsert equipment in equipment table (based on manufacturer + model + serial).
    - Insert a user_equipment_events row.
    - Respond to user with a simple acknowledgement: “I think this is [manufacturer] [model]. I’m looking for your manual now.”

Deliverables:

- Exact PostgreSQL CREATE TABLE statements.
- Example Telegram bot code (could be Python + python-telegram-bot or Node.js) and how it posts to n8n.
- n8n workflow description with node names and what each node does.

FEATURE 2 – Manual knowledge base schema and lookup from Telegram

Goal:
When a user sends a photo, if we already have a matching manual in our knowledge base, instantly return the best manual PDF/link.

Requirements:

- Extend PostgreSQL schema:
    - equipment_manuals:
        - id
        - equipment_key (manufacturer + model normalized)
        - manufacturer
        - model
        - manual_title
        - manual_type (user_manual, install_guide, programming, datasheet, etc.)
        - pdf_original_url
        - pdf_local_path
        - file_hash
        - file_size_bytes
        - language
        - confidence_score (0–1)
        - source (duckduckgo, brave, manufacturer, etc.)
        - created_at, updated_at
- Define “equipment_key” normalization rules (e.g., strip whitespace, dashes, upper‑case).
- n8n extension to Feature 1:
    - After logging user \& equipment, attempt to find a matching manual:
        - Query equipment_manuals where equipment_key matches or is very close (Levenshtein or similar).
        - Order by confidence_score DESC, prefer same manufacturer and language.
    - If found manual with confidence_score ≥ 0.8:
        - Reply to user with PDF link (from local_path or signed URL).
    - If not found:
        - Reply: “I don’t have this manual yet, but I’m adding it to the queue. I’ll learn it soon.”

Deliverables:

- SQL schema for equipment_manuals and indexes.
- Matching logic description (how to compute equipment_key and how to select best manual).
- Update to existing n8n workflow to perform this lookup and respond appropriately.

FEATURE 3 – 24/7 “knowledge factory” for harvesting manuals by manufacturer/product family (free search stack)

Goal:
Continuously crawl the web and populate equipment_manuals, focusing on product families (e.g., Siemens drives, contactors, etc.), using free search engines (DuckDuckGo, Brave, etc.) and simple rule‑based filters plus light LLM validation via Groq/DeepSeek.

Requirements:

- Define a configuration table in PostgreSQL:
    - product_families:
        - id
        - manufacturer
        - family_name (e.g., “Siemens SINAMICS drives”)
        - search_patterns (JSON array of query templates)
        - estimated_sku_count (rough guess)
        - target_coverage_percent (e.g., 70)
        - current_manual_count
        - last_crawled_at
        - status (active, paused)
- n8n “knowledge factory” workflow:
    - Runs on schedule (e.g., every hour).
    - Selects one or more product_families with lowest coverage or oldest last_crawled_at.
    - For each family:
        - Generate search queries (using templates like: “{manufacturer} {family} user manual pdf”, “{model} manual pdf”, etc.).
        - Call DuckDuckGo or other free search endpoint via HTTP GET (respect reasonable rate limits).
        - Parse HTML results to extract candidate links.
        - Filter candidates deterministically:
            - Must be .pdf or clearly a PDF download.
            - HTTP status 200.
            - File size between 100KB and, say, 50MB.
            - Domain scoring: prefer manufacturer domains, documentation domains; blacklist obvious spam.
            - Basic text match: title/snippet must contain manufacturer or family keywords and words like “manual”, “user guide”, “installation”, “datasheet”.
        - Score each candidate (0–100) from these rules.
        - Keep top N (e.g., 3–5) per search query.
        - For these candidates, call a free LLM (Groq/DeepSeek) with a tiny prompt:
            - “Equipment family: [family description]. Result: [title], [domain], [snippet]. Is this likely a manual for some product in this family? Respond YES or NO only.”
        - Only keep links where LLM says YES.
        - Download PDFs for accepted links, compute file_hash, store to disk (local_path), extract minimal metadata (title, maybe first page text).
        - Insert into equipment_manuals with a reasonable confidence_score and source=”duckduckgo+rules+llm_yes”.
    - Update product_families.current_manual_count and last_crawled_at.
- No heavy vector embedding yet in this feature; the goal is to just populate PDFs.

Deliverables:

- SQL schema for product_families.
- Detailed n8n workflow steps for the harvesting pipeline.
- Example LLM prompt and expected simple responses.
- Rules for scoring candidates (explain in plain language).

FEATURE 4 – Vectorization and RAG over manuals (“chat with your manual”)

Goal:
Given a user question about a piece of equipment, retrieve relevant manual passages and answer in natural language using RAG (retrieval‑augmented generation). Support any language for the user question; it’s fine if manuals are in English at first.

Requirements:

- Choose a free or cheap embedding system:
    - Either a self‑hosted open‑source embedding model (e.g., via Hugging Face or Ollama) OR free embeddings from a provider that has a decent free tier.
- Design vector schema:
    - manual_chunks:
        - id
        - manual_id (FK into equipment_manuals)
        - chunk_index
        - text
        - embedding_vector_id (ID in vector DB)
        - created_at
- Offline vectorization process (n8n or a simple script):
    - For each manual with pdf_local_path and no chunks:
        - Extract text from PDF (use Tesseract or another free tool).
        - Split into chunks (e.g., 500–800 tokens with overlap).
        - For each chunk, compute embeddings and store into vector DB (Pinecone or open‑source).
        - Insert row into manual_chunks with embedding id.
- New Telegram conversation path:
    - When a user has an equipment_id identified from a recent photo, and they send a text question (e.g., “Why is my drive showing F0012?”):
        - Look up one or more manuals linked to that equipment (equipment_manuals).
        - Perform vector search against the chunks for those manuals:
            - Convert user question to embedding.
            - Query the relevant subset of vectors.
            - Retrieve top K chunks.
        - Build a context prompt: include the question and the retrieved chunks as context.
        - Call a free LLM (Groq/DeepSeek) to generate an answer in natural language with explicit references: “According to [Manual X, page Y]…”
        - Return the answer to the user through Telegram.
- Keep this feature simple: no graph DB yet, just vector RAG over manuals, but design everything with the graph extension in mind.

Deliverables:

- Schema for manual_chunks.
- Description of vectorization pipeline.
- Example prompt for answering questions from retrieved chunks.
- The flow from Telegram question → RAG → Telegram answer.

FEATURE 5 – Basic user knowledge graph (without Neo4j yet)

Goal:
Start tracking which equipment and product families each user interacts with, so we can later build personalization and analytics. For now, implement this as relational tables and views in PostgreSQL, not a full graph database.

Requirements:

- Extend schema:
    - user_equipment_stats (materialized view or table updated by cron / n8n):
        - user_id
        - equipment_key
        - manufacturer
        - model
        - product_family (optional string for now)
        - query_count
        - last_seen_at
    - user_family_stats:
        - user_id
        - manufacturer
        - product_family
        - query_count
        - last_seen_at
- Process:
    - Nightly n8n job scans user_equipment_events and aggregates counts into these stats tables.
- Use cases:
    - When user sends a new query, the system can see:
        - Their top 3 product families.
        - Their historical equipment usage.
    - This will later let us:
        - Prioritize manual harvesting for top product families used by many users.
        - Provide targeted tips (“You often work on Siemens drives; here’s a quick reference card.”).

Deliverables:

- SQL for stats tables or materialized views.
- n8n aggregation workflow description.
- Example queries I can run to ask:
    - “What does this technician mostly work on?”
    - “Which product families are most common across all users?”

FEATURE 6 – Product knowledge graph (first cut) and cross‑manual reasoning

Goal:
Add a simple product‑level knowledge graph that can link related equipment and manuals (e.g., VFDs to contactors, fuses, PLCs), and feed these relationships into the RAG pipeline so answers can consider multiple products, not just one manual.

Requirements:

- For now, still store graph data in PostgreSQL using adjacency tables, not Neo4j (keep ops simple). Later you can migrate to Neo4j if needed.
- Schema:
    - products:
        - id
        - manufacturer
        - model
        - product_type (drive, contactor, fuse, plc, hmi, etc.)
        - product_family
        - equipment_key
    - product_relations:
        - id
        - from_product_id
        - to_product_id
        - relation_type (e.g., “POWERED_BY”, “PROTECTS”, “CONTROLS”, “SIMILAR_TO”, “PART_OF_FAMILY”)
        - confidence (0–1)
        - source (manual_text, human_input, rule, etc.)
        - created_at
- Populate this graph first using simple rules and manual seeding:
    - If a manual for a drive references a particular contactor or fuse family, create relations like DRIVE POWERED_BY CONTACTOR, CONTACTOR PROTECTS MOTOR, etc.
    - These can be inferred by scanning manual text or initially hardcoded lists for major families.
- Extend RAG retrieval:
    - When answering a question about equipment A, look up:
        - The product node for A.
        - All directly related products within 1 hop (e.g., its typical contactor, fuse, etc.).
    - Include relevant manual chunks from those related products in the retrieval set so answers can mention them when appropriate (e.g., “Also check the contactor upstream of the drive…”).

Deliverables:

- SQL schema for products and product_relations.
- Rules for initial relation creation (you can assume simple heuristics now).
- Description of how RAG retrieval incorporates these related products into the context.

FEATURE 7 – Expert judge and feedback loop

Goal:
Create an “expert judge” module that scores every answer before sending it to the user, and learns over time from user feedback, so answer quality keeps improving.

Requirements:

- Schema:
    - answers:
        - id
        - user_id
        - equipment_id
        - question_text
        - answer_text
        - source_manual_ids (JSON array)
        - created_at
    - answer_scores:
        - id
        - answer_id
        - automatic_score (0–1)
        - reasoning (short text, optional)
        - user_feedback (helpful/not_helpful/null)
        - final_score (0–1)
        - flagged_for_review (bool)
        - reviewed_by (optional)
        - reviewed_at (optional)
- Automatic judge logic:
    - Implement as a small service or n8n sub‑workflow that:
        - Checks that answer_text cites at least one manual and that those manuals exist.
        - Optionally calls a small LLM (Groq/DeepSeek) with a short prompt:
            - “Given this question and these manual excerpts, does the answer correctly reflect the manuals and avoid making unsafe claims? Score between 0 and 1 and justify briefly.”
        - Produces automatic_score and brief reasoning.
    - If automatic_score >= 0.85:
        - final_score = automatic_score, send answer to user.
    - If automatic_score < 0.75:
        - still send answer but mark flagged_for_review = true.
        - Optionally, send shorter/safer response (“I’m not fully confident; here are some possible checks.”).
- User feedback:
    - After sending an answer to Telegram, add quick feedback buttons:
        - “Helpful 👍” → user_feedback = helpful.
        - “Not helpful 👎” → user_feedback = not_helpful.
    - n8n workflow logs this feedback to answer_scores.
- Later:
    - You can build simple analytics:
        - Answers with many “not helpful” votes.
        - Product families with systematically low scores (need better coverage or rules).

Deliverables:

- SQL schema for answers and answer_scores.
- Description of automatic scoring pipeline.
- Example judge prompt that uses manuals + answer + question.
- Flow of how Telegram feedback updates the scores.

GENERAL INSTRUCTIONS FOR CLAUDE (Ralph Wiggum):

1) For each feature above, produce:
    - Architecture summary (1–2 paragraphs).
    - Concrete schemas, workflows, and code snippets.
    - Clear testing instructions.
2) Assume you will be called multiple times: each time, focus on ONE feature and go deep instead of trying to do all at once.
3) Keep everything as simple and free as possible:
    - Prefer DuckDuckGo/Brave + HTML parsing to paid Google APIs.
    - Prefer Groq/DeepSeek and free embeddings.
    - Use self‑hosted services where realistic on a single VPS.
4) Always think about:
    - How this connects back to Telegram (the technician UX).
    - How it contributes to long‑term knowledge building (user histories, product families, graphs).
    - How a non‑developer can run, test, and debug it.

Your first task will be FEATURE 1. Once you finish, I will paste that section back to you and ask you to generate FEATURE 1 in detail.
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: 1000004450.jpg

