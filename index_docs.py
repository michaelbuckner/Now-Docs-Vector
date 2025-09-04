#!/usr/bin/env python3
"""Main script to index ServiceNow documentation into vector database"""

import click
from pathlib import Path
import json
from datetime import datetime
import sys

from document_processor import DocumentProcessor
from vector_store import VectorStoreManager
from config import settings


@click.command()
@click.option(
    '--docs-path',
    type=click.Path(exists=True),
    default='zurich-intelligent-experiences.md',
    help='Path to the markdown documentation file'
)
@click.option(
    '--chunk-size',
    type=int,
    default=None,
    help='Size of text chunks (overrides config)'
)
@click.option(
    '--chunk-overlap',
    type=int,
    default=None,
    help='Overlap between chunks (overrides config)'
)
@click.option(
    '--reset',
    is_flag=True,
    help='Reset the vector database before indexing'
)
@click.option(
    '--batch-size',
    type=int,
    default=100,
    help='Batch size for indexing'
)
def index_documentation(docs_path, chunk_size, chunk_overlap, reset, batch_size):
    """Index ServiceNow documentation into vector database"""
    
    print("=" * 60)
    print("ServiceNow Documentation Vectorizer")
    print("=" * 60)
    
    # Convert path to Path object
    docs_file = Path(docs_path)
    
    if not docs_file.exists():
        print(f"Error: Documentation file not found: {docs_file}")
        sys.exit(1)
    
    # Get file size
    file_size = docs_file.stat().st_size / (1024 * 1024)  # Convert to MB
    print(f"\nDocument: {docs_file.name}")
    print(f"Size: {file_size:.2f} MB")
    
    # Initialize components
    print("\n1. Initializing components...")
    
    # Use provided values or fall back to config
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    processor = DocumentProcessor(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    vector_store = VectorStoreManager()
    
    # Reset database if requested
    if reset:
        print("\n2. Resetting vector database...")
        vector_store.reset_database()
    else:
        print("\n2. Using existing vector database...")
        info = vector_store.get_collection_info()
        print(f"   Current documents: {info.get('count', 0)}")
    
    # Process the document
    print(f"\n3. Processing document with chunk_size={chunk_size}, overlap={chunk_overlap}...")
    documents = processor.chunk_markdown(docs_file)
    
    # Get and display statistics
    stats = processor.get_chunk_statistics(documents)
    print("\nChunking Statistics:")
    print(f"   Total chunks: {stats['total_chunks']}")
    print(f"   Average chunk size: {stats['avg_char_count']:.0f} characters")
    print(f"   Min/Max chunk size: {stats['min_char_count']}/{stats['max_char_count']} characters")
    print(f"   Total words: {stats['total_words']:,}")
    
    # Index documents
    print(f"\n4. Indexing {len(documents)} chunks into vector database...")
    print(f"   Using embedding model: {settings.embedding_model_type}/{settings.embedding_model_name}")
    print(f"   Batch size: {batch_size}")
    
    indexing_stats = vector_store.add_documents(documents, batch_size=batch_size)
    
    # Display results
    print("\n5. Indexing Complete!")
    print("=" * 60)
    print(f"   Successfully indexed: {indexing_stats['successful']} chunks")
    if indexing_stats['failed'] > 0:
        print(f"   Failed: {indexing_stats['failed']} chunks")
    print(f"   Total documents in database: {indexing_stats['final_document_count']}")
    
    # Save summary
    summary_file = Path("indexing_summary.json")
    summary = {
        "timestamp": datetime.now().isoformat(),
        "document": str(docs_file),
        "file_size_mb": file_size,
        "chunk_config": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        },
        "chunking_stats": stats,
        "indexing_stats": indexing_stats,
        "embedding_model": {
            "type": settings.embedding_model_type,
            "name": settings.embedding_model_name
        }
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nSummary saved to: {summary_file}")
    
    # Test search
    print("\n6. Testing search functionality...")
    test_query = "Now Assist AI agents"
    results = vector_store.search_with_relevance(test_query, k=3)
    
    if results:
        print(f"\nTest query: '{test_query}'")
        print(f"Found {len(results)} relevant chunks:")
        for i, result in enumerate(results, 1):
            print(f"\n   Result {i} (score: {result['score']:.3f}):")
            preview = result['content'][:200].replace('\n', ' ')
            print(f"   {preview}...")
            if result.get('headers'):
                print(f"   Headers: {result['headers']}")
    
    print("\n✅ Indexing complete! The vector database is ready for use.")
    print(f"   Database location: {settings.chroma_persist_directory}")
    print(f"   Collection name: {settings.collection_name}")


if __name__ == "__main__":
    index_documentation()
