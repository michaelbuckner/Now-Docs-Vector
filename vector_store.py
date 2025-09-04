# vector_store.py

"""Vector store management using ChromaDB and LangChain"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain.schema import Document
from tqdm import tqdm

# Assuming config.py is in the same directory and contains 'settings'
from config import settings

class VectorStoreManager:
    """Manage vector database operations for ServiceNow documentation."""
    
    def __init__(self, persist_directory: Optional[str] = None, collection_name: Optional[str] = None):
        """Initializes the VectorStoreManager."""
        self.persist_directory = Path(persist_directory or settings.chroma_persist_directory)
        self.collection_name = collection_name or settings.collection_name
        self.embedding_function = settings.get_embedding_function()
        
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # This client configuration is correct and disables the problematic telemetry.
        # The package upgrade is the final part of the fix.
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize the LangChain Chroma vector store wrapper
        self.vector_store = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
            persist_directory=str(self.persist_directory)
        )
        
        # Get the underlying collection object for direct operations like count()
        self.collection = self.client.get_collection(name=self.collection_name)
        
        print(f"Vector store initialized for collection: '{self.collection_name}'", file=sys.stderr)
        print(f"Current document count: {self.collection.count()}", file=sys.stderr)

    def add_documents(self, documents: List[Document], batch_size: int = 100) -> Dict[str, Any]:
        """Adds documents to the vector store in batches."""
        if not documents:
            return {"error": "No documents provided"}
        
        stats = {"total_documents": len(documents), "successful": 0, "failed": 0, "start_time": datetime.now().isoformat()}
        
        for i in tqdm(range(0, len(documents), batch_size), desc="Indexing batches"):
            batch = documents[i:i + batch_size]
            try:
                texts = [doc.page_content for doc in batch]
                ids = [doc.metadata.get("chunk_id", f"chunk_{i + j}") for j, doc in enumerate(batch)]
                
                # Clean metadata to ensure all values are basic types compatible with ChromaDB
                cleaned_metadatas = []
                for doc in batch:
                    clean_meta = {}
                    for key, value in doc.metadata.items():
                        if isinstance(value, (str, int, float, bool, type(None))):
                            clean_meta[key] = value
                        else:
                            clean_meta[key] = str(value)
                    cleaned_metadatas.append(clean_meta)

                self.vector_store.add_texts(texts=texts, metadatas=cleaned_metadatas, ids=ids)
                stats["successful"] += len(batch)
            except Exception as e:
                print(f"Error processing batch starting at index {i}: {e}", file=sys.stderr)
                stats["failed"] += len(batch)
                stats["last_error"] = str(e)
        
        stats["end_time"] = datetime.now().isoformat()
        stats["final_document_count"] = self.collection.count()
        self._save_stats(stats)
        return stats
    
    def search_with_relevance(self, query: str, k: int = 5, distance_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Searches for documents and filters them by a distance threshold.

        Note: The score returned is a distance metric (e.g., L2, cosine distance).
        A smaller score indicates a better match (i.e., less distance).

        Args:
            query: The search query string.
            k: The number of results to retrieve before filtering.
            distance_threshold: The maximum allowed distance for a result to be included.
                                (e.g., 0.5 means only results with a distance of 0.5 or less).

        Returns:
            A list of formatted search results.
        """
        if not self.vector_store:
            return []
        
        # similarity_search_with_score returns documents and their distance scores.
        results_with_scores = self.vector_store.similarity_search_with_relevance_scores(query=query, k=k)
        
        formatted_results = []
        for doc, score in results_with_scores:
            # The score is a distance, so a lower value is better.
            # We filter out results where the distance is too high.
            if score <= distance_threshold:
                formatted_results.append({
                    "content": doc.page_content,
                    "score": float(score),  # This is the distance score
                    "metadata": doc.metadata,
                    "headers": doc.metadata.get("headers", {}),
                    "source": doc.metadata.get("source", "")
                })
        
        return formatted_results
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Gets information about the current collection."""
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
            "metadata": self.collection.metadata,
            "persist_directory": str(self.persist_directory)
        }
    
    def _save_stats(self, stats: Dict[str, Any]):
        """Saves indexing statistics to a file."""
        stats_file = self.persist_directory / "indexing_stats.json"
        try:
            existing_stats = json.loads(stats_file.read_text()) if stats_file.exists() else []
            existing_stats.append(stats)
            stats_file.write_text(json.dumps(existing_stats, indent=2))
        except Exception as e:
            print(f"Could not save indexing stats: {e}", file=sys.stderr)