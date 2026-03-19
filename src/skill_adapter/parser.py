import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from .models import SkillMetadata

_FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_KV_LINE_PATTERN = re.compile(r"^\s*(name|description|discrition)\s*:\s*(.+?)\s*$", re.IGNORECASE)


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def _extract_front_matter(text: str) -> Tuple[Dict[str, Any], str]:
    match = _FRONT_MATTER_PATTERN.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        return {}, text[match.end() :]
    return data, text[match.end() :]


def _extract_section_lines(body: str, section_title: str) -> List[str]:
    pattern = re.compile(
        rf"^##\s+{re.escape(section_title)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(body)
    if not match:
        return []
    section = match.group(1)
    lines: List[str] = []
    for line in section.splitlines():
        cleaned = line.strip().lstrip("-*0123456789. ").strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _extract_description(body: str) -> str:
    heading = _HEADING_PATTERN.search(body)
    start = heading.end() if heading else 0
    lines = body[start:].splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def _extract_name_description_from_body(body: str) -> Tuple[str, str]:
    name = ""
    description = ""
    for line in body.splitlines():
        match = _KV_LINE_PATTERN.match(line)
        if not match:
            continue
        key = match.group(1).lower().strip()
        value = match.group(2).strip()
        if key == "name" and value:
            name = value
        if key in {"description", "discrition"} and value:
            description = value
    return name, description


def parse_skill_metadata_from_file(skill_md_path: Path) -> SkillMetadata:
    text = skill_md_path.read_text(encoding="utf-8")
    front_matter, body = _extract_front_matter(text)
    body_name, body_description = _extract_name_description_from_body(body)

    default_id = skill_md_path.parent.name
    heading = _HEADING_PATTERN.search(body)
    default_name = heading.group(1).strip() if heading else default_id

    skill_id = str(front_matter.get("skill_id") or default_id).strip()
    front_description = front_matter.get("description") or front_matter.get("discrition")
    name = str(front_matter.get("name") or body_name or default_name).strip()
    description = str(front_description or body_description or _extract_description(body)).strip()

    use_when = _ensure_list(front_matter.get("use_when"))
    if not use_when:
        use_when = _extract_section_lines(body, "Use When")

    examples = _ensure_list(front_matter.get("examples"))
    if not examples:
        examples = _extract_section_lines(body, "Examples")

    return SkillMetadata(
        skill_id=skill_id,
        name=name or default_id,
        description=description,
        use_when=use_when,
        examples=examples,
        path=str(skill_md_path),
    )


def parse_skill_metadata(skill_dir: Path) -> SkillMetadata:
    skill_md_path = skill_dir / "SKILL.md"
    return parse_skill_metadata_from_file(skill_md_path)
