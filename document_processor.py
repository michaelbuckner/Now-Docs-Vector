"""Document processing utilities for markdown chunking and parsing"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib

from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain.schema import Document
from tqdm import tqdm
import tiktoken


@dataclass
class ChunkMetadata:
    """Metadata for document chunks"""
    chunk_id: str
    source: str
    chunk_index: int
    total_chunks: int
    headers: Dict[str, str]
    start_char: int
    end_char: int
    word_count: int
    token_count: Optional[int] = None


class DocumentProcessor:
    """Process and chunk markdown documents for vectorization"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = None
        
    def count_tokens(self, text: str, model: str = "cl100k_base") -> int:
        """Count tokens in text using tiktoken"""
        if self.tokenizer is None:
            self.tokenizer = tiktoken.get_encoding(model)
        return len(self.tokenizer.encode(text))
    
    def generate_chunk_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """Generate a unique ID for a chunk based on content and metadata"""
        hash_input = f"{content}{metadata.get('source', '')}{metadata.get('chunk_index', '')}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def extract_headers_from_markdown(self, content: str) -> List[Document]:
        """Extract headers and structure from markdown content"""
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )
        
        return markdown_splitter.split_text(content)
    
    def chunk_markdown(self, file_path: Path) -> List[Document]:
        """
        Chunk a markdown file into smaller pieces while preserving structure
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            List of Document objects with content and metadata
        """
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Processing {file_path.name} ({len(content):,} characters)...")
        
        # First, split by headers to maintain document structure
        header_chunks = self.extract_headers_from_markdown(content)
        
        # Then, further split large sections using RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )
        
        all_chunks = []
        total_header_chunks = len(header_chunks)
        
        for idx, header_chunk in enumerate(tqdm(header_chunks, desc="Processing sections")):
            # Get the headers from metadata
            headers = header_chunk.metadata
            
            # If the section is still too large, split it further
            if len(header_chunk.page_content) > self.chunk_size:
                sub_chunks = text_splitter.split_text(header_chunk.page_content)
                
                for sub_idx, sub_chunk_text in enumerate(sub_chunks):
                    # Create metadata for this chunk
                    metadata = {
                        "source": str(file_path),
                        "chunk_index": len(all_chunks),
                        "section_index": idx,
                        "subsection_index": sub_idx,
                        "total_sections": total_header_chunks,
                        "headers": headers,
                        "word_count": len(sub_chunk_text.split()),
                        "char_count": len(sub_chunk_text),
                    }
                    
                    # Generate unique chunk ID
                    chunk_id = self.generate_chunk_id(sub_chunk_text, metadata)
                    metadata["chunk_id"] = chunk_id
                    
                    # Count tokens if needed (optional, can be slow for large docs)
                    # metadata["token_count"] = self.count_tokens(sub_chunk_text)
                    
                    doc = Document(
                        page_content=sub_chunk_text,
                        metadata=metadata
                    )
                    all_chunks.append(doc)
            else:
                # Use the section as-is
                metadata = {
                    "source": str(file_path),
                    "chunk_index": len(all_chunks),
                    "section_index": idx,
                    "subsection_index": 0,
                    "total_sections": total_header_chunks,
                    "headers": headers,
                    "word_count": len(header_chunk.page_content.split()),
                    "char_count": len(header_chunk.page_content),
                }
                
                chunk_id = self.generate_chunk_id(header_chunk.page_content, metadata)
                metadata["chunk_id"] = chunk_id
                
                doc = Document(
                    page_content=header_chunk.page_content,
                    metadata=metadata
                )
                all_chunks.append(doc)
        
        print(f"Created {len(all_chunks)} chunks from {total_header_chunks} sections")
        return all_chunks
    
    def process_multiple_files(self, file_paths: List[Path]) -> List[Document]:
        """Process multiple markdown files"""
        all_documents = []
        
        for file_path in file_paths:
            if file_path.exists() and file_path.suffix == '.md':
                documents = self.chunk_markdown(file_path)
                all_documents.extend(documents)
                print(f"Processed {file_path.name}: {len(documents)} chunks")
            else:
                print(f"Skipping {file_path}: not a valid markdown file")
        
        return all_documents
    
    def get_chunk_statistics(self, chunks: List[Document]) -> Dict[str, Any]:
        """Get statistics about the processed chunks"""
        if not chunks:
            return {}
        
        char_counts = [chunk.metadata.get("char_count", 0) for chunk in chunks]
        word_counts = [chunk.metadata.get("word_count", 0) for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "avg_char_count": sum(char_counts) / len(char_counts),
            "min_char_count": min(char_counts),
            "max_char_count": max(char_counts),
            "avg_word_count": sum(word_counts) / len(word_counts),
            "min_word_count": min(word_counts),
            "max_word_count": max(word_counts),
            "total_characters": sum(char_counts),
            "total_words": sum(word_counts),
        }
