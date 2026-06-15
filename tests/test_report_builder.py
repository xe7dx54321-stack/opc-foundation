"""Test Markdown report builder."""
from opc_foundation.reports.markdown_builder import MarkdownBuilder


def test_heading():
    md = MarkdownBuilder().heading(1, "Title").build()
    assert "# Title" in md


def test_bullet_list():
    md = MarkdownBuilder().bullet_list(["a", "b", "c"]).build()
    assert "- a" in md
    assert "- b" in md


def test_table():
    md = MarkdownBuilder().table(["Col1", "Col2"], [["a", "b"], ["c", "d"]]).build()
    assert "| Col1 | Col2 |" in md
    assert "| a | b |" in md


def test_code_block():
    md = MarkdownBuilder().code_block("print('hi')", language="python").build()
    assert "```python" in md
    assert "print('hi')" in md


def test_write_report(tmp_path):
    p = tmp_path / "report.md"
    builder = MarkdownBuilder()
    builder.heading(1, "Test Report").paragraph("Summary here.").bullet_list(["item1"])
    builder.write_report(p)
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "Test Report" in content
    assert "item1" in content
