"""
Service for chunking documents into smaller, semantically meaningful units.

This module implements strategies for breaking down documents into chunks based on their content type,
maintaining parent-child relationships between original documents and their chunks.
"""
import re
import abc
import logging
from uuid import uuid4
from typing import List, Dict, Any, Optional, Tuple

from src.domain.entities.context_item import ContextItem, ContentType
from src.domain.ports.llm_provider import LLMProvider


class ChunkingStrategy(abc.ABC):
    """Base abstract class for document chunking strategies."""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the chunking strategy.

        Args:
            llm_provider: LLM provider for generating embeddings
        """
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def chunk_document(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk the document into smaller units.

        Args:
            document: The document to chunk

        Returns:
            List of context items representing chunks of the document
        """
        pass

    def _create_chunk(
            self,
            parent: ContextItem,
            content: str,
            chunk_type: str,
            chunk_identifier: str,
            metadata: Dict[str, Any]
    ) -> ContextItem:
        """
        Create a chunk context item from a parent document.

        Args:
            parent: Parent context item
            content: Content of the chunk
            chunk_type: Type of chunk (e.g., function, method, section)
            chunk_identifier: Identifier for this chunk (e.g., function name)
            metadata: Additional metadata for the chunk

        Returns:
            New context item representing the chunk
        """
        # Create source path that includes parent path and chunk identifier
        source = f"{parent.source}:{chunk_identifier}"

        # Create the chunk
        chunk = ContextItem(
            id=str(uuid4()),
            source=source,
            content=content,
            content_type=parent.content_type,
            metadata=parent.metadata.copy(),  # Copy parent metadata
            container_id=parent.container_id,
            parent_id=parent.id,
            is_chunk=True,
            chunk_type=chunk_type,
            chunk_metadata=metadata
        )

        # Generate embedding for the chunk
        try:
            chunk.embedding = self.llm_provider.generate_embedding(content)
        except Exception as e:
            self.logger.warning(
                f"Failed to generate embedding for chunk {source}: {str(e)}")

        return chunk


