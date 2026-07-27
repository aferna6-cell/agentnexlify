"""Graph state and channel reducers.

State is a flat dict. Every key is a *channel* with a declared reducer that
says how concurrent writes combine. Reducers are what make parallel branches
safe: without them, two nodes writing the same key in one superstep race, and
the winner depends on asyncio scheduling order.
"""

import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from backend.graph.errors import ChannelConflictError

# A reducer takes (existing_value_or_MISSING, incoming_value) and returns the
# merged value. It is called once per write, folded left over the writes of a
# superstep in node-name order so the result never depends on scheduling.
Reducer = Callable[[Any, Any], Any]


class _Missing:
    """Sentinel for 'this channel has no value yet'.

    A dedicated type rather than ``None`` because ``None`` is a legitimate
    channel value.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING = _Missing()


def reduce_last(existing: Any, incoming: Any) -> Any:
    """Last write wins. The default."""
    return incoming


def reduce_append(existing: Any, incoming: Any) -> list:
    """Concatenate into a list. A non-list incoming value is appended as one item."""
    base = [] if existing is MISSING or existing is None else list(existing)
    if isinstance(incoming, list):
        return base + incoming
    return base + [incoming]


def reduce_merge(existing: Any, incoming: Any) -> dict:
    """Shallow dict update."""
    if not isinstance(incoming, dict):
        raise ChannelConflictError(
            f"merge reducer requires a dict, got {type(incoming).__name__}"
        )
    base = {} if existing is MISSING or existing is None else dict(existing)
    base.update(incoming)
    return base


def reduce_add(existing: Any, incoming: Any) -> Any:
    """Numeric sum."""
    base = 0 if existing is MISSING or existing is None else existing
    return base + incoming


def reduce_once(existing: Any, incoming: Any) -> Any:
    """Write-once. A second write is a hard error, not a silent overwrite."""
    if existing is not MISSING:
        raise ChannelConflictError(
            f"channel is write-once and already holds {existing!r}; "
            f"refusing to overwrite with {incoming!r}"
        )
    return incoming


REDUCERS: dict[str, Reducer] = {
    "last": reduce_last,
    "append": reduce_append,
    "merge": reduce_merge,
    "add": reduce_add,
    "once": reduce_once,
}


@dataclass(frozen=True)
class Channel:
    """Declares one state key: how writes combine and what it starts as."""

    name: str
    reducer: str = "last"
    default: Any = MISSING

    def __post_init__(self) -> None:
        if self.reducer not in REDUCERS:
            raise ValueError(
                f"unknown reducer {self.reducer!r} for channel {self.name!r}; "
                f"valid: {sorted(REDUCERS)}"
            )


@dataclass
class StateSchema:
    """The set of channels a graph reads and writes.

    ``strict`` controls what happens when a node writes an undeclared key.
    Strict schemas catch typos ("summry" vs "summary") at run time instead of
    letting them accumulate as dead state; permissive schemas auto-declare the
    key with the ``last`` reducer, which is the right default for quick
    scripts and tests.
    """

    channels: dict[str, Channel] = field(default_factory=dict)
    strict: bool = False

    @classmethod
    def build(cls, spec: dict[str, str | Channel] | None = None, strict: bool = False):
        """Build from a compact ``{"messages": "append"}`` mapping."""
        channels: dict[str, Channel] = {}
        for name, value in (spec or {}).items():
            channels[name] = (
                value if isinstance(value, Channel) else Channel(name, reducer=value)
            )
        return cls(channels=channels, strict=strict)

    def declare(self, name: str, reducer: str = "last", default: Any = MISSING) -> None:
        self.channels[name] = Channel(name, reducer=reducer, default=default)

    def reducer_for(self, name: str) -> Reducer:
        channel = self.channels.get(name)
        if channel is None:
            if self.strict:
                raise ChannelConflictError(
                    f"undeclared channel {name!r}; declare it on the graph's "
                    f"state schema or set strict=False"
                )
            return reduce_last
        return REDUCERS[channel.reducer]

    def initial(self) -> dict[str, Any]:
        """Starting state from channel defaults."""
        return {
            name: copy.deepcopy(channel.default)
            for name, channel in self.channels.items()
            if channel.default is not MISSING
        }


def apply_updates(
    state: dict[str, Any],
    updates: list[tuple[str, dict[str, Any]]],
    schema: StateSchema,
) -> dict[str, Any]:
    """Fold a superstep's writes into a new state dict.

    ``updates`` is ``[(node_name, delta), ...]``. It is sorted by node name
    before folding, so a superstep's result is identical no matter which node
    happened to finish first — that determinism is the whole point of applying
    writes at the superstep boundary rather than as they land.

    The input ``state`` is not mutated; a new dict is returned so checkpoints
    of earlier supersteps stay valid.
    """
    merged = dict(state)
    for node_name, delta in sorted(updates, key=lambda item: item[0]):
        if not delta:
            continue
        for key, value in delta.items():
            reducer = schema.reducer_for(key)
            existing = merged.get(key, MISSING)
            try:
                merged[key] = reducer(existing, value)
            except ChannelConflictError as exc:
                raise ChannelConflictError(
                    f"node {node_name!r} writing channel {key!r}: {exc}"
                ) from exc
    return merged
