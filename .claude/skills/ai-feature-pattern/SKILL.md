---
name: ai-feature-pattern
description: "Use this skill when building any feature that calls the Claude API for AI-powered functionality (text generation, categorization, extraction, analysis). Ensures consistent prompt engineering, JSON parsing, and error handling."
version: 1.0.0
origin: claude
allowed_tools: []
triggers: ["AI-powered feature", "Claude API", "text generation", "categorization", "extraction", "AI job writer", "content repurposer", "review response"]
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

## Checklist
- [ ] Model ID is `claude-sonnet-4-6` (verify against CLAUDE.md)
- [ ] API key comes from `settings.anthropic_api_key` (never hardcoded)
- [ ] JSON parsing handles markdown code blocks
- [ ] Both `json.JSONDecodeError` and `anthropic.APIError` are caught
- [ ] Prompt includes output format instructions
- [ ] max_tokens is right-sized (not wastefully large)
- [ ] Background tasks have rate limiting if called per-message
