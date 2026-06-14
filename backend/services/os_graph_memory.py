"""Agent OS knowledge graph — long-term memory that accumulates per owner turn.

Built when the revisit trigger in
``planning/decisions/2026-05-25-agent-os-graph-memory.md`` fired
(owner-requested navigable memory, 2026-06-09).

Pipeline, per orchestrator turn (fired AFTER the reply is persisted, so it
never adds latency to the conversation):

1. ``accumulate_from_turn`` — one Haiku call extracts entities + relations
   from the owner's ask + the assistant's reply. One LLM call per TURN, not
   per memory write — that bound is what the deferral ADR worried about.
2. Nodes upsert by (client_id, entity_type, normalized name): facts append
   (capped, with provenance), mention_count increments, summary refreshes,
   name+summary re-embed for entity search.
3. Edges upsert by (from, to, relation) with observed_count as the weight.
4. Each NEW fact also writes through to ``os_memory_entries`` so the existing
   semantic (vector) recall stays consistent with the graph.

Retrieval: ``graph_kb_entries`` shapes graph nodes + semantic hits into the
engine's ``KbEntry {topic, answer}`` list — the vendored engine consumes it
through ``SharedContext.kb`` with zero engine changes.

Every query is client_id-scoped via tenant_scope; client_id always comes from
the JWT, never a request body.
"""

import json
import logging
import re
from datetime import datetime, timezone

from backend.services import os_memory
from backend.services.embeddings import embed_text
from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

EXTRACTION_MODEL = "claude-haiku-4-5-20251001"

VALID_ENTITY_TYPES = {
    "customer",
    "staff",
    "vendor",
    "service",
    "job",
    "preference",
    "decision",
    "place",
    "other",
}

# Turns shorter than this carry no durable knowledge ("yes", "approve", "ok").
_MIN_TURN_CHARS = 25
# Cap stored facts per node — oldest drop off; summary keeps the gist.
_MAX_FACTS_PER_NODE = 20
# Cap nodes fed into one SharedContext.
_KB_NODE_LIMIT = 12
_KB_SEMANTIC_LIMIT = 6

_EXTRACTION_SYSTEM = """You extract durable business knowledge from one conversation turn between a small-business owner and their AI assistant.

Return ONLY a JSON object, no prose, shaped exactly like:
{"entities": [{"type": "customer", "name": "Sarah Chen", "fact": "Has a pending $680 brake quote"}],
 "relations": [{"from": "Sarah Chen", "to": "brake job", "relation": "requested"}]}

Rules:
- type must be one of: customer, staff, vendor, service, job, preference, decision, place, other
- Extract only DURABLE knowledge worth remembering next week: people, jobs, prices, preferences ("owner closes Sundays"), decisions. Like this: a customer name with their request, a stated business hour, a pricing decision.
- Skip pleasantries, questions with no new information, and anything already obviously known.
- Empty turn -> {"entities": [], "relations": []}
- Each fact is one short sentence, third person, self-contained."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def parse_extraction(text: str) -> dict:
    """Parse the model's JSON (tolerating code fences). Empty result on failure."""
    empty = {"entities": [], "relations": []}
    if not text:
        return empty
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace:
            cleaned = brace.group(0)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        logger.warning("os_graph_memory: unparseable extraction output")
        return empty

    entities = []
    for e in data.get("entities") or []:
        name = (e.get("name") or "").strip()
        fact = (e.get("fact") or "").strip()
        etype = (e.get("type") or "other").strip().lower()
        if not name or not fact:
            continue
        if etype not in VALID_ENTITY_TYPES:
            etype = "other"
        entities.append({"type": etype, "name": name[:120], "fact": fact[:500]})

    relations = []
    for r in data.get("relations") or []:
        frm = (r.get("from") or "").strip()
        to = (r.get("to") or "").strip()
        rel = (r.get("relation") or "").strip().lower()
        if frm and to and rel:
            relations.append({"from": frm[:120], "to": to[:120], "relation": rel[:60]})

    return {"entities": entities[:15], "relations": relations[:15]}


