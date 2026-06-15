"""Skill system with progressive disclosure + immutability locks.

Fixes (from research):
  - Hermes overwriting hand-crafted skills -> `protect()` immutability lock
  - Token blowup on fresh sessions          -> 3-level progressive loading
"""
from edith.skills.registry import Skill, SkillRegistry, SkillLevel, ProtectedSkillError

__all__ = ["Skill", "SkillRegistry", "SkillLevel", "ProtectedSkillError"]
