"""Skill system with progressive disclosure + immutability locks.

Fixes: Hermes overwriting hand-crafted skills -> `protect()` edit-lock;
token blowup on fresh sessions -> 3-level progressive loading.
"""
from edith.skills.registry import Skill, SkillRegistry, SkillLevel, ProtectedSkillError

__all__ = ["Skill", "SkillRegistry", "SkillLevel", "ProtectedSkillError"]
