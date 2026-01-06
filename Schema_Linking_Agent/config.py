"""
Configuration Module

Centralized configuration for Query-Based Schema Filtering.
Contains default values and configuration options.
"""

from dataclasses import dataclass


@dataclass
class FilterConfig:
    """
    Configuration class for Query-Based Schema Filtering.
    
    Contains all configurable parameters for embedding generation,
    vector database, filtering, and update strategies.
    """
    
    # Embedding Configuration
    embedding_model: str = "Alibaba-NLP/gte-large-en-v1.5"  # sentence-transformers model (local)
    batch_size: int = 100  # Batch size for embedding generation
    
    # Vector Database Configuration
    vector_db_type: str = "chroma"  # "chroma" or "pinecone"
    vector_db_path: str = "./vector_db"  # Path to vector database directory
    collection_name: str = "schema_embeddings"  # Collection name in vector DB
    
    # Filtering Configuration
    default_top_k_tables: int = 20  # Default max tables to include
    default_top_k_columns: int = 20  # Default max columns per table
    default_similarity_threshold: float = 0.6 # Default similarity threshold (0-1)
    default_fk_hops: int = 1  # Default foreign key hop limit
    
    # Update Strategy Configuration
    update_on_schema_change: bool = True  # Auto-update on schema changes
    periodic_update_interval: int = 86400  # Update interval in seconds (24 hours)
    embedding_cache_path: str = "./embeddings_cache.json"  # Path to cache file
    
    # Reranker Configuration
    reranker_enabled: bool = True  # Enable reranker (on by default)
    reranker_model: str = "BAAI/bge-reranker-base"  # Cross-encoder reranker model
    reranker_top_k_initial: int = 20  # Initial candidates from vector search (before reranking)
    reranker_top_k_final_tables: int = 10  # Final table results after reranking (reranker-specific)
    reranker_top_k_final_columns: int = 10  # Final column results after reranking (reranker-specific)
    enable_llm_validation: bool = False  # LLM-based validation/fallback (off by default)
    llm_validation_threshold: float = 0.7  # Only validate with LLM if confidence < threshold

