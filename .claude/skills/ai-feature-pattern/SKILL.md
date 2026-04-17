---
name: ai-feature-pattern
description: "Use this skill when building any feature that calls the Claude API for AI-powered functionality (text generation, categorization, extraction, analysis). Ensures consistent prompt engineering, JSON parsing, and error handling."
version: 1.1.0
origin: claude
allowed-tools: []
triggers: ["AI-powered feature", "Claude API", "text generation", "categorization", "extraction", "AI job writer", "content repurposer", "review response"]
effort: medium
---

# AI Feature Pattern

## When to Use
- Building a feature that calls the Anthropic Claude API
- Adding AI-powered text generation, categorization, extraction, or analysis
- Examples: AI job writer, conversation categorizer, content repurposer, review response drafting

## When NOT to Use
- Simple CRUD features with no AI calls
- Features using non-Anthropic LLMs (OpenAI, etc.)
- One-off scripts or local AI experiments outside the production service
- Tasks that only involve prompt engineering without API integration

## Standard Pattern

### 1. Prompt Engineering
- Include business context (tenant name, type, city) when available
- Be explicit about output format: "Return ONLY valid JSON with these fields..."
- Include "Output ONLY the JSON object, no markdown fences" to reduce parsing issues
- Set `temperature=0` for deterministic tasks (categorization, extraction)
- Use default temperature for creative tasks (writing, drafting)

### 2. API Call Template
```python
import anthropic
from backend.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
response = client.messages.create(
    model="claude-sonnet-4-6",  # Always use this exact model ID
    max_tokens=1000,            # Right-size for the task
    messages=[{"role": "user", "content": prompt}],
)
text = response.content[0].text.strip()
```

### 3. JSON Parsing (Required)
Always handle markdown code blocks — the model sometimes wraps JSON:
```python
import json

if text.startswith("```"):
    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    text = text.rsplit("```", 1)[0].strip()

result = json.loads(text)
```

### 4. Error Handling (Required)
Always catch these three errors:
```python
except json.JSONDecodeError:
    logger.warning("AI returned invalid JSON: %s", text[:200])
    raise HTTPException(status_code=502, detail="AI returned invalid response — try again")
except anthropic.APIError as e:
    logger.warning("Anthropic API error: %s", str(e))
    raise HTTPException(status_code=502, detail="AI service error — try again")
```

### 5. Background Tasks
For non-blocking AI calls (categorization, tagging), use FastAPI BackgroundTasks:
```python
background_tasks.add_task(_categorize_thing, tenant_id, data)
```
- Background AI tasks should fail silently (log warning, don't raise)
- Rate-limit background calls to avoid cost explosion (e.g., every 5th message)

### 6. Managed Agent / Structured Extraction Pattern
For field-extraction tasks (leads, contacts, entities from free text), prefer the `structured_extractor` managed agent over custom prompt chains:

```python
# backend/services/structured_extractor.py
from backend.services.structured_extractor import extract_structured

try:
    result = extract_structured(
        tenant_id=tenant_id,
        raw_text=raw_text,
        target_schema="lead",   # "lead" | "appointment" | etc.
    )
    # result is a dict — keys depend on schema, values may be None
    name  = result.get("name")
    email = result.get("email")
    phone = result.get("phone")
    interest = result.get("interest")   # maps to areas_of_interest in DB
except ValueError as exc:
    # structured_extractor raises ValueError on parse failure (not a custom exception class)
    # Do NOT catch ExtractorError — it does not exist
    logger.warning("extractor parse failed: %s", exc)
except Exception:
    logger.exception("unexpected extractor error")
```

Key rules:
- Raises `ValueError` on JSON parse failure — catch specifically, not generically
- No custom exception class — `ExtractorError` does NOT exist; grepping the file before coding a catch block prevents spec drift
- `target_schema="lead"` returns `{name, email, phone, interest, timeline, budget, source}`
- `interest` key maps to `areas_of_interest` DB column — apply field mapping explicitly
- Always run as background task (after response sent) to avoid latency impact on happy path

## Checklist
- [ ] Model ID is `claude-sonnet-4-6` (verify against CLAUDE.md)
- [ ] API key comes from `settings.anthropic_api_key` (never hardcoded)
- [ ] JSON parsing handles markdown code blocks
- [ ] Both `json.JSONDecodeError` and `anthropic.APIError` are caught
- [ ] Prompt includes output format instructions
- [ ] max_tokens is right-sized (not wastefully large)
- [ ] Background tasks have rate limiting if called per-message

## Gotchas
- **Haiku wraps JSON in ` ```json ` fences ~50% of the time** even when told not to. Strict `json.loads` will crash. Always use fence-tolerant parsing. See `backend/services/structured_extractor.py::_extract_json_from_reply` for the canonical helper.
- **Model ID drift.** Only `claude-sonnet-4-6`, `claude-opus-4-7`, or `claude-haiku-4-5-20251001`. Any other ID → 404 from Anthropic. These change over time — verify against CLAUDE.md.
- **Opus 4.7 sampling ban.** `claude-opus-4-7` returns 400 if you pass `temperature`, `top_p`, or `top_k`. `llm_runtime.call_claude_messages_sync` auto-strips them. Direct `anthropic.Anthropic()` calls must omit them manually.
- **Opus 4.7 prefill ban.** Prefilling assistant messages on 4.7 returns 400. Use structured outputs / system prompt instead.
- **Streaming responses + thinking mode.** Set `thinking.display: "omitted"` or the extended-thinking tokens get interleaved with user-visible text.
- **max_tokens too small silently truncates mid-JSON.** A 512-token cap on a "return a JSON object" prompt will produce unparseable output in ~5% of calls. Right-size for the expected output, not the input.
- **`temperature=0` is not deterministic.** Claude still varies slightly. Don't write regression tests that assert exact text output — assert on shape/fields.
- **Background task + error swallowing.** `background_tasks.add_task` runs after response is returned — exceptions don't reach the client. Must log with `logger.exception(...)` or errors disappear.
- **Leaking the API key in logs.** Never log `response.request` objects or full headers — the Anthropic SDK sometimes includes the Bearer token. Log only `response.id` and `stop_reason`.
- **Per-message AI calls without rate limit = cost explosion.** Categorizer on every chat message runs up $50-$100/day on a busy tenant. Gate on message count (every 5th) or conversation milestone.
- **`content[0].text` assumes text-only response.** If tools are enabled, the first block might be `tool_use`. Iterate with `[b for b in response.content if b.type == "text"]`.
- **Prompt caching** (`cache_control`) only helps on identical prompts. System prompt drift between tenants → no cache hit → no savings.