async def extract_turn_knowledge(
    business_name: str, user_text: str, assistant_text: str
) -> dict:
    """One Haiku call: turn text -> {entities, relations}. Empty dict shape on failure."""
    prompt = (
        f"Business: {business_name or 'unknown'}\n\n"
        f"OWNER SAID:\n{user_text[:2000]}\n\n"
        f"ASSISTANT REPLIED:\n{(assistant_text or '')[:2000]}"
    )
    try:
        result = await call_claude_messages(
            operation="os_graph_extract",
            model=EXTRACTION_MODEL,
            max_tokens=600,
            system=_EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            timeout=20.0,
        )
        return parse_extraction(result.text)
    except Exception:
        logger.warning("os_graph_memory: extraction call failed", exc_info=True)
        return {"entities": [], "relations": []}


async def _upsert_node(db, client_id: str, entity: dict, source: str) -> dict | None:
    """Insert or update one node; returns the row. Never raises."""
    try:
        norm = normalize_name(entity["name"])
        existing = (
            tenant_table(db, "os_graph_nodes", client_id)
            .select("*")
            .eq("entity_type", entity["type"])
            .eq("normalized_name", norm)
            .limit(1)
            .execute()
        ).data or []

        fact_row = {"fact": entity["fact"], "source": source, "at": _now()}

        if existing:
            node = existing[0]
            facts = list(node.get("facts") or [])
            known = {f.get("fact") for f in facts}
            if entity["fact"] not in known:
                facts.append(fact_row)
                facts = facts[-_MAX_FACTS_PER_NODE:]
            summary = "; ".join(f.get("fact", "") for f in facts[-5:])
            patch = {
                "facts": facts,
                "summary": summary[:1000],
                "mention_count": (node.get("mention_count") or 0) + 1,
                "last_seen_at": _now(),
                "updated_at": _now(),
            }
            try:
                patch["embedding"] = await embed_text(f"{entity['name']}: {summary}"[:1000])
            except Exception:
                logger.warning("os_graph_memory: node re-embed failed", exc_info=True)
            updated = (
                tenant_table(db, "os_graph_nodes", client_id)
                .update(patch)
                .eq("id", node["id"])
                .execute()
            )
            row = updated.data[0] if updated.data else {**node, **patch}
            # New fact -> write through to semantic memory too.
            if entity["fact"] not in known:
                await os_memory.write_memory(
                    db, client_id, entity["fact"], kind="fact", source=source,
                    created_by="graph",
                )
            return row

        embedding = None
        try:
            embedding = await embed_text(f"{entity['name']}: {entity['fact']}"[:1000])
        except Exception:
            logger.warning("os_graph_memory: node embed failed", exc_info=True)
        created = (
            tenant_table(db, "os_graph_nodes", client_id)
            .insert(
                {
                    "entity_type": entity["type"],
                    "name": entity["name"],
                    "normalized_name": norm,
                    "summary": entity["fact"][:1000],
                    "facts": [fact_row],
                    "embedding": embedding,
                }
            )
            .execute()
        )
        await os_memory.write_memory(
            db, client_id, entity["fact"], kind="fact", source=source,
            created_by="graph",
        )
        return created.data[0] if created.data else None
    except Exception:
        logger.warning(
            "os_graph_memory: node upsert failed name=%s", entity.get("name"),
            exc_info=True,
        )
        return None


def _upsert_edge(db, client_id: str, from_id: str, to_id: str, relation: str) -> None:
    try:
        existing = (
            tenant_table(db, "os_graph_edges", client_id)
            .select("id, observed_count")
            .eq("from_node", from_id)
            .eq("to_node", to_id)
            .eq("relation", relation)
            .limit(1)
            .execute()
        ).data or []
        if existing:
            tenant_table(db, "os_graph_edges", client_id).update(
                {
                    "observed_count": (existing[0].get("observed_count") or 0) + 1,
                    "last_seen_at": _now(),
                }
            ).eq("id", existing[0]["id"]).execute()
        else:
            tenant_table(db, "os_graph_edges", client_id).insert(
                {"from_node": from_id, "to_node": to_id, "relation": relation}
            ).execute()
    except Exception:
        logger.warning("os_graph_memory: edge upsert failed", exc_info=True)


