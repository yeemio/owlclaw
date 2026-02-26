"""Unit tests for document-driven skill generation."""

from pathlib import Path

from owlclaw.capabilities.skill_doc_extractor import SkillDocExtractor


def test_skill_doc_extractor_reads_supported_text_file(tmp_path: Path) -> None:
    source = tmp_path / "sop.md"
    source.write_text("# Inventory\n每天早上 9 点检查库存", encoding="utf-8")
    extractor = SkillDocExtractor(available_tools=["check-inventory"])
    text = extractor.read_document(source)
    assert "检查库存" in text


def test_skill_doc_extractor_rejects_unsupported_suffix(tmp_path: Path) -> None:
    source = tmp_path / "sop.pdf"
    source.write_text("x", encoding="utf-8")
    extractor = SkillDocExtractor()
    try:
        extractor.read_document(source)
    except ValueError as exc:
        assert "only markdown/text documents are supported" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_skill_doc_extractor_generates_skill_files(tmp_path: Path) -> None:
    source = tmp_path / "sop.txt"
    source.write_text(
        "# Daily Inventory Monitor\n每天早上 9 点检查库存并发送邮件提醒\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "skills"
    extractor = SkillDocExtractor(available_tools=["send-email", "check-inventory"])
    written = extractor.generate_from_document(source, output_dir)
    assert len(written) == 1
    generated = written[0]
    assert generated.exists()
    content = generated.read_text(encoding="utf-8")
    assert "name: daily-inventory-monitor" in content
    assert "## Suggested Tools" in content
