import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.ports.llm_provider import LLMProvider
from src.application.services.chunking_service import (
    ChunkingService,
    ChunkingStrategy,
    CodeChunkingStrategy,
    DocumentChunkingStrategy,
    DefaultChunkingStrategy
)


class TestChunkingService:
    """Test cases for the document chunking service."""

    @pytest.fixture
    def llm_provider_mock(self):
        """Mock for the LLM provider."""
        provider = Mock(spec=LLMProvider)
        # Default embedding for tests
        provider.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        return provider

    @pytest.fixture
    def sample_python_file(self):
        """Sample Python file content for testing."""
        return """import os
import sys

# A simple Python class
class ExampleClass:
    \"\"\"
    This is an example class for testing chunking.
    \"\"\"

    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2

    def method1(self):
        \"\"\"A simple method\"\"\"
        return self.param1 + self.param2

    def method2(self):
        \"\"\"Another method\"\"\"
        return self.param1 * self.param2

# A standalone function
def standalone_function(arg1, arg2):
    \"\"\"
    This is a standalone function for testing.

    Args:
        arg1: First argument
        arg2: Second argument

    Returns:
        Sum of arguments
    \"\"\"
    return arg1 + arg2

if __name__ == "__main__":
    example = ExampleClass(1, 2)
    result = example.method1()
    print(result)
"""

    @pytest.fixture
    def sample_markdown_file(self):
        """Sample Markdown file content for testing."""
        return """# Sample Document

## Introduction

This is a sample document for testing the chunking service.
The document has multiple sections and paragraphs.

## Section 1

This is the first section of the document.
It contains multiple paragraphs.

This is another paragraph in section 1.
It should be considered as a separate chunk.

## Section 2

This is the second section of the document.
It also has multiple paragraphs.

### Subsection 2.1

This is a subsection within section 2.
Hierarchical structure should be preserved in the chunks.

## Conclusion

This is the conclusion of the document.
"""

    @pytest.fixture
    def chunking_service(self, llm_provider_mock):
        """Create a chunking service for testing."""
        return ChunkingService(llm_provider=llm_provider_mock)

    def test_chunking_service_initialization(self, chunking_service):
        """Test chunking service initialization."""
        assert chunking_service is not None
        assert hasattr(chunking_service, 'chunk_document')
        assert hasattr(chunking_service, 'get_strategy_for_content_type')

    def test_document_chunking_service(self, chunking_service,
                                       sample_python_file):
        """Test general chunking functionality."""
        # Arrange
        document = ContextItem(
            id=str(uuid4()),
            source="test_file.py",
            content=sample_python_file,
            content_type=ContentType.PYTHON
        )

        # Act
        chunks = chunking_service.chunk_document(document)

        # Assert
        assert len(chunks) > 0  # Should create at least some chunks

        # Check that all chunks have the parent document ID
        for chunk in chunks:
            assert chunk.parent_id == document.id
            assert chunk.is_chunk is True
            assert chunk.container_id == document.container_id
            assert chunk.content_type == document.content_type
            assert len(chunk.content) < len(document.content)
            assert chunk.source.startswith(document.source)

        # Verify chunk metadata
        for chunk in chunks:
            assert "line_start" in chunk.chunk_metadata
            assert "line_end" in chunk.chunk_metadata

    def test_code_file_chunking(self, chunking_service, sample_python_file):
        """Test code file specific chunking."""
        # Arrange
        document = ContextItem(
            id=str(uuid4()),
            source="test_file.py",
            content=sample_python_file,
            content_type=ContentType.PYTHON
        )

        # Act
        chunks = chunking_service.chunk_document(document)

        # Assert - Check for specific code structures

        # Find class chunk
        class_chunks = [c for c in chunks if
                        c.chunk_type == "class"]
        assert len(class_chunks) > 0
        class_chunk = class_chunks[0]
        assert "ExampleClass" in class_chunk.content
        assert "class ExampleClass" in class_chunk.content

        # Find method chunks
        method_chunks = [c for c in chunks if
                         c.chunk_type == "method"]
        assert len(method_chunks) >= 2  # Should have at least 2 methods

        # Find function chunk
        function_chunks = [c for c in chunks if
                           c.chunk_type == "function"]
        assert len(function_chunks) > 0
        function_chunk = function_chunks[0]
        assert "standalone_function" in function_chunk.content
        assert "def standalone_function" in function_chunk.content

        # Verify source paths include parent path and chunk identifier
        for chunk in chunks:
            if chunk.chunk_type == "class":
                assert ":ExampleClass" in chunk.source
            elif chunk.chunk_type == "method":
                assert "ExampleClass." in chunk.source
            elif chunk.chunk_type == "function":
                assert ":standalone_function" in chunk.source

    def test_document_file_chunking(self, chunking_service,
                                    sample_markdown_file):
        """Test document file chunking."""
        # Arrange
        document = ContextItem(
            id=str(uuid4()),
            source="test_file.md",
            content=sample_markdown_file,
            content_type=ContentType.MARKDOWN
        )

        # Act
        chunks = chunking_service.chunk_document(document)

        # Assert - Check for document structure

        # Should have chunks for each main section
        section_chunks = [c for c in chunks if
                          c.chunk_type == "section"]
        assert len(
            section_chunks) >= 3  # Introduction, Section 1, Section 2, Conclusion

        # Check for subsection
        subsection_chunks = [c for c in chunks if
                             c.chunk_type == "subsection"]
        assert len(subsection_chunks) > 0
        subsection_chunk = subsection_chunks[0]
        assert "Subsection 2.1" in subsection_chunk.content

        # Check for paragraphs
        paragraph_chunks = [c for c in chunks if
                            c.chunk_type == "paragraph"]
        assert len(paragraph_chunks) > 0

        # Verify source paths include parent path and chunk identifier
        for chunk in chunks:
            chunk_type = chunk.chunk_type
            if chunk_type == "section":
                assert ":" in chunk.source
            elif chunk_type == "subsection":
                assert ":" in chunk.source
            elif chunk_type == "paragraph":
                assert ":" in chunk.source

    def test_unsupported_file_chunking(self, chunking_service):
        """Test chunking of unsupported file types."""
        # Arrange
        content = "This is a simple text file with no special structure."
        document = ContextItem(
            id=str(uuid4()),
            source="test_file.txt",
            content=content,
            content_type=ContentType.TEXT
        )

        # Act
        chunks = chunking_service.chunk_document(document)

        # Assert - Should fall back to simple chunking
        assert len(chunks) > 0

        # For simple text, we might just get one chunk or a few based on size
        for chunk in chunks:
            assert chunk.parent_id == document.id
            assert chunk.is_chunk is True
            assert chunk.chunk_type == "paragraph"

    def test_chunk_embedding_generation(self, chunking_service,
                                        llm_provider_mock, sample_python_file):
        """Test embedding generation for chunks."""
        # Arrange
        document = ContextItem(
            id=str(uuid4()),
            source="test_file.py",
            content=sample_python_file,
            content_type=ContentType.PYTHON
        )

        # Act
        chunks = chunking_service.chunk_document(document)

        # Assert
        # Verify that embeddings were generated for each chunk
        assert llm_provider_mock.generate_embedding.call_count >= len(chunks)

        # Check that all chunks have embeddings
        for chunk in chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) > 0

    def test_very_small_document_chunking(self, chunking_service):
        """Test chunking of a very small document."""
        # Arrange
        document = ContextItem(
            id=str(uuid4()),
            source="small_file.py",
            content="print('Hello, World!')",
            content_type=ContentType.PYTHON
        )

        # Act
        chunks = chunking_service.chunk_document(document)

        # Assert - For very small documents, might not chunk at all
        if len(chunks) > 0:
            # If chunks are created, they should be properly formed
            for chunk in chunks:
                assert chunk.parent_id == document.id
                assert chunk.is_chunk is True