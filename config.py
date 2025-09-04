"""Configuration for ServiceNow Documentation Vectorizer"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # OpenAI API Configuration (optional - can use local embeddings instead)
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Vector Database Configuration
    chroma_persist_directory: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    collection_name: str = Field(default="servicenow_docs", env="COLLECTION_NAME")
    
    # Embedding Model Configuration
    embedding_model_type: str = Field(default="local", env="EMBEDDING_MODEL_TYPE")  # "openai" or "local"
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL_NAME")
    
    # Chunking Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    separators: List[str] = Field(default=["\n\n", "\n", " ", ""], env="SEPARATORS")
    
    # MCP Server Configuration
    mcp_server_port: int = Field(default=3333, env="MCP_SERVER_PORT")
    mcp_server_host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    
    # Search Configuration
    max_results: int = Field(default=10, env="MAX_RESULTS")
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    
    # Documentation paths
    docs_path: Path = Field(default=Path("./zurich-intelligent-experiences.md"))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_embedding_function(self):
        """Get the appropriate embedding function based on configuration"""
        if self.embedding_model_type.lower() == "openai":
            from langchain_openai import OpenAIEmbeddings
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY must be set when using OpenAI embeddings")
            return OpenAIEmbeddings(
                model=self.embedding_model_name,
                openai_api_key=self.openai_api_key
            )
        else:
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
            except ImportError:
                from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )


# Create a global settings instance
settings = Settings()
