"""
Public procedural-generation entry points.

Keep this module as the stable import path for generator callers. More advanced
stellar generation can replace the internals later as long as generate_system()
continues to return a SystemRecord or v0.2-compatible mapping.
"""

from __future__ import annotations

from .procedural import generate_system


__all__ = ["generate_system"]
