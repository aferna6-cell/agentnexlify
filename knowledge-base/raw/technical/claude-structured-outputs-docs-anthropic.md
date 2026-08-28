---
title: Anthropic Docs — Structured Outputs (JSON schema output_config + strict tool use)
date: 2026-08-26
source_url: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
fetched_at: 2026-08-26
category: technical
tags: [anthropic, structured-outputs, json-schema, strict-tools, output-config, pydantic, zod, prompt-cache, lead-extraction]
---

# Structured Outputs (Anthropic platform docs)

*Official docs page; no author byline. Date above is fetch date — page is living documentation.*

## Two features

1. **JSON outputs** — force the response body to conform to a JSON Schema:
   ```json
   "output_config": {
     "format": { "type": "json_schema", "schema": { ... } }
   }
   ```
2. **Strict tool use** — `"strict": true` on a tool definition guarantees tool-call arguments match the tool's `input_schema` exactly.

## Supported models

`claude-fable-5`, `claude-mythos-5`, `claude-opus-5`, `claude-opus-4-8`, `claude-opus-4-7`, `claude-opus-4-6`, `claude-sonnet-5`, `claude-sonnet-4-6`, `claude-sonnet-4-5`, `claude-opus-4-5`, `claude-haiku-4-5`.

## Migration from beta

- The beta `output_format` parameter + header `structured-outputs-2025-11-13` is **deprecated**.
- Python SDK **v1.0+** raises `TypeError` if `output_format` is passed to `client.beta.messages.create()`.
- `client.messages.parse(output_format=PydanticModel)` still works and returns `response.parsed_output`.
- TypeScript: `zodOutputFormat(schema)` helper.

## Runtime behavior

- Grammar is compiled from the schema on **first use** and cached for **24 hours**; any change to the schema or tool set invalidates it (first call after a change is slower).
- Structured output adds tokens to the system prompt; **changing the format invalidates the prompt cache** — keep the schema stable and above the cache breakpoint.

## Schema constraints

| Allowed | Not allowed |
|---|---|
| `additionalProperties: false` (**required** on objects) | Recursive schemas |
| `enum`, `const`, `anyOf`, `allOf` | `allOf` combined with `$ref` |
| Formats: `date-time`, `date`, `email`, `uri`, `uuid`, `ipv4`, `ipv6`, `hostname`, `duration`, `time` | `minimum` / `maximum` / `multipleOf` |
| `minItems` of 0 or 1 | `minLength` / `maxLength` |
| Regex subset (`pattern`) | Regex backreferences, named groups, unicode property classes |
| Local definitions | External `$ref` |

## Example in the docs

The doc's worked example is **lead extraction** — an object with `name`, `email`, `plan_interest`, `demo_requested` extracted from free text.

## Notes for AgentNexLiFy

- `lead-extractor` agent and `lead_qualifier` service currently rely on prompt-enforced JSON; migrate to `output_config.format` for guaranteed parse and drop the retry/parse-fix code.
- Any Pydantic model used with `messages.parse` must set `extra = "forbid"` (→ `additionalProperties: false`) and avoid `Field(ge=, le=, min_length=)` constraints — validate ranges in Python after parse.
- Keep the schema stable per call site — a per-tenant dynamic schema would break both the grammar cache and the prompt cache.
- Check `backend/requirements.txt` anthropic SDK version before using `messages.parse`.
