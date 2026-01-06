"""
Query-Based Schema Filter - Main Module

Main orchestrator class that integrates all components to provide
query-based schema filtering functionality. Handles embedding generation,
vector storage, query filtering, and foreign key expansion.
"""

import os
import json
from typing import Dict, Optional
from embedding_service import EmbeddingService
from vector_store import VectorStore
from schema_embedder import SchemaEmbedder
from query_filter import QueryFilter
from foreign_key_expander import ForeignKeyExpander
from config import FilterConfig


class QueryBasedSchemaFilter:
    """
    Main class for query-based schema filtering.
    
    This class orchestrates the entire pipeline:
    1. Pre-computes embeddings for the M-Schema
    2. Stores embeddings in vector database
    3. Filters schema based on user queries
    4. Expands selection with foreign key relationships
    
    Provides a simple interface for filtering large schemas to only
    relevant tables and columns based on semantic similarity to queries.
    """
    
    def __init__(
        self, 
        schema_path: str, 
        vector_db_path: str = "./vector_db",
        embedding_cache_path: Optional[str] = None
    ):
        """
        Initialize the Query-Based Schema Filter.
        
        Sets up all necessary components: embedding service, vector store,
        schema embedder, and query filter. Loads the M-Schema from the
        specified path.
        
        Args:
            schema_path: Path to the M-Schema JSON file.
            vector_db_path: Path to the vector database directory.
                          Default is "./vector_db".
            embedding_cache_path: Optional path to cache embeddings on disk.
                                 If None, uses "./embeddings_cache.json".
                                 Default is None.
        
        Raises:
            FileNotFoundError: If schema file doesn't exist.
            ValueError: If GROQ_API_KEY is not set.
        
        Example:
            >>> filter = QueryBasedSchemaFilter(
            ...     schema_path="./schema.json",
            ...     vector_db_path="./my_vector_db"
            ... )
        """
        self.schema_path = schema_path
        self.vector_db_path = vector_db_path
        self.embedding_cache_path = embedding_cache_path or "./embeddings_cache.json"
        
        # Load configuration
        self.config = FilterConfig()
        
        # Initialize components
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore(
            db_path=vector_db_path,
            collection_name="schema_embeddings"
        )
        self.vector_store.initialize_store()
        
        self.schema_embedder = SchemaEmbedder(self.embedding_service)
        
        # Initialize reranker if enabled (lazy loading - model loads on first use)
        reranker = None
        if self.config.reranker_enabled:
            try:
                from reranker import Reranker
                # Create reranker instance (model will load lazily on first use)
                reranker = Reranker(
                    model=self.config.reranker_model,
                    enable_llm_fallback=self.config.enable_llm_validation,
                    llm_validation_threshold=self.config.llm_validation_threshold
                )
                print("✓ Reranker initialized (model will load on first use)")
            except Exception as e:
                print(f"⚠ Warning: Failed to initialize reranker: {str(e)}")
                print("   Continuing without reranker...")
                reranker = None
        
        self.query_filter = QueryFilter(
            self.embedding_service,
            self.vector_store,
            reranker=reranker,
            config=self.config
        )
        
        # Load schema
        self.mschema = self.schema_embedder.load_schema(schema_path)
        self.foreign_key_expander = ForeignKeyExpander(self.mschema)
    
    def precompute_embeddings(self, force_recompute: bool = False):
        """
        Pre-compute and store embeddings for the entire M-Schema.
        
        Generates embeddings for all tables and columns in the M-Schema
        and stores them in the vector database. Can use cached embeddings
        from disk if available and force_recompute is False.
        
        Args:
            force_recompute: If True, regenerate embeddings even if cache exists.
                           If False, use cached embeddings if available.
                           Default is False.
        
        Returns:
            None (embeddings are stored in vector database and optionally cached).
        
        Example:
            >>> filter = QueryBasedSchemaFilter("./schema.json")
            >>> filter.precompute_embeddings(force_recompute=False)
        """
        # Check if cache exists and we don't want to recompute
        if not force_recompute and os.path.exists(self.embedding_cache_path):
            print(f"Loading embeddings from cache: {self.embedding_cache_path}")
            try:
                with open(self.embedding_cache_path, 'r', encoding='utf-8') as f:
                    cached_embeddings = json.load(f)
                
                # Check if cache is valid (has embeddings)
                if cached_embeddings and len(cached_embeddings) > 0:
                    print(f"Found {len(cached_embeddings)} cached embeddings")
                    # Store in vector database
                    self.vector_store.store_embeddings(cached_embeddings)
                    return
            except Exception as e:
                print(f"Error loading cache, regenerating: {str(e)}")
        
        # Generate embeddings
        print("Generating embeddings for M-Schema...")
        embeddings = self.schema_embedder.embed_full_schema(self.mschema)
        print(f"Generated {len(embeddings)} embeddings")
        
        # Store in vector database
        print("Storing embeddings in vector database...")
        self.vector_store.store_embeddings(embeddings)
        print("Embeddings stored successfully")
        
        # Cache embeddings to disk
        print(f"Caching embeddings to: {self.embedding_cache_path}")
        self.schema_embedder.save_embeddings(embeddings, self.embedding_cache_path)
        print("Embeddings cached successfully")
    
    def filter_schema(
        self, 
        user_query: str, 
        top_k_tables: int = 15, 
        top_k_columns: int = 20, 
        similarity_threshold: float = 0.5, 
        fk_hops: int = 1
    ) -> Dict:
        """
        Filter schema based on user query with foreign key expansion.
        
        Main method for filtering the M-Schema. Takes a user query,
        finds relevant tables and columns using semantic search, expands
        selection with foreign key relationships, and returns a filtered
        M-Schema containing only relevant elements.
        
        Args:
            user_query: Natural language query from the user.
            top_k_tables: Maximum number of tables to include. Default is 15.
            top_k_columns: Maximum number of columns per table to include.
                          Default is 20.
            similarity_threshold: Minimum similarity score (0-1) required.
                                Default is 0.5.
            fk_hops: Number of foreign key hops to traverse when expanding
                    selection. 0 = no expansion, 1 = directly connected,
                    2 = two hops away, etc. Default is 1.
        
        Returns:
            Dictionary containing filtered M-Schema with:
            - "db_id": str - Database identifier
            - "schema": str - Schema name
            - "tables": Dict - Filtered tables with selected columns
            - "foreign_keys": List - Foreign keys involving selected tables
        
        Example:
            >>> filter = QueryBasedSchemaFilter("./schema.json")
            >>> filter.precompute_embeddings()
            >>> filtered = filter.filter_schema(
            ...     "Show me revenue by region and segment",
            ...     top_k_tables=10,
            ...     top_k_columns=15,
            ...     fk_hops=1
            ... )
            >>> len(filtered["tables"]) <= 10
            True
        """
        # Filter based on query
        filtered_schema = self.query_filter.filter_by_query(
            user_query=user_query,
            mschema=self.mschema,
            top_k_tables=top_k_tables,
            top_k_columns=top_k_columns,
            similarity_threshold=similarity_threshold
        )
        
        # Get selected tables
        selected_tables = list(filtered_schema.get("tables", {}).keys())
        
        # Expand with foreign keys if hops > 0
        if fk_hops > 0 and selected_tables:
            expanded_tables = self.foreign_key_expander.expand_with_foreign_keys(
                selected_tables=selected_tables,
                max_hops=fk_hops
            )
            
            # Add any new tables from FK expansion
            original_tables = self.mschema.get("tables", {})
            for table_name in expanded_tables:
                if table_name not in filtered_schema["tables"] and table_name in original_tables:
                    # Add the full table (all columns) for FK-expanded tables
                    filtered_schema["tables"][table_name] = original_tables[table_name].copy()
        
        # Update foreign keys in filtered schema
        selected_tables_set = set(filtered_schema["tables"].keys())
        filtered_schema["foreign_keys"] = [
            fk for fk in self.mschema.get("foreign_keys", [])
            if len(fk) >= 5 and fk[0] in selected_tables_set and fk[3] in selected_tables_set
        ]
        
        return filtered_schema
    
    def update_embeddings(self, table_name: Optional[str] = None):
        """
        Update embeddings for changed tables.
        
        Regenerates and updates embeddings for a specific table or
        all tables if table_name is None. Useful when schema changes
        and you want to update embeddings incrementally.
        
        Args:
            table_name: Name of the table to update. If None, updates
                       all tables. Default is None.
        
        Returns:
            None (embeddings are updated in vector database).
        
        Example:
            >>> filter = QueryBasedSchemaFilter("./schema.json")
            >>> filter.update_embeddings(table_name="revenue")
        """
        if table_name is None:
            # Update all tables
            print("Updating embeddings for all tables...")
            self.precompute_embeddings(force_recompute=True)
        else:
            # Update specific table
            print(f"Updating embeddings for table: {table_name}")
            if table_name in self.mschema.get("tables", {}):
                table_data = self.mschema["tables"][table_name]
                # Generate embeddings for this table
                table_embeddings = []
                
                # Table-level embedding
                table_text = self.schema_embedder.extract_embeddable_text(
                    table_name, table_data
                )
                table_embedding = self.embedding_service.embed_text(table_text)
                table_embeddings.append({
                    "embedding": table_embedding,
                    "element_type": "table",
                    "table_name": table_name,
                    "column_name": None,
                    "description": table_data.get('table_description', ''),
                    "metadata": {"table_name": table_name}
                })
                
                # Column-level embeddings
                for col_name, col_info in table_data.get("fields", {}).items():
                    col_text = self.schema_embedder.extract_embeddable_text(
                        table_name, table_data, {col_name: col_info}
                    )
                    col_embedding = self.embedding_service.embed_text(col_text)
                    table_embeddings.append({
                        "embedding": col_embedding,
                        "element_type": "column",
                        "table_name": table_name,
                        "column_name": col_name,
                        "description": col_info.get('column_description', ''),
                        "metadata": {"table_name": table_name, "column_name": col_name}
                    })
                
                # Update in vector store
                self.vector_store.update_embeddings(table_name, table_embeddings)
                print(f"Updated embeddings for {len(table_embeddings)} elements")
            else:
                print(f"Table '{table_name}' not found in schema")
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the schema and embeddings.
        
        Returns information about the original schema size, number of
        embeddings stored, and vector database status.
        
        Returns:
            Dictionary containing:
            - "num_tables": int - Number of tables in original schema
            - "num_columns": int - Total number of columns
            - "num_foreign_keys": int - Number of foreign key relationships
            - "num_embeddings": int - Number of embeddings stored
            - "stored_tables": List[str] - List of tables with stored embeddings
        
        Example:
            >>> filter = QueryBasedSchemaFilter("./schema.json")
            >>> stats = filter.get_statistics()
            >>> stats["num_tables"]
            4
        """
        tables = self.mschema.get("tables", {})
        num_tables = len(tables)
        num_columns = sum(len(t.get("fields", {})) for t in tables.values())
        num_foreign_keys = len(self.mschema.get("foreign_keys", []))
        
        stored_tables = self.vector_store.get_all_tables()
        num_embeddings = len(stored_tables) * 2  # Rough estimate (table + columns)
        
        return {
            "num_tables": num_tables,
            "num_columns": num_columns,
            "num_foreign_keys": num_foreign_keys,
            "num_embeddings": num_embeddings,
            "stored_tables": stored_tables
        }

