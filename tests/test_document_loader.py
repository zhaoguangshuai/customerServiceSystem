import io

import pytest

from src.utils.document_loader import (
    chunk_text,
    load_document,
    load_markdown,
)


class TestChunkText:
    def test_short_text_single_chunk(self):
        text = "hello"
        assert chunk_text(text, chunk_size=500) == ["hello"]

    def test_exact_chunk_size(self):
        text = "a" * 500
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        text = "a" * 1100
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 3
        # First chunk: 0-500, second: 450-950, third: 900-1100
        assert len(chunks[0]) == 500
        assert len(chunks[1]) == 500
        assert len(chunks[2]) == 200

    def test_overlap_present(self):
        text = "abcdefghij" * 60  # 600 chars
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 2
        # Second chunk should start 50 chars before end of first
        overlap_start = 450
        assert chunks[1][:50] == text[overlap_start:overlap_start + 50]

    def test_empty_text(self):
        chunks = chunk_text("", chunk_size=500)
        assert chunks == [""]


class TestLoadDocument:
    def test_markdown_file(self):
        content = "# Hello\nThis is a test".encode("utf-8")
        result = load_document("test.md", content)
        assert "Hello" in result

    def test_txt_file(self):
        content = "plain text content".encode("utf-8")
        result = load_document("test.txt", content)
        assert result == "plain text content"

    def test_unsupported_extension(self):
        with pytest.raises(ValueError, match="不支持的文件类型"):
            load_document("test.xyz", b"content")

    def test_case_insensitive_extension(self):
        content = "test content".encode("utf-8")
        result = load_document("TEST.MD", content)
        assert result == "test content"


class TestLoadMarkdown:
    def test_utf8_content(self):
        content = "# 标题\n\n这是一段中文内容".encode("utf-8")
        result = load_markdown(content)
        assert "标题" in result
        assert "中文内容" in result

    def test_empty_content(self):
        result = load_markdown(b"")
        assert result == ""
