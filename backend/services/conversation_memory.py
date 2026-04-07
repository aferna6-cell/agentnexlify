"""Conversation memory service — maintains running summaries for context window efficiency.

Instead of passing raw conversation history (which grows unbounded), this service:
1. Creates periodic summaries of conversation segments
2. Extracts and maintains a "memory" of key facts about the user
3. Provides a compact context injection for the system prompt
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ConversationMemory:
    """Structured memory of a conversation."""

    # Running summary of what has been discussed
    summary: str = ""

    # Extracted facts about the user (name, preferences, requirements, etc.)
    user_facts: list[str] = field(default_factory=list)

    # User's stated goals or needs
    goals: list[str] = field(default_factory=list)

    # User's constraints or limitations (budget, timeline, dealbreakers)
    constraints: list[str] = field(default_factory=list)

    # Topics covered so far (to avoid repetition)
    topics_discussed: list[str] = field(default_factory=list)

    # Action items or next steps mentioned
    action_items: list[str] = field(default_factory=list)

    # Sentiment trend (positive, neutral, negative)
    sentiment: str = "neutral"

    def to_prompt_context(self) -> str:
        """Format memory as a context string for the system prompt."""
        parts = []

        if self.summary:
            parts.append(f"Conversation Summary: {self.summary}")

        if self.user_facts:
            facts = ", ".join(self.user_facts)
            parts.append(f"Known Facts: {facts}")

        if self.goals:
            goals = "; ".join(self.goals)
            parts.append(f"User Goals: {goals}")

        if self.constraints:
            constraints = "; ".join(self.constraints)
            parts.append(f"Constraints: {constraints}")

        if self.action_items:
            items = "; ".join(self.action_items)
            parts.append(f"Action Items: {items}")

        if self.topics_discussed:
            topics = ", ".join(self.topics_discussed)
            parts.append(f"Topics Already Discussed: {topics}")

        return "\n".join(parts) if parts else ""

    def to_dict(self) -> dict:
        """Serialize to JSON for database storage."""
        return {
            "summary": self.summary,
            "user_facts": self.user_facts,
            "goals": self.goals,
            "constraints": self.constraints,
            "topics_discussed": self.topics_discussed,
            "action_items": self.action_items,
            "sentiment": self.sentiment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMemory":
        """Deserialize from JSON stored in database."""
        if not data:
            return cls()
        return cls(
            summary=data.get("summary", ""),
            user_facts=data.get("user_facts", []),
            goals=data.get("goals", []),
            constraints=data.get("constraints", []),
            topics_discussed=data.get("topics_discussed", []),
            action_items=data.get("action_items", []),
            sentiment=data.get("sentiment", "neutral"),
        )


def build_memory_prompt(
    memory: ConversationMemory,
    recent_messages: list[dict],
    max_context_chars: int = 2000,
) -> str:
    """Build a context string combining memory and recent messages.

    Strategy: Use the memory summary + last N messages, staying within
    the character budget. This avoids the need to pass the full conversation
    history while maintaining continuity.
    """
    parts = []

    # Start with memory context
    mem_context = memory.to_prompt_context()
    if mem_context:
        parts.append("=== Previous Conversation Context ===")
        parts.append(mem_context)
        parts.append("")

    # Add recent messages
    if recent_messages:
        parts.append("=== Recent Messages ===")
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]  # Cap individual messages
            parts.append(f"{role}: {content}")

    # Trim to fit budget
    full_text = "\n".join(parts)
    if len(full_text) > max_context_chars:
        # Truncate recent messages to fit
        full_text = full_text[:max_context_chars]
        # Find last complete line
        last_newline = full_text.rfind("\n")
        if last_newline > max_context_chars * 0.5:
            full_text = full_text[:last_newline] + "\n...(truncated)"

    return full_text


def extract_memory_update(
    llm_response: str,
    current_memory: ConversationMemory,
    user_message: str,
) -> ConversationMemory:
    """Update conversation memory based on a new exchange.

    In production, this would use an LLM call to extract facts.
    For now, uses rule-based extraction as a lightweight alternative.
    """
    memory = ConversationMemory(
        summary=current_memory.summary,
        user_facts=list(current_memory.user_facts),
        goals=list(current_memory.goals),
        constraints=list(current_memory.constraints),
        topics_discussed=list(current_memory.topics_discussed),
        action_items=list(current_memory.action_items),
        sentiment=current_memory.sentiment,
    )

    # Rule-based fact extraction
    _extract_facts(memory, user_message, llm_response)

    # Update summary (append new info)
    if user_message and len(user_message) > 20:
        # Create a one-line summary of the latest exchange
        exchange_summary = _summarize_exchange(user_message, llm_response)
        if exchange_summary:
            if memory.summary:
                memory.summary += f" {exchange_summary}"
                # Keep summary under 500 chars
                if len(memory.summary) > 500:
                    memory.summary = memory.summary[-500:]
            else:
                memory.summary = exchange_summary

    # Update sentiment
    memory.sentiment = _detect_sentiment(user_message, llm_response)

    return memory


def _extract_facts(memory: ConversationMemory, user_msg: str, _llm_response: str) -> None:
    """Extract facts from user messages using pattern matching."""
    lower = user_msg.lower()

    # Name extraction
    import re
    name_match = re.search(r"\b(?:my name is|i'm|i am)\s+([A-Z][a-z]+)", user_msg)
    if name_match:
        name = name_match.group(1)
        if not any(name in f for f in memory.user_facts):
            memory.user_facts.append(f"Name: {name}")

    # Contact info
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", user_msg)
    if email_match and not any("email" in f for f in memory.user_facts):
        memory.user_facts.append(f"Email: {email_match.group(0)}")

    phone_match = re.search(r"(\+?\d[\d\s()-]{7,})", user_msg)
    if phone_match and not any("phone" in f for f in memory.user_facts):
        memory.user_facts.append(f"Phone: {phone_match.group(1).strip()}")

    # Budget
    budget_match = re.search(r"\$([\d,]+(?:k)?)(?:\s*(?:to|-)\s*\$([\d,]+(?:k)?))?", user_msg, re.IGNORECASE)
    if budget_match and not any("budget" in f for f in memory.constraints):
        budget = budget_match.group(0)
        memory.constraints.append(f"Budget: {budget}")

    # Timeline
    timeline_keywords = ["asap", "urgent", "immediately", "this week", "next week", "next month", "soon", "within"]
    for kw in timeline_keywords:
        if kw in lower and not any("timeline" in c for c in memory.constraints):
            memory.constraints.append(f"Timeline: {kw}")
            break

    # Goals
    goal_keywords = ["looking for", "want to", "need to", "interested in", "would like"]
    for kw in goal_keywords:
        if kw in lower:
            idx = lower.find(kw)
            goal = user_msg[idx:idx+80].strip()
            if goal and not any(goal[:20] in g for g in memory.goals):
                memory.goals.append(goal[:80])
                break


def _summarize_exchange(user_msg: str, llm_response: str) -> str | None:
    """Create a one-line summary of a user-assistant exchange."""
    if not user_msg:
        return None

    # Simple extraction: first sentence of user message
    first_sentence = user_msg.split(".")[0].strip()
    if len(first_sentence) > 100:
        first_sentence = first_sentence[:97] + "..."

    return f"User: {first_sentence}" if first_sentence else None


def _detect_sentiment(user_msg: str, llm_response: str) -> str:
    """Rough sentiment detection based on keyword analysis."""
    positive_words = [
        "great", "awesome", "perfect", "excellent", "thank", "thanks",
        "appreciate", "love", "wonderful", "fantastic", "good", "nice",
        "happy", "pleased", "satisfied",
    ]
    negative_words = [
        "bad", "terrible", "horrible", "worst", "angry", "frustrated",
        "disappointed", "unhappy", "poor", "awful", "hate", "scam",
        "complaint", "sue", "lawyer", "refund",
    ]

    combined = f"{user_msg} {llm_response}".lower()

    pos_count = sum(1 for w in positive_words if w in combined)
    neg_count = sum(1 for w in negative_words if w in combined)

    if pos_count > neg_count + 1:
        return "positive"
    if neg_count > pos_count + 1:
        return "negative"
    return "neutral"