async def accumulate_from_turn(
    db,
    client_id: str,
    user_text: str,
    assistant_text: str | None,
    source: str,
    business_name: str = "",
) -> dict:
    """Extract + persist knowledge from one finished turn. Never raises.

    Designed to run as a background task AFTER the reply is persisted — a
    failure here loses one turn's worth of memory, never the conversation.
    Returns counts for tests/telemetry.
    """
    if len((user_text or "").strip()) < _MIN_TURN_CHARS:
        return {"nodes": 0, "edges": 0, "skipped": "short_turn"}

    extraction = await extract_turn_knowledge(
        business_name, user_text, assistant_text or ""
    )
    if not extraction["entities"]:
        return {"nodes": 0, "edges": 0, "skipped": "no_entities"}

    nodes_by_norm: dict[str, dict] = {}
    node_count = 0
    for entity in extraction["entities"]:
        row = await _upsert_node(db, client_id, entity, source)
        if row:
            node_count += 1
            nodes_by_norm[normalize_name(entity["name"])] = row

    edge_count = 0
    for rel in extraction["relations"]:
        frm = nodes_by_norm.get(normalize_name(rel["from"]))
        to = nodes_by_norm.get(normalize_name(rel["to"]))
        if frm and to and frm["id"] != to["id"]:
            _upsert_edge(db, client_id, frm["id"], to["id"], rel["relation"])
            edge_count += 1

    logger.info(
        "os_graph_memory: accumulated client_id=%s nodes=%d edges=%d",
        client_id,
        node_count,
        edge_count,
    )
    return {"nodes": node_count, "edges": edge_count}


async def accumulate_background(
    client_id: str,
    user_text: str,
    assistant_text: str | None,
    source: str,
    business_name: str = "",
) -> None:
    """BackgroundTasks entrypoint — opens its own db handle, never raises."""
    try:
        from backend.models.database import get_service_supabase

        db = get_service_supabase()
        await accumulate_from_turn(
            db, client_id, user_text, assistant_text, source, business_name
        )
    except Exception:
        logger.warning("os_graph_memory: background accumulate failed", exc_info=True)


def node_to_kb_entry(node: dict) -> dict:
    """Graph node -> engine KbEntry {topic, answer}."""
    return {
        "topic": f"{node.get('entity_type', 'other')}: {node.get('name', '')}",
        "answer": node.get("summary") or "",
    }


async def graph_kb_entries(db, client_id: str, ask: str | None) -> list[dict]:
    """Memory for one turn, shaped as engine KbEntry rows.

    Recent/most-mentioned graph nodes + (when an ask is given) semantic hits
    against os_memory_entries. Returns [] on any failure — memory enrichment
    must never break a turn.
    """
    entries: list[dict] = []
    try:
        nodes = (
            tenant_table(db, "os_graph_nodes", client_id)
            .select("entity_type, name, summary, mention_count, last_seen_at")
            .order("last_seen_at", desc=True)
            .limit(_KB_NODE_LIMIT)
            .execute()
        ).data or []
        entries.extend(node_to_kb_entry(n) for n in nodes if n.get("summary"))
    except Exception:
        logger.warning("os_graph_memory: kb node read failed", exc_info=True)

    if ask:
        try:
            hits = await os_memory.search_memory(
                db, client_id, ask, match_count=_KB_SEMANTIC_LIMIT
            )
            seen = {e["answer"] for e in entries}
            for h in hits:
                content = h.get("content") or ""
                if content and content not in seen:
                    entries.append({"topic": f"memory: {h.get('kind', 'fact')}", "answer": content})
        except Exception:
            logger.warning("os_graph_memory: semantic enrich failed", exc_info=True)

    return entries


def list_graph(db, client_id: str) -> dict:
    """Full graph for the owner's Memory view (no embeddings)."""
    nodes = (
        tenant_table(db, "os_graph_nodes", client_id)
        .select(
            "id, entity_type, name, summary, facts, mention_count, "
            "created_at, last_seen_at"
        )
        .order("last_seen_at", desc=True)
        .limit(500)
        .execute()
    ).data or []
    edges = (
        tenant_table(db, "os_graph_edges", client_id)
        .select("id, from_node, to_node, relation, observed_count, last_seen_at")
        .order("last_seen_at", desc=True)
        .limit(1000)
        .execute()
    ).data or []
    return {"nodes": nodes, "edges": edges}


def delete_node(db, client_id: str, node_id: str) -> bool:
    """Owner 'forget this' — edges cascade via FK."""
    result = (
        tenant_table(db, "os_graph_nodes", client_id)
        .delete()
        .eq("id", node_id)
        .execute()
    )
    return bool(result.data)
