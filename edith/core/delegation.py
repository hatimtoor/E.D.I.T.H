"""Multi-agent delegation (ported from Hermes tools/delegate_tool.py).

The parent spawns child agents with a FRESH conversation, a restricted toolset, and their own
session lineage; it BLOCKS until they finish and only ever sees the child's summary result —
never its intermediate reasoning/tool calls. Children cannot recursively delegate or touch
shared memory/messaging.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# Tools a child agent may never have (no recursion, no shared-state side effects).
DELEGATE_BLOCKED_TOOLS = {"delegate_task", "remember", "save_skill"}


@dataclass
class SubAgentResult:
    goal: str
    summary: str
    ok: bool = True


def _child_system(goal: str, context: str) -> str:
    return (f"You are a focused sub-agent. Complete ONE goal and report a concise result.\n"
            f"GOAL: {goal}\n" + (f"CONTEXT: {context}\n" if context else "") +
            "Do the work, then give a short summary of what you found/did. Do not ask questions.")


def _spawn_one(parent, goal: str, context: str, max_tool_rounds: int) -> SubAgentResult:
    from edith.core.agent import Agent
    child = Agent(config=parent.config)
    try:
        # fresh, isolated session linked to the parent for lineage
        child.session = child.state.create_session(
            source="subagent", model=parent.config.model,
            parent_session_id=getattr(parent, "session", None) and parent.session.id)
        child.load_default_tools()
        for name in DELEGATE_BLOCKED_TOOLS:        # strip dangerous/shared tools
            child.tools.pop(name, None)
        child.ctx.system_prompt = _child_system(goal, context)
        child.history = []
        summary = child.step(goal, max_tool_rounds=max_tool_rounds)
        return SubAgentResult(goal=goal, summary=summary, ok=True)
    except Exception as e:
        return SubAgentResult(goal=goal, summary=f"sub-agent error: {type(e).__name__}: {e}", ok=False)
    finally:
        child.close()


def delegate(parent, goals: list[str] | str, *, context: str = "",
             max_tool_rounds: int = 6, max_workers: int = 4) -> list[SubAgentResult]:
    """Run one or more sub-agent goals (parallel if multiple). Parent blocks until all done."""
    if isinstance(goals, str):
        goals = [goals]
    if len(goals) == 1:
        return [_spawn_one(parent, goals[0], context, max_tool_rounds)]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(goals))) as ex:
        return list(ex.map(lambda g: _spawn_one(parent, g, context, max_tool_rounds), goals))


def register_delegate_tool(agent) -> None:
    """Expose `delegate_task` on the parent agent (summary-only return)."""
    def delegate_task(goal: str, context: str = "") -> str:
        results = delegate(agent, goal, context=context)
        return "\n\n".join(f"[sub-agent: {r.goal}]\n{r.summary}" for r in results)

    agent.register("delegate_task",
                   "Delegate a focused sub-task to an isolated child agent; returns its summary.",
                   {"type": "object",
                    "properties": {"goal": {"type": "string"}, "context": {"type": "string"}},
                    "required": ["goal"]},
                   delegate_task)
