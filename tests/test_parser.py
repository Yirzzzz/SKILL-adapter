from pathlib import Path

from skill_adapter.parser import parse_skill_metadata, parse_skill_metadata_from_file
from test_utils import make_case_dir


def test_parser_extracts_metadata_with_front_matter() -> None:
    skill_dir = make_case_dir() / "paper-summary"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: Paper Summary
description: Summarize papers
use_when:
  - summarize paper
examples:
  - 请总结这篇论文
---
# Paper Summary
""",
        encoding="utf-8",
    )

    meta = parse_skill_metadata(skill_dir)
    assert meta.skill_id == "paper-summary"
    assert meta.name == "Paper Summary"
    assert meta.description == "Summarize papers"
    assert meta.retrieval_text == "Paper Summary\nSummarize papers"
    assert meta.use_when == ["summarize paper"]
    assert meta.examples == ["请总结这篇论文"]


def test_parser_extracts_metadata_without_front_matter() -> None:
    skill_dir = make_case_dir() / "web-summary"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """# Web Summary
Summarize web pages quickly.

## Use When
- summarize webpage

## Examples
- 总结这个网页
""",
        encoding="utf-8",
    )

    meta = parse_skill_metadata(skill_dir)
    assert meta.skill_id == "web-summary"
    assert meta.name == "Web Summary"
    assert "Summarize web pages quickly." in meta.description
    assert meta.retrieval_text.startswith("Web Summary\n")
    assert "summarize webpage" in meta.use_when
    assert "总结这个网页" in meta.examples


def test_parser_supports_discrition_key() -> None:
    skill_dir = make_case_dir() / "math"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: no-math
discrition: 拒绝回答数学计算和比较大小问题
---
""",
        encoding="utf-8",
    )

    meta = parse_skill_metadata(skill_dir)
    assert meta.name == "no-math"
    assert meta.description == "拒绝回答数学计算和比较大小问题"


def test_parser_uses_parent_dir_as_default_skill_id_for_any_md_name() -> None:
    skill_dir = make_case_dir() / "math-skill"
    skill_dir.mkdir()
    md = skill_dir / "whatever-name.md"
    md.write_text(
        """name: no-math
discrition: 拒绝回答数学题
""",
        encoding="utf-8",
    )

    meta = parse_skill_metadata_from_file(md)
    assert meta.skill_id == "math-skill"
