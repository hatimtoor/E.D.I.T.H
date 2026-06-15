"""Built-in agent tools — what lets E.D.I.T.H *do things* instead of only chatting.

`register_default_tools(agent)` wires the full toolset onto an Agent so the LLM can
call them: web fetch/search, memory, sandboxed shell, authorized security scan,
skill save/list, and workspace file read/write.
"""
from edith.tools.builtin import register_default_tools, ToolBox

__all__ = ["register_default_tools", "ToolBox"]