class CodeChunkingStrategy(ChunkingStrategy):
    """Strategy for chunking code files."""

    def chunk_document(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a code document into classes, methods, and functions.

        Args:
            document: The code document to chunk

        Returns:
            List of context items representing code chunks
        """
        chunks = []
        content = document.content

        if not content.strip():
            return []

        # For Python files, use regex-based chunking
        if document.content_type == ContentType.PYTHON:
            chunks.extend(self._chunk_python_file(document))
        # For JavaScript/TypeScript files, use different regexes
        elif document.content_type in [ContentType.JAVASCRIPT]:
            chunks.extend(self._chunk_javascript_file(document))
        # For other code files, fall back to simple chunking
        else:
            chunks.extend(self._chunk_generic_code_file(document))

        return chunks

    def _chunk_python_file(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a Python file into classes, methods, and functions.

        Args:
            document: The Python document to chunk

        Returns:
            List of context items representing Python code chunks
        """
        chunks = []
        content = document.content
        lines = content.split("\n")

        # Find classes
        class_pattern = r"^class\s+(\w+)(?:\(.*\))?:"
        class_matches = []

        for i, line in enumerate(lines):
            match = re.match(class_pattern, line)
            if match:
                class_name = match.group(1)
                class_matches.append((i, class_name))

        # Extract class content and create chunks
        for i, (class_line, class_name) in enumerate(class_matches):
            # Determine end of class
            if i < len(class_matches) - 1:
                end_line = class_matches[i + 1][0]
            else:
                end_line = len(lines)

            # Extract class content
            class_content = "\n".join(lines[class_line:end_line])

            # Create class chunk
            class_chunk = self._create_chunk(
                parent=document,
                content=class_content,
                chunk_type="class",
                chunk_identifier=class_name,
                metadata={
                    "class_name": class_name,
                    "line_start": class_line + 1,
                    "line_end": end_line,
                }
            )
            chunks.append(class_chunk)

            # Find methods within the class
            method_pattern = r"^\s+def\s+(\w+)\("
            method_matches = []

            for j, line in enumerate(lines[class_line:end_line], class_line):
                match = re.match(method_pattern, line)
                if match:
                    method_name = match.group(1)
                    method_matches.append((j, method_name))

            # Extract method content and create chunks
            for j, (method_line, method_name) in enumerate(method_matches):
                # Determine end of method
                if j < len(method_matches) - 1:
                    method_end_line = method_matches[j + 1][0]
                else:
                    method_end_line = end_line

                # Skip if method is just one line
                if method_end_line - method_line <= 1:
                    continue

                # Extract method content
                method_content = "\n".join(lines[method_line:method_end_line])

                # Create method chunk
                method_chunk = self._create_chunk(
                    parent=document,
                    content=method_content,
                    chunk_type="method",
                    chunk_identifier=f"{class_name}.{method_name}",
                    metadata={
                        "class_name": class_name,
                        "method_name": method_name,
                        "line_start": method_line + 1,
                        "line_end": method_end_line,
                    }
                )
                chunks.append(method_chunk)

        # Find standalone functions
        function_pattern = r"^def\s+(\w+)\("
        function_matches = []

        for i, line in enumerate(lines):
            match = re.match(function_pattern, line)
            if match:
                function_name = match.group(1)
                function_matches.append((i, function_name))

        # Extract function content and create chunks
        for i, (function_line, function_name) in enumerate(function_matches):
            # Determine end of function
            if i < len(function_matches) - 1:
                end_line = function_matches[i + 1][0]
            else:
                end_line = len(lines)

            # Find next non-indented line
            for j in range(function_line + 1, len(lines)):
                if j >= len(lines):
                    end_line = len(lines)
                    break

                line = lines[j]
                if line.strip() and not line.startswith(
                        " ") and not line.startswith("\t"):
                    end_line = j
                    break

            # Skip if function is just one line
            if end_line - function_line <= 1:
                continue

            # Extract function content
            function_content = "\n".join(lines[function_line:end_line])

            # Create function chunk
            function_chunk = self._create_chunk(
                parent=document,
                content=function_content,
                chunk_type="function",
                chunk_identifier=function_name,
                metadata={
                    "function_name": function_name,
                    "line_start": function_line + 1,
                    "line_end": end_line,
                }
            )
            chunks.append(function_chunk)

        return chunks

    def _chunk_javascript_file(self, document: ContextItem) -> List[
        ContextItem]:
        """
        Chunk a JavaScript file into classes, methods, and functions.

        Args:
            document: The JavaScript document to chunk

        Returns:
            List of context items representing JavaScript code chunks
        """
        # Implementation would be similar to Python but with JavaScript patterns
        # For brevity, falling back to generic code chunking
        return self._chunk_generic_code_file(document)

    def _chunk_generic_code_file(self, document: ContextItem) -> List[
        ContextItem]:
        """
        Chunk a generic code file by logical blocks.

        Args:
            document: The code document to chunk

        Returns:
            List of context items representing code chunks
        """
        chunks = []
        content = document.content
        lines = content.split("\n")

        # Simple chunking by empty lines
        chunk_lines = []
        chunk_start = 0

        for i, line in enumerate(lines):
            chunk_lines.append(line)

            # End of chunk on empty line or large chunk size
            if (not line.strip() and len(chunk_lines) > 5) or len(
                    chunk_lines) > 50:
                # Create chunk if it has meaningful content
                if any(l.strip() for l in chunk_lines):
                    chunk_content = "\n".join(chunk_lines)
                    chunk = self._create_chunk(
                        parent=document,
                        content=chunk_content,
                        chunk_type="code_block",
                        chunk_identifier=f"block_{chunk_start}",
                        metadata={
                            "line_start": chunk_start + 1,
                            "line_end": i + 1,
                        }
                    )
                    chunks.append(chunk)

                # Reset for next chunk
                chunk_lines = []
                chunk_start = i + 1

        # Add final chunk if any
        if chunk_lines and any(l.strip() for l in chunk_lines):
            chunk_content = "\n".join(chunk_lines)
            chunk = self._create_chunk(
                parent=document,
                content=chunk_content,
                chunk_type="code_block",
                chunk_identifier=f"block_{chunk_start}",
                metadata={
                    "line_start": chunk_start + 1,
                    "line_end": len(lines),
                }
            )
            chunks.append(chunk)

        return chunks


class DocumentChunkingStrategy(ChunkingStrategy):
    """Strategy for chunking documentation files like Markdown."""

    def chunk_document(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a documentation document into sections and paragraphs.

        Args:
            document: The document to chunk

        Returns:
            List of context items representing document chunks
        """
        chunks = []
        content = document.content

        if not content.strip():
            return []

        # For Markdown files, use header-based chunking
        if document.content_type == ContentType.MARKDOWN:
            chunks.extend(self._chunk_markdown_file(document))
        # For text files, use paragraph-based chunking
        elif document.content_type == ContentType.TEXT:
            chunks.extend(self._chunk_text_file(document))
        # For other document types, fall back to simple chunking
        else:
            chunks.extend(self._chunk_generic_document(document))

        return chunks

    def _chunk_markdown_file(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a Markdown file into sections and paragraphs.

        Args:
            document: The Markdown document to chunk

        Returns:
            List of context items representing Markdown chunks
        """
        chunks = []
        content = document.content
        lines = content.split("\n")

        # Find headers
        header_pattern = r"^(#+)\s+(.+)$"
        header_matches = []

        for i, line in enumerate(lines):
            match = re.match(header_pattern, line)
            if match:
                level = len(match.group(1))  # Number of # characters
                title = match.group(2).strip()
                header_matches.append((i, level, title))

        # Extract section content and create chunks
        for i, (header_line, level, title) in enumerate(header_matches):
            # Determine end of section
            if i < len(header_matches) - 1:
                next_header = header_matches[i + 1]
                next_level = next_header[1]

                # Only end section at same or higher level header
                if next_level <= level:
                    end_line = next_header[0]
                else:
                    # Find next header at same or higher level
                    end_line = None
                    for j in range(i + 1, len(header_matches)):
                        if header_matches[j][1] <= level:
                            end_line = header_matches[j][0]
                            break

                    if end_line is None:
                        end_line = len(lines)
            else:
                end_line = len(lines)

            # Extract section content
            section_content = "\n".join(lines[header_line:end_line])

            # Determine chunk type based on header level
            chunk_type = "section" if level <= 2 else "subsection"

            # Create section chunk
            section_chunk = self._create_chunk(
                parent=document,
                content=section_content,
                chunk_type=chunk_type,
                chunk_identifier=title.lower().replace(" ", "_"),
                metadata={
                    "title": title,
                    "level": level,
                    "line_start": header_line + 1,
                    "line_end": end_line,
                }
            )
            chunks.append(section_chunk)

            # Find paragraphs within the section
            paragraph_lines = []
            paragraph_start = header_line + 1

            for j in range(header_line + 1, end_line):
                line = lines[j] if j < len(lines) else ""

                # Empty line indicates paragraph break
                if not line.strip():
                    if paragraph_lines:
                        paragraph_content = "\n".join(paragraph_lines)

                        # Skip very short paragraphs (likely just whitespace after headers)
                        if len(paragraph_content) < 20:
                            paragraph_lines = []
                            paragraph_start = j + 1
                            continue

                        paragraph_chunk = self._create_chunk(
                            parent=document,
                            content=paragraph_content,
                            chunk_type="paragraph",
                            chunk_identifier=f"{title.lower().replace(' ', '_')}_p{paragraph_start}",
                            metadata={
                                "section_title": title,
                                "line_start": paragraph_start + 1,
                                "line_end": j,
                            }
                        )
                        chunks.append(paragraph_chunk)
                        paragraph_lines = []
                        paragraph_start = j + 1
                else:
                    paragraph_lines.append(line)

            # Add final paragraph if any
            if paragraph_lines:
                paragraph_content = "\n".join(paragraph_lines)

                # Skip very short paragraphs
                if len(paragraph_content) >= 20:
                    paragraph_chunk = self._create_chunk(
                        parent=document,
                        content=paragraph_content,
                        chunk_type="paragraph",
                        chunk_identifier=f"{title.lower().replace(' ', '_')}_p{paragraph_start}",
                        metadata={
                            "section_title": title,
                            "line_start": paragraph_start + 1,
                            "line_end": end_line,
                        }
                    )
                    chunks.append(paragraph_chunk)

        return chunks

    def _chunk_text_file(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a text file into paragraphs.

        Args:
            document: The text document to chunk

        Returns:
            List of context items representing text chunks
        """
        chunks = []
        content = document.content

        # Split by blank lines to find paragraphs
        paragraphs = re.split(r"\n\s*\n", content)

        # Create chunks for each paragraph
        line_count = 0
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Calculate line position
            line_start = line_count + 1
            line_count += paragraph.count(
                "\n") + 2  # +2 for the blank line separator

            # Create paragraph chunk
            paragraph_chunk = self._create_chunk(
                parent=document,
                content=paragraph,
                chunk_type="paragraph",
                chunk_identifier=f"p{i + 1}",
                metadata={
                    "paragraph_index": i + 1,
                    "line_start": line_start,
                    "line_end": line_start + paragraph.count("\n"),
                }
            )
            chunks.append(paragraph_chunk)

        return chunks

    def _chunk_generic_document(self, document: ContextItem) -> List[
        ContextItem]:
        """
        Chunk a generic document file.

        Args:
            document: The document to chunk

        Returns:
            List of context items representing document chunks
        """
        # For generic documents, simply split by blank lines or a maximum size
        return self._chunk_text_file(document)


class DefaultChunkingStrategy(ChunkingStrategy):
    """Default strategy for chunking unsupported file types."""

    def chunk_document(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a document using a simple size-based approach.

        Args:
            document: The document to chunk

        Returns:
            List of context items representing chunks
        """
        chunks = []
        content = document.content

        if not content.strip():
            return []

        # Simple chunking by roughly equal sizes
        max_chunk_size = 1000  # characters

        if len(content) <= max_chunk_size:
            # Document small enough to be a single chunk
            chunk = self._create_chunk(
                parent=document,
                content=content,
                chunk_type="text",
                chunk_identifier="full",
                metadata={
                    "line_start": 1,
                    "line_end": content.count("\n") + 1,
                }
            )
            chunks.append(chunk)
        else:
            # Split into roughly equal chunks
            lines = content.split("\n")
            chunk_lines = []
            chunk_start = 0
            current_size = 0

            for i, line in enumerate(lines):
                line_size = len(line) + 1  # +1 for newline
                current_size += line_size
                chunk_lines.append(line)

                if current_size >= max_chunk_size:
                    # Create chunk
                    chunk_content = "\n".join(chunk_lines)
                    chunk = self._create_chunk(
                        parent=document,
                        content=chunk_content,
                        chunk_type="text",
                        chunk_identifier=f"chunk_{chunk_start}",
                        metadata={
                            "line_start": chunk_start + 1,
                            "line_end": i + 1,
                        }
                    )
                    chunks.append(chunk)

                    # Reset for next chunk
                    chunk_lines = []
                    chunk_start = i + 1
                    current_size = 0

            # Add final chunk if any
            if chunk_lines:
                chunk_content = "\n".join(chunk_lines)
                chunk = self._create_chunk(
                    parent=document,
                    content=chunk_content,
                    chunk_type="text",
                    chunk_identifier=f"chunk_{chunk_start}",
                    metadata={
                        "line_start": chunk_start + 1,
                        "line_end": len(lines),
                    }
                )
                chunks.append(chunk)

        return chunks


class ChunkingService:
    """Service for chunking documents into smaller, semantically meaningful units."""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize the chunking service.

        Args:
            llm_provider: LLM provider for generating embeddings
        """
        self.llm_provider = llm_provider
        self.logger = logging.getLogger(__name__)

        # Initialize chunking strategies
        self.code_chunking_strategy = CodeChunkingStrategy(llm_provider)
        self.document_chunking_strategy = DocumentChunkingStrategy(llm_provider)
        self.default_chunking_strategy = DefaultChunkingStrategy(llm_provider)

    def chunk_document(self, document: ContextItem) -> List[ContextItem]:
        """
        Chunk a document into smaller, semantically meaningful units.

        Args:
            document: The document to chunk

        Returns:
            List of context items representing chunks of the document
        """
        if not document.content:
            return []

        # Get the appropriate chunking strategy for the document type
        strategy = self.get_strategy_for_content_type(document.content_type)

        # Chunk the document
        chunks = strategy.chunk_document(document)

        self.logger.info(
            f"Chunked document {document.source} into {len(chunks)} chunks")
        return chunks

    def get_strategy_for_content_type(self,
                                      content_type: ContentType) -> ChunkingStrategy:
        """
        Get the appropriate chunking strategy for a content type.

        Args:
            content_type: Type of content to chunk

        Returns:
            Appropriate chunking strategy
        """
        # Code file types
        if content_type in [ContentType.PYTHON, ContentType.JAVASCRIPT]:
            return self.code_chunking_strategy

        # Document file types
        elif content_type in [ContentType.MARKDOWN, ContentType.TEXT]:
            return self.document_chunking_strategy

        # Default for unsupported types
        else:
            return self.default_chunking_strategy