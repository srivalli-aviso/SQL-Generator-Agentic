"""
Vector Store Module

Provides interface to vector database (Chroma) for storing and querying
schema embeddings. Handles CRUD operations for embeddings with metadata.
"""

import os
import json
from typing import List, Dict, Optional

try:
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
except ImportError:
    raise ImportError(
        "chromadb package is required. Install it with: pip install chromadb>=0.4.0"
    )


class VectorStore:
    """
    Vector database interface for storing and querying schema embeddings.
    
    Uses ChromaDB as the underlying vector database to store embeddings
    with associated metadata (table names, column names, descriptions, etc.).
    """
    
    def __init__(self, db_path: str = "./vector_db", collection_name: str = "schema_embeddings"):
        """
        Initialize the Vector Store.
        
        Args:
            db_path: Path to the ChromaDB database directory. Default is "./vector_db".
            collection_name: Name of the collection to store embeddings. 
                           Default is "schema_embeddings".
        
        Example:
            >>> store = VectorStore(db_path="./my_db", collection_name="embeddings")
            >>> store.initialize_store()
        """
        self.db_path = db_path
        self.collection_name = collection_name
        self.client = None
        self.collection = None
    
    def initialize_store(self, reset: bool = False):
        """
        Initialize the vector database connection and collection.
        
        Creates or connects to the ChromaDB database and initializes
        the collection for storing embeddings. If reset is True, deletes
        existing collection and creates a new one.
        
        Args:
            reset: If True, delete existing collection and create new one.
                  Default is False.
        
        Example:
            >>> store = VectorStore()
            >>> store.initialize_store(reset=True)
        """
        # Create directory if it doesn't exist
        os.makedirs(self.db_path, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Delete collection if reset is requested
        if reset:
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception:
                pass  # Collection doesn't exist, which is fine
        
        # Get or create collection
        # Use cosine distance for better similarity matching with normalized embeddings
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Schema embeddings for query-based filtering"},
                # Use cosine distance for normalized embeddings
                # This will make similarity calculations more accurate
            )
    
    def store_embeddings(self, embeddings: List[Dict]):
        """
        Store embeddings in the vector database.
        
        Stores a list of embeddings with their associated metadata.
        Each embedding dictionary should contain:
        - "embedding": List[float] - The embedding vector
        - "element_type": str - "table" or "column"
        - "table_name": str - Name of the table
        - "column_name": Optional[str] - Name of column (if column)
        - "description": str - Description text
        - Additional metadata fields
        
        Args:
            embeddings: List of dictionaries, each containing an embedding
                       and metadata.
        
        Raises:
            Exception: If vector store is not initialized or storage fails.
        
        Example:
            >>> store = VectorStore()
            >>> store.initialize_store()
            >>> embeddings = [
            ...     {
            ...         "embedding": [0.1, 0.2, ...],
            ...         "element_type": "table",
            ...         "table_name": "revenue",
            ...         "description": "Revenue data"
            ...     }
            ... ]
            >>> store.store_embeddings(embeddings)
        """
        if self.collection is None:
            raise Exception("Vector store not initialized. Call initialize_store() first.")
        
        # Prepare data for ChromaDB
        ids = []
        embeddings_list = []
        metadatas = []
        
        for i, emb_data in enumerate(embeddings):
            # Create unique ID
            if emb_data.get("element_type") == "table":
                emb_id = f"table_{emb_data.get('table_name', i)}"
            else:
                emb_id = f"column_{emb_data.get('table_name', 'unknown')}_{emb_data.get('column_name', i)}"
            
            ids.append(emb_id)
            embeddings_list.append(emb_data["embedding"])
            
            # Prepare metadata (ChromaDB requires string values, no None allowed)
            # Convert None values to empty strings
            element_type = emb_data.get("element_type") or "unknown"
            table_name = emb_data.get("table_name") or ""
            column_name = emb_data.get("column_name") or ""
            description = emb_data.get("description") or ""
            
            # Ensure all values are strings (ChromaDB requirement)
            metadata = {
                "element_type": str(element_type),
                "table_name": str(table_name),
                "column_name": str(column_name),
                "description": str(description)
            }
            metadatas.append(metadata)
        
        # Store in ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings_list,
            metadatas=metadatas
        )
    
    def search_similar(
        self, 
        query_embedding: List[float], 
        top_k: int = 10, 
        threshold: float = 0.7,
        element_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for similar embeddings using cosine similarity.
        
        Searches the vector database for embeddings most similar to the
        query embedding. Results are filtered by similarity threshold and
        limited to top_k results. Optionally filters by element type.
        
        Args:
            query_embedding: The query embedding vector to search for.
            top_k: Maximum number of results to return. Default is 10.
            threshold: Minimum similarity score (0-1). Default is 0.7.
            element_type: Optional filter by element type ("table" or "column").
                         If None, searches all types. Default is None.
        
        Returns:
            List of dictionaries, each containing:
            - "id": str - Unique identifier
            - "distance": float - Similarity distance (lower is more similar)
            - "metadata": Dict - Metadata associated with the embedding
            Results are sorted by similarity (most similar first).
        
        Example:
            >>> store = VectorStore()
            >>> store.initialize_store()
            >>> query_emb = [0.1, 0.2, ...]
            >>> results = store.search_similar(query_emb, top_k=5, threshold=0.7)
            >>> len(results)
            5
        """
        if self.collection is None:
            raise Exception("Vector store not initialized. Call initialize_store() first.")
        
        # Prepare where clause for filtering
        where_clause = {}
        if element_type:
            where_clause["element_type"] = element_type
        
        # Search in ChromaDB
        # Note: ChromaDB by default uses L2 distance, but we can configure it
        # For cosine similarity, we need to use cosine distance and convert
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 3,  # Get more results to filter by threshold
            where=where_clause if where_clause else None
        )
        
        # Process results
        similar_items = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i, (emb_id, distance, metadata) in enumerate(zip(
                results['ids'][0],
                results['distances'][0],
                results['metadatas'][0]
            )):
                # ChromaDB uses L2 (Euclidean) distance by default
                # For normalized embeddings (sentence-transformers normalizes by default):
                # - For normalized vectors a, b: ||a - b||^2 = 2(1 - cos(a,b))
                # - So: ||a - b|| = sqrt(2(1 - cos(a,b)))
                # - Therefore: cos(a,b) = 1 - (||a - b||^2 / 2)
                # - ChromaDB returns ||a - b|| (not squared), so we square it
                
                try:
                    dist = float(distance)
                    
                    # For normalized embeddings, L2 distance ranges from 0 to 2
                    # Convert to cosine similarity using the correct formula
                    if dist <= 2.0:
                        # Normalized L2 distance: convert to cosine similarity
                        # cos_sim = 1 - (d^2 / 2) where d is L2 distance
                        similarity = 1.0 - ((dist * dist) / 2.0)
                    else:
                        # Distance > 2 suggests non-normalized or different metric
                        # Use approximation: similarity decreases with distance
                        similarity = max(0.0, 1.0 - (dist / 4.0))
                    
                    # Clamp to [0, 1] range
                    similarity = max(0.0, min(1.0, similarity))
                except (TypeError, ValueError, ZeroDivisionError):
                    # Fallback: assume distance is already a similarity metric (inverted)
                    similarity = max(0.0, min(1.0, 1.0 - float(distance))) if distance else 0.0
                
                # Apply threshold filter
                if similarity >= threshold:
                    similar_items.append({
                        "id": emb_id,
                        "distance": distance,
                        "similarity": similarity,
                        "metadata": metadata
                    })
                
                # Stop if we have enough results
                if len(similar_items) >= top_k:
                    break
        
        return similar_items
    
    def update_embeddings(self, table_name: str, embeddings: Dict):
        """
        Update embeddings for a specific table.
        
        Updates or adds embeddings for a table and its columns.
        Deletes existing embeddings for the table first, then adds new ones.
        
        Args:
            table_name: Name of the table to update.
            embeddings: Dictionary or list of embedding dictionaries to store.
                       Should follow the same format as store_embeddings().
        
        Example:
            >>> store = VectorStore()
            >>> store.initialize_store()
            >>> new_embeddings = [{"embedding": [...], "table_name": "revenue", ...}]
            >>> store.update_embeddings("revenue", new_embeddings)
        """
        if self.collection is None:
            raise Exception("Vector store not initialized. Call initialize_store() first.")
        
        # Delete existing embeddings for this table
        try:
            existing = self.collection.get(
                where={"table_name": table_name}
            )
            if existing['ids']:
                self.collection.delete(ids=existing['ids'])
        except Exception:
            pass  # No existing embeddings, which is fine
        
        # Store new embeddings
        if isinstance(embeddings, dict):
            embeddings = [embeddings]
        self.store_embeddings(embeddings)
    
    def get_all_tables(self) -> List[str]:
        """
        Get list of all table names stored in the vector database.
        
        Retrieves all unique table names from the stored embeddings.
        Useful for checking which tables have been embedded.
        
        Returns:
            List of unique table names (strings).
        
        Example:
            >>> store = VectorStore()
            >>> store.initialize_store()
            >>> tables = store.get_all_tables()
            >>> "revenue" in tables
            True
        """
        if self.collection is None:
            raise Exception("Vector store not initialized. Call initialize_store() first.")
        
        try:
            all_data = self.collection.get()
            table_names = set()
            for metadata in all_data.get('metadatas', []):
                if metadata and 'table_name' in metadata:
                    table_names.add(metadata['table_name'])
            return sorted(list(table_names))
        except Exception:
            return []

