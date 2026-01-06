"""
Embedding Service Module

Provides functionality to generate embeddings using sentence-transformers (local model).
Since Groq doesn't have an embeddings API, we use a local embedding model.
Handles batch processing, error handling, and retry logic for embedding generation.
"""

import os
from typing import List, Dict, Optional
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:
    raise ImportError(
        "sentence-transformers package is required for embeddings. "
        "Install it with: pip install sentence-transformers"
    )


class EmbeddingService:
    """
    Service for generating embeddings using sentence-transformers (local model).
    
    Note: Groq doesn't provide an embeddings API, so we use a local embedding model
    from sentence-transformers. This runs locally and doesn't require an API key.
    This class provides embedding generation functionality with batch processing.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "Alibaba-NLP/gte-large-en-v1.5"):
        """
        Initialize the Embedding Service.
        
        Args:
            api_key: Not used (kept for compatibility). Groq API key is not needed
                   for local embeddings.
            model: Embedding model to use. Options:
                  - "Alibaba-NLP/gte-large-en-v1.5" (default, 1024 dimensions, high quality)
                  - "all-MiniLM-L6-v2" (384 dimensions, fast, good quality)
                  - "all-mpnet-base-v2" (768 dimensions, better quality, slower)
                  - "all-MiniLM-L12-v2" (384 dimensions, better than L6)
        
        Note:
            The model will be downloaded on first use and cached locally.
            Models with "gte" or "Alibaba" in the name require trust_remote_code=True.
        """
        # Load the sentence transformer model
        self.model_name = model
        print(f"Loading embedding model: {model}...")
        
        # Some models (like gte-large-en-v1.5) require trust_remote_code
        if "gte" in model.lower() or "Alibaba" in model:
            print("Using trust_remote_code=True (required for this model)")
            self.model = SentenceTransformer(model, trust_remote_code=True)
        else:
            self.model = SentenceTransformer(model)
        
        print(f"Model loaded successfully. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: The text string to embed.
        
        Returns:
            List of floats representing the embedding vector.
        
        Raises:
            Exception: If embedding generation fails.
        
        Example:
            >>> service = EmbeddingService()
            >>> embedding = service.embed_text("revenue by region")
            >>> len(embedding)
            768
        """
        try:
            # Generate embedding using sentence-transformers
            embedding = self.model.encode(text, convert_to_numpy=False, normalize_embeddings=True)
            return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
        except Exception as e:
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for a batch of text strings.
        
        Processes texts in batches to optimize API calls and handle rate limits.
        If a batch fails, it retries individual items in that batch.
        
        Args:
            texts: List of text strings to embed.
            batch_size: Number of texts to process in each batch. Default is 100.
        
        Returns:
            List of embedding vectors, one for each input text.
        
        Raises:
            Exception: If embedding generation fails for all retries.
        
        Example:
            >>> service = EmbeddingService()
            >>> texts = ["revenue", "region", "segment"]
            >>> embeddings = service.embed_batch(texts, batch_size=10)
            >>> len(embeddings)
            3
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                # Generate embeddings for the batch using sentence-transformers
                batch_embeddings = self.model.encode(
                    batch, 
                    convert_to_numpy=False, 
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
                # Convert to list format
                for emb in batch_embeddings:
                    all_embeddings.append(emb.tolist() if hasattr(emb, 'tolist') else list(emb))
            except Exception as e:
                # If batch fails, try individual items
                print(f"Batch embedding failed, processing individually: {str(e)}")
                for text in batch:
                    try:
                        embedding = self.embed_text(text)
                        all_embeddings.append(embedding)
                    except Exception as individual_error:
                        print(f"Failed to embed text '{text[:50]}...': {str(individual_error)}")
                        # Add zero vector as placeholder
                        dim = self.model.get_sentence_embedding_dimension()
                        all_embeddings.append([0.0] * dim)
        
        return all_embeddings
    
    def embed_schema_element(
        self, 
        element: Dict, 
        element_type: str = "table"
    ) -> Dict:
        """
        Generate embedding for a schema element (table or column) with metadata.
        
        Creates an embedding for a table or column along with its metadata.
        The metadata includes element type, table name, column name (if applicable),
        and description.
        
        Args:
            element: Dictionary containing schema element information.
                   For tables: {"table_name": str, "table_description": str, ...}
                   For columns: {"table_name": str, "column_name": str, 
                                "column_description": str, "type": str, ...}
            element_type: Type of element - "table" or "column". Default is "table".
        
        Returns:
            Dictionary containing:
            - "embedding": List[float] - The embedding vector
            - "element_type": str - Type of element (table/column)
            - "table_name": str - Name of the table
            - "column_name": Optional[str] - Name of column (if element_type is "column")
            - "description": str - Description of the element
            - "metadata": Dict - Additional metadata from the element
        
        Example:
            >>> service = EmbeddingService()
            >>> table_element = {
            ...     "table_name": "revenue",
            ...     "table_description": "Revenue data by region"
            ... }
            >>> result = service.embed_schema_element(table_element, "table")
            >>> "embedding" in result
            True
        """
        if element_type == "table":
            text = f"{element.get('table_name', '')}: {element.get('table_description', '')}"
            description = element.get('table_description', '')
            column_name = None
        else:  # column
            table_name = element.get('table_name', '')
            column_name = element.get('column_name', '')
            column_type = element.get('type', '')
            column_description = element.get('column_description', '')
            text = f"{table_name}.{column_name} ({column_type}): {column_description}"
            description = column_description
        
        embedding = self.embed_text(text)
        
        return {
            "embedding": embedding,
            "element_type": element_type,
            "table_name": element.get('table_name', ''),
            "column_name": column_name,
            "description": description,
            "metadata": element
        }

