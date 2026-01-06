"""
Query-Based Filter Module

Filters M-Schema based on user queries using semantic search.
Finds relevant tables and columns by comparing query embeddings
with schema element embeddings stored in the vector database.
"""

from typing import List, Dict, Optional
from embedding_service import EmbeddingService
from vector_store import VectorStore
from reranker import Reranker
from config import FilterConfig


class QueryFilter:
    """
    Filters schema elements based on semantic similarity to user queries.
    
    This class uses embedding-based similarity search to find the most
    relevant tables and columns for a given user query. It combines
    top-K selection with similarity threshold filtering.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        reranker: Optional[Reranker] = None,
        config: Optional[FilterConfig] = None
    ):
        """
        Initialize the Query Filter.
        
        Sets up the query filter with embedding service, vector store, and
        optionally a reranker for improved accuracy. The reranker is used
        as a second stage after vector search to rerank candidates.
        
        Args:
            embedding_service: Instance of EmbeddingService for generating query embeddings.
            vector_store: Instance of VectorStore for searching similar schema elements.
            reranker: Optional Reranker instance for reranking candidates.
                    If None, reranking is disabled. Default is None.
            config: Optional FilterConfig instance for configuration.
                  If None, uses default configuration. Default is None.
        
        Example:
            >>> from embedding_service import EmbeddingService
            >>> from vector_store import VectorStore
            >>> from reranker import Reranker
            >>> emb_service = EmbeddingService()
            >>> v_store = VectorStore()
            >>> v_store.initialize_store()
            >>> reranker = Reranker() if config.reranker_enabled else None
            >>> filter = QueryFilter(emb_service, v_store, reranker=reranker)
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.reranker = reranker
        self.config = config or FilterConfig()
        self.reranker_enabled = self.config.reranker_enabled and reranker is not None
    
    def get_relevant_tables(
        self, 
        query_embedding: List[float],
        user_query: str,
        top_k: int = 15, 
        threshold: float = 0.7
    ) -> List[str]:
        """
        Find relevant tables based on query embedding with optional reranking.
        
        Searches the vector database for tables whose embeddings are most similar
        to the query embedding. If reranker is enabled, performs a two-stage
        retrieval: (1) vector search for initial candidates, (2) reranker for
        improved accuracy. Results must meet both the similarity threshold and
        be in the top-K most similar.
        
        Args:
            query_embedding: Embedding vector of the user query.
            user_query: Original natural language query (needed for reranking).
            top_k: Maximum number of tables to return. Default is 15.
            threshold: Minimum similarity score (0-1) required. Default is 0.7.
        
        Returns:
            List of table names (strings) sorted by relevance (most relevant first).
            If reranker is enabled, tables are reranked by reranker scores.
            If reranker is disabled, tables are sorted by similarity scores.
        
        Example:
            >>> query_emb = embedding_service.embed_text("revenue by region")
            >>> tables = filter.get_relevant_tables(
            ...     query_emb,
            ...     "Show me revenue by region",
            ...     top_k=10,
            ...     threshold=0.7
            ... )
            >>> len(tables) <= 10
            True
        """
        # Stage 1: Vector search for initial candidates
        # Get more candidates if reranker is enabled
        initial_top_k = self.config.reranker_top_k_initial if self.reranker_enabled else top_k
        
        results = self.vector_store.search_similar(
            query_embedding=query_embedding,
            top_k=initial_top_k,
            threshold=threshold,
            element_type="table"
        )
        
        # Stage 2: Rerank if enabled
        if self.reranker_enabled and self.reranker and results:
            # Use reranker's own configuration for final count, not filtering config
            reranker_top_k = self.config.reranker_top_k_final_tables
            reranked_results = self.reranker.rerank_tables(
                query=user_query,
                candidates=results,
                top_k=reranker_top_k
            )
            # Apply filtering limit after reranking (if reranker returned more than requested)
            reranked_results = reranked_results[:top_k]
            # Extract table names from reranked results
            table_names = []
            for result in reranked_results:
                table_name = result['metadata'].get('table_name')
                if table_name and table_name not in table_names:
                    table_names.append(table_name)
            return table_names
        else:
            # No reranking: extract table names from vector search results
            table_names = []
            for result in results:
                table_name = result['metadata'].get('table_name')
                if table_name and table_name not in table_names:
                    table_names.append(table_name)
            return table_names
    
    def get_relevant_columns(
        self, 
        table_name: str,
        query_embedding: List[float],
        user_query: str,
        top_k: int = 20, 
        threshold: float = 0.7
    ) -> List[str]:
        """
        Find relevant columns for a specific table based on query embedding with optional reranking.
        
        Searches the vector database for columns in the specified table whose embeddings
        are most similar to the query embedding. If reranker is enabled, performs a two-stage
        retrieval: (1) vector search for initial candidates, (2) reranker for improved accuracy.
        Results are filtered to only include columns from the specified table.
        
        Args:
            table_name: Name of the table to search columns in.
            query_embedding: Embedding vector of the user query.
            user_query: Original natural language query (needed for reranking).
            top_k: Maximum number of columns to return. Default is 20.
            threshold: Minimum similarity score (0-1) required. Default is 0.7.
        
        Returns:
            List of column names (strings) sorted by relevance (most relevant first).
            If reranker is enabled, columns are reranked by reranker scores.
            If reranker is disabled, columns are sorted by similarity scores.
        
        Example:
            >>> query_emb = embedding_service.embed_text("revenue amount")
            >>> columns = filter.get_relevant_columns(
            ...     "revenue_table",
            ...     query_emb,
            ...     "Show me revenue amount",
            ...     top_k=15
            ... )
            >>> "amount" in columns or "revenue" in columns
            True
        """
        # Stage 1: Vector search for initial candidates
        # Get more candidates if reranker is enabled
        initial_top_k = self.config.reranker_top_k_initial if self.reranker_enabled else top_k * 2
        
        results = self.vector_store.search_similar(
            query_embedding=query_embedding,
            top_k=initial_top_k,
            threshold=threshold,
            element_type="column"
        )
        
        # Filter by table name first
        table_candidates = [
            result for result in results
            if result['metadata'].get('table_name') == table_name
        ]
        
        # Stage 2: Rerank if enabled
        if self.reranker_enabled and self.reranker and table_candidates:
            # Use reranker's own configuration for final count, not filtering config
            reranker_top_k = self.config.reranker_top_k_final_columns
            reranked_results = self.reranker.rerank_columns(
                query=user_query,
                table_name=table_name,
                candidates=table_candidates,
                top_k=reranker_top_k
            )
            # Apply filtering limit after reranking (if reranker returned more than requested)
            reranked_results = reranked_results[:top_k]
            # Extract column names from reranked results
            column_names = []
            for result in reranked_results:
                column_name = result['metadata'].get('column_name')
                if column_name and column_name not in column_names:
                    column_names.append(column_name)
            return column_names
        else:
            # No reranking: extract column names from vector search results
            column_names = []
            for result in table_candidates:
                column_name = result['metadata'].get('column_name')
                if column_name and column_name not in column_names:
                    column_names.append(column_name)
                    # Stop if we have enough columns
                    if len(column_names) >= top_k:
                        break
            return column_names
    
    def build_filtered_schema(
        self, 
        selected_tables: List[str], 
        selected_columns: Dict[str, List[str]],
        mschema: Dict
    ) -> Dict:
        """
        Build a filtered M-Schema containing only selected tables and columns.
        
        Creates a new M-Schema dictionary that includes only the selected
        tables and their selected columns, preserving the original structure
        and metadata (descriptions, types, etc.).
        
        Args:
            selected_tables: List of table names to include in filtered schema.
            selected_columns: Dictionary mapping table names to lists of
                            column names to include for each table.
                            Format: {"table_name": ["col1", "col2", ...]}
            mschema: Original M-Schema dictionary to filter.
        
        Returns:
            Dictionary containing filtered M-Schema with:
            - "db_id": str - Database identifier (from original)
            - "schema": str - Schema name (from original)
            - "tables": Dict - Filtered tables with selected columns
            - "foreign_keys": List - Foreign keys involving selected tables
        
        Example:
            >>> selected_tables = ["revenue", "customers"]
            >>> selected_columns = {"revenue": ["amount", "date"], "customers": ["id", "name"]}
            >>> filtered = filter.build_filtered_schema(selected_tables, selected_columns, schema)
            >>> "revenue" in filtered["tables"]
            True
        """
        filtered_schema = {
            "db_id": mschema.get("db_id", ""),
            "schema": mschema.get("schema", ""),
            "tables": {},
            "foreign_keys": []
        }
        
        original_tables = mschema.get("tables", {})
        
        # Filter tables and columns
        for table_name in selected_tables:
            if table_name in original_tables:
                original_table = original_tables[table_name]
                filtered_table = {
                    "fields": {},
                    "examples": original_table.get("examples", []),
                    "table_description": original_table.get("table_description", "")
                }
                
                # Filter columns
                table_columns = selected_columns.get(table_name, [])
                original_fields = original_table.get("fields", {})
                
                # If no columns specified, include all columns
                if not table_columns:
                    filtered_table["fields"] = original_fields.copy()
                else:
                    for col_name in table_columns:
                        if col_name in original_fields:
                            filtered_table["fields"][col_name] = original_fields[col_name].copy()
                
                filtered_schema["tables"][table_name] = filtered_table
        
        # Filter foreign keys to include only those involving selected tables
        selected_tables_set = set(selected_tables)
        for fk in mschema.get("foreign_keys", []):
            if len(fk) >= 5:
                source_table = fk[0]
                ref_table = fk[3]
                # Include FK if both tables are in selected set
                if source_table in selected_tables_set and ref_table in selected_tables_set:
                    filtered_schema["foreign_keys"].append(fk)
        
        return filtered_schema
    
    def filter_by_query(
        self, 
        user_query: str, 
        mschema: Dict,
        top_k_tables: int = 15, 
        top_k_columns: int = 20, 
        similarity_threshold: float = 0.5
    ) -> Dict:
        """
        Filter schema based on user query using semantic search.
        
        Main filtering method that takes a user query, generates its embedding,
        finds relevant tables and columns, and builds a filtered M-Schema.
        
        Args:
            user_query: Natural language query from the user.
            mschema: Original M-Schema dictionary to filter.
            top_k_tables: Maximum number of tables to include. Default is 15.
            top_k_columns: Maximum number of columns per table to include.
                          Default is 20.
            similarity_threshold: Minimum similarity score (0-1) required.
                                 Default is 0.7.
        
        Returns:
            Dictionary containing filtered M-Schema with only relevant
            tables and columns based on the query.
        
        Example:
            >>> schema = load_schema("schema.json")
            >>> filtered = filter.filter_by_query(
            ...     "Show me revenue by region",
            ...     schema,
            ...     top_k_tables=10,
            ...     top_k_columns=15
            ... )
            >>> len(filtered["tables"]) <= 10
            True
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(user_query)
        
        # Find relevant tables (with reranking if enabled)
        relevant_tables = self.get_relevant_tables(
            query_embedding=query_embedding,
            user_query=user_query,
            top_k=top_k_tables,
            threshold=similarity_threshold
        )
        
        # Debug: Print if no tables found
        if not relevant_tables:
            print(f"⚠ Warning: No tables found for query '{user_query}' with threshold {similarity_threshold}")
            print(f"   Try lowering the similarity_threshold (e.g., 0.3 or 0.5)")
        
        # Find relevant columns for each table (with reranking if enabled)
        selected_columns = {}
        for table_name in relevant_tables:
            relevant_cols = self.get_relevant_columns(
                table_name=table_name,
                query_embedding=query_embedding,
                user_query=user_query,
                top_k=top_k_columns,
                threshold=similarity_threshold
            )
            selected_columns[table_name] = relevant_cols
            
            # Debug: Print if no columns found for a table
            if not relevant_cols:
                print(f"⚠ Warning: No columns found for table '{table_name}' with threshold {similarity_threshold}")
        
        # Build filtered schema
        filtered_schema = self.build_filtered_schema(
            selected_tables=relevant_tables,
            selected_columns=selected_columns,
            mschema=mschema
        )
        
        return filtered_schema

