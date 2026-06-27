"""Load an agent's skill file (skills/<name>/SKILL.md), splitting YAML frontmatter
from the instruction body so the frontmatter (name/description/tools) never leaks
into the LLM prompt.

Returns (metadata: dict, instruction: str). Agents with no frontmatter still work —
metadata comes back empty and the full file is the instruction.
"""
from pathlib import Path

_SKILLS_DIR = Path(__file__).parent.parent / "skills"


def load_skill(name: str) -> tuple[dict, str]:
    text = (_SKILLS_DIR / name / "SKILL.md").read_text()
    if text.lstrip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            import yaml  # provided transitively by google-adk
            meta = yaml.safe_load(parts[1]) or {}
            return meta, parts[2].lstrip("\n")
    return {}, text
