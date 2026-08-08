"""
Knowledge Chunker - Text Chunking and Embedding Service
========================================================

Handles intelligent text chunking for knowledge base documents.
Supports multiple chunking strategies and embedding generation.

Author: W3J Consulting
Date: 2026-02-11
Phase: 2 - Knowledge Base System
"""

import hashlib
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import tiktoken
from loguru import logger


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    index: int
    char_count: int
    token_count: int
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    start_char: int = 0
    end_char: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            "text": self.text,
            "index": self.index,
            "char_count": self.char_count,
            "token_count": self.token_count,
            "section_title": self.section_title,
            "page_number": self.page_number,
            "start_char": self.start_char,
            "end_char": self.end_char
        }


class KnowledgeChunker:
    """
    Intelligent text chunking for knowledge bases
    
    Features:
    - Multiple chunking strategies (fixed, semantic, sliding window)
    - Token-aware chunking (respects LLM context limits)
    - Section-aware chunking (preserves document structure)
    - Overlap for context preservation
    """

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 50,
        model: str = "gpt-3.5-turbo"
    ):
        """
        Initialize chunker
        
        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Tokens to overlap between chunks
            model: Model name for tokenization
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.model = model
        
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning(f"Model {model} not found, using cl100k_base encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))

    def chunk_text(
        self,
        content: str,
        strategy: str = "sliding_window",
        section_markers: Optional[List[str]] = None
    ) -> List[Chunk]:
        """
        Chunk text using specified strategy
        
        Args:
            content: Full text to chunk
            strategy: Chunking strategy (fixed, semantic, sliding_window, section)
            section_markers: List of regex patterns to identify sections
            
        Returns:
            List of Chunk objects
        """
        if not content or not content.strip():
            return []

        if strategy == "sliding_window":
            return self._sliding_window_chunk(content)
        elif strategy == "semantic":
            return self._semantic_chunk(content)
        elif strategy == "section" and section_markers:
            return self._section_aware_chunk(content, section_markers)
        else:
            return self._fixed_size_chunk(content)

    def _fixed_size_chunk(self, content: str) -> List[Chunk]:
        """Simple fixed-size chunking with overlap"""
        chunks = []
        tokens = self.encoding.encode(content)
        
        chunk_index = 0
        start = 0
        
        while start < len(tokens):
            # Extract chunk tokens
            end = min(start + self.max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Create chunk
            chunks.append(Chunk(
                text=chunk_text.strip(),
                index=chunk_index,
                char_count=len(chunk_text),
                token_count=len(chunk_tokens),
                start_char=start,
                end_char=end
            ))
            
            # Move to next chunk with overlap
            if end >= len(tokens):
                break
            start = end - self.overlap_tokens
            chunk_index += 1
        
        return chunks

    def _sliding_window_chunk(self, content: str) -> List[Chunk]:
        """
        Sliding window chunking with sentence boundary awareness
        
        Better than fixed-size as it respects sentence boundaries
        """
        chunks = []
        
        # Split into sentences
        sentences = self._split_into_sentences(content)
        
        current_chunk_sentences = []
        current_tokens = 0
        chunk_index = 0
        start_char = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # If adding this sentence exceeds limit
            if current_tokens + sentence_tokens > self.max_tokens and current_chunk_sentences:
                # Save current chunk
                chunk_text = " ".join(current_chunk_sentences)
                chunks.append(Chunk(
                    text=chunk_text.strip(),
                    index=chunk_index,
                    char_count=len(chunk_text),
                    token_count=current_tokens,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text)
                ))
                
                # Start new chunk with overlap (last sentence)
                overlap_sentences = current_chunk_sentences[-1:] if self.overlap_tokens > 0 else []
                current_chunk_sentences = overlap_sentences + [sentence]
                current_tokens = sum(self.count_tokens(s) for s in current_chunk_sentences)
                start_char += len(chunk_text) - len(overlap_sentences[0]) if overlap_sentences else 0
                chunk_index += 1
            else:
                current_chunk_sentences.append(sentence)
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            chunks.append(Chunk(
                text=chunk_text.strip(),
                index=chunk_index,
                char_count=len(chunk_text),
                token_count=current_tokens,
                start_char=start_char,
                end_char=start_char + len(chunk_text)
            ))
        
        return chunks

    def _semantic_chunk(self, content: str) -> List[Chunk]:
        """
        Semantic chunking based on paragraph boundaries and topic shifts
        
        Groups related paragraphs together until token limit reached
        """
        chunks = []
        
        # Split into paragraphs (double newline)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_chunk_paras = []
        current_tokens = 0
        chunk_index = 0
        start_char = 0
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # If paragraph alone exceeds limit, chunk it separately
            if para_tokens > self.max_tokens:
                # Save current chunk if exists
                if current_chunk_paras:
                    chunk_text = "\n\n".join(current_chunk_paras)
                    chunks.append(Chunk(
                        text=chunk_text.strip(),
                        index=chunk_index,
                        char_count=len(chunk_text),
                        token_count=current_tokens,
                        start_char=start_char,
                        end_char=start_char + len(chunk_text)
                    ))
                    chunk_index += 1
                    start_char += len(chunk_text)
                    current_chunk_paras = []
                    current_tokens = 0
                
                # Chunk the long paragraph using sentence-based chunking
                long_para_chunks = self._sliding_window_chunk(para)
                for lp_chunk in long_para_chunks:
                    lp_chunk.index = chunk_index
                    chunks.append(lp_chunk)
                    chunk_index += 1
                continue
            
            # If adding this paragraph exceeds limit
            if current_tokens + para_tokens > self.max_tokens and current_chunk_paras:
                # Save current chunk
                chunk_text = "\n\n".join(current_chunk_paras)
                chunks.append(Chunk(
                    text=chunk_text.strip(),
                    index=chunk_index,
                    char_count=len(chunk_text),
                    token_count=current_tokens,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text)
                ))
                chunk_index += 1
                start_char += len(chunk_text)
                current_chunk_paras = [para]
                current_tokens = para_tokens
            else:
                current_chunk_paras.append(para)
                current_tokens += para_tokens
        
        # Add final chunk
        if current_chunk_paras:
            chunk_text = "\n\n".join(current_chunk_paras)
            chunks.append(Chunk(
                text=chunk_text.strip(),
                index=chunk_index,
                char_count=len(chunk_text),
                token_count=current_tokens,
                start_char=start_char,
                end_char=start_char + len(chunk_text)
            ))
        
        return chunks

    def _section_aware_chunk(self, content: str, section_markers: List[str]) -> List[Chunk]:
        """
        Section-aware chunking that preserves document structure
        
        Args:
            content: Document content
            section_markers: Regex patterns for section headers (e.g., ["^# ", "^## "])
        """
        chunks = []
        
        # Identify sections
        sections = self._identify_sections(content, section_markers)
        
        chunk_index = 0
        for section_title, section_text in sections:
            # Chunk each section
            section_chunks = self._semantic_chunk(section_text)
            
            for sc in section_chunks:
                sc.index = chunk_index
                sc.section_title = section_title
                chunks.append(sc)
                chunk_index += 1
        
        return chunks

    def _identify_sections(self, content: str, section_markers: List[str]) -> List[Tuple[str, str]]:
        """Identify document sections based on markers"""
        sections = []
        current_title = "Introduction"
        current_text = []
        
        lines = content.split('\n')
        
        for line in lines:
            # Check if line is a section header
            is_header = False
            for marker in section_markers:
                if re.match(marker, line):
                    # Save previous section
                    if current_text:
                        sections.append((current_title, '\n'.join(current_text)))
                    
                    # Start new section
                    current_title = line.strip('# ').strip()
                    current_text = []
                    is_header = True
                    break
            
            if not is_header:
                current_text.append(line)
        
        # Add final section
        if current_text:
            sections.append((current_title, '\n'.join(current_text)))
        
        return sections

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting (can be enhanced with NLTK for better accuracy)
        sentence_endings = re.compile(r'([.!?])\s+')
        sentences = sentence_endings.split(text)
        
        # Rejoin sentence with its ending punctuation
        result = []
        for i in range(0, len(sentences) - 1, 2):
            result.append(sentences[i] + sentences[i + 1])
        
        # Add last sentence if no ending punctuation
        if len(sentences) % 2 == 1:
            result.append(sentences[-1])
        
        return [s.strip() for s in result if s.strip()]

    def compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content for change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def chunk_document(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        strategy: str = "semantic"
    ) -> Dict:
        """
        Chunk a complete document with metadata
        
        Args:
            content: Document content
            metadata: Optional metadata (title, category, etc.)
            strategy: Chunking strategy
            
        Returns:
            Dictionary with chunks and document metadata
        """
        metadata = metadata or {}
        
        # Detect section markers from content
        section_markers = self._detect_section_markers(content)
        
        # Chunk based on strategy
        if section_markers and strategy == "section":
            chunks = self._section_aware_chunk(content, section_markers)
        else:
            chunks = self.chunk_text(content, strategy=strategy)
        
        # Compute content hash
        content_hash = self.compute_content_hash(content)
        
        return {
            "content_hash": content_hash,
            "chunk_count": len(chunks),
            "chunks": [chunk.to_dict() for chunk in chunks],
            "total_tokens": sum(c.token_count for c in chunks),
            "total_chars": len(content),
            "metadata": metadata
        }

    def _detect_section_markers(self, content: str) -> List[str]:
        """Auto-detect section markers in document"""
        markers = []
        
        # Check for markdown headers
        if re.search(r'^#{1,6}\s+', content, re.MULTILINE):
            markers.append(r'^#{1,6}\s+')
        
        # Check for numbered sections (1. 2. etc.)
        if re.search(r'^\d+\.\s+[A-Z]', content, re.MULTILINE):
            markers.append(r'^\d+\.\s+[A-Z]')
        
        # Check for ALL CAPS titles
        if re.search(r'^[A-Z\s]{3,}$', content, re.MULTILINE):
            markers.append(r'^[A-Z\s]{3,}$')
        
        return markers


# Example usage and testing
if __name__ == "__main__":
    # Test chunker
    chunker = KnowledgeChunker(max_tokens=200, overlap_tokens=20)
    
    test_content = """
    # Introduction
    This is a sample document with multiple sections. It will be used to test the chunking functionality.
    
    The chunker should intelligently split this content while preserving context and structure.
    
    # First Section
    This section contains information about our products. We offer a wide range of services including
    consulting, development, and support. Our team has over 10 years of experience.
    
    ## Subsection 1.1
    More detailed information about specific products. This includes features, pricing, and availability.
    
    # Second Section
    Contact information and support details. You can reach us via email, phone, or WhatsApp.
    """
    
    result = chunker.chunk_document(test_content, strategy="section")
    
    print(f"Document chunked into {result['chunk_count']} chunks")
    print(f"Total tokens: {result['total_tokens']}")
    print(f"Content hash: {result['content_hash']}")
    
    for chunk in result['chunks'][:2]:  # Show first 2 chunks
        print(f"\nChunk {chunk['index']}:")
        print(f"  Section: {chunk['section_title']}")
        print(f"  Tokens: {chunk['token_count']}")
        print(f"  Text preview: {chunk['text'][:100]}...")
