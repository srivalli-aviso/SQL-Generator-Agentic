"""
Reranker Module

Provides reranking functionality to improve accuracy of schema filtering.
Uses cross-encoder reranker (BAAI/bge-reranker-base) as primary method,
with LLM-based reranker (Groq API) as optional fallback/validation layer.
"""

import os
from typing import List, Dict, Optional
try:
    from sentence_transformers import CrossEncoder  # type: ignore
except ImportError:
    raise ImportError(
        "sentence-transformers package is required for reranking. "
        "Install it with: pip install sentence-transformers"
    )

try:
    from groq import Groq  # type: ignore
except ImportError:
    Groq = None  # Optional dependency


class Reranker:
    """
    Reranker for improving schema filtering accuracy.
    
    Implements a two-stage reranking system:
    1. Cross-encoder reranker (primary) - Uses BAAI/bge-reranker-base
    2. LLM-based reranker (fallback) - Uses Groq API for validation
    
    The reranker takes initial candidates from vector search and reranks
    them based on query-candidate relevance, improving precision.
    """
    
    def __init__(
        self,
        model: str = "BAAI/bge-reranker-base",
        enable_llm_fallback: bool = False,
        llm_model: str = "llama-3.1-70b-versatile",
        llm_validation_threshold: float = 0.7
    ):
        """
        Initialize the Reranker.
        
        Loads the cross-encoder model for reranking. Optionally configures
        LLM-based reranker for fallback/validation scenarios.
        
        Args:
            model: Cross-encoder model name from sentence-transformers.
                  Default is "BAAI/bge-reranker-base".
                  Other options: "BAAI/bge-reranker-large", "cross-encoder/ms-marco-MiniLM-L-12-v2"
            enable_llm_fallback: Whether to enable LLM-based reranker as fallback.
                                Default is False (not enabled by default).
            llm_model: Groq model to use for LLM reranking. Default is "llama-3.1-70b-versatile".
            llm_validation_threshold: Confidence threshold below which LLM validation is triggered.
                                     Default is 0.7. Only used if enable_llm_fallback is True.
        
        Raises:
            ValueError: If enable_llm_fallback is True but GROQ_API_KEY is not set.
            ImportError: If sentence-transformers is not installed.
        
        Example:
            >>> reranker = Reranker(model="BAAI/bge-reranker-base")
            >>> reranker.enabled
            True
        """
        self.model_name = model
        self.enable_llm_fallback = enable_llm_fallback
        self.llm_validation_threshold = llm_validation_threshold
        
        # Lazy loading: Don't load model until first use
        # This prevents blocking during initialization if download is slow
        self.cross_encoder = None
        self._model_loaded = False
        
        # Initialize LLM client if fallback is enabled
        self.llm_client = None
        self.llm_model = llm_model
        if enable_llm_fallback:
            if Groq is None:
                raise ValueError(
                    "groq package is required for LLM fallback. "
                    "Install it with: pip install groq"
                )
            if "GROQ_API_KEY" not in os.environ:
                raise ValueError(
                    "GROQ_API_KEY environment variable is not set. "
                    "Required when enable_llm_fallback=True"
                )
            self.llm_client = Groq()
            print(f"✓ LLM fallback enabled (model: {llm_model})")
    
    def _format_candidate_text(self, candidate: Dict) -> str:
        """
        Format a candidate (table or column) into text for reranking.
        
        Extracts relevant information from candidate metadata and formats
        it into a text string that can be used for reranking with the
        cross-encoder model.
        
        Args:
            candidate: Dictionary containing candidate information with keys:
                     - "metadata": Dict - Contains table_name, column_name, description, etc.
                     - "similarity": float - Original similarity score
                     - Other metadata fields
        
        Returns:
            Formatted text string representing the candidate.
            Format: "table_name: description" for tables
            Format: "table_name.column_name (type): description" for columns
        
        Example:
            >>> candidate = {
            ...     "metadata": {
            ...         "table_name": "metrics",
            ...         "table_description": "Financial metrics"
            ...     }
            ... }
            >>> text = reranker._format_candidate_text(candidate)
            >>> "metrics" in text
            True
        """
        metadata = candidate.get('metadata', {})
        element_type = metadata.get('element_type', 'unknown')
        
        if element_type == 'table':
            table_name = metadata.get('table_name', '')
            table_desc = metadata.get('table_description', metadata.get('description', ''))
            return f"{table_name}: {table_desc}"
        elif element_type == 'column':
            table_name = metadata.get('table_name', '')
            column_name = metadata.get('column_name', '')
            col_type = metadata.get('type', '')
            col_desc = metadata.get('column_description', metadata.get('description', ''))
            return f"{table_name}.{column_name} ({col_type}): {col_desc}"
        else:
            # Fallback: use description or metadata
            description = metadata.get('description', '')
            table_name = metadata.get('table_name', '')
            column_name = metadata.get('column_name', '')
            if column_name:
                return f"{table_name}.{column_name}: {description}"
            return f"{table_name}: {description}"
    
    def _ensure_model_loaded(self):
        """
        Ensure the cross-encoder model is loaded (lazy loading).
        
        Loads the model on first use to avoid blocking during initialization.
        This is especially useful when the model download is slow or interrupted.
        
        Raises:
            Exception: If model loading fails (network issues, disk space, etc.)
        """
        if not self._model_loaded:
            print(f"Loading reranker model: {self.model_name}...")
            print("   (This may take a few minutes on first run - downloading ~1.1GB)")
            try:
                self.cross_encoder = CrossEncoder(self.model_name)
                self._model_loaded = True
                print(f"✓ Reranker model loaded successfully")
            except Exception as e:
                print(f"✗ Failed to load reranker model: {str(e)}")
                print("   Tip: Check your internet connection and try again.")
                print("   Or disable reranker by setting reranker_enabled=False in config")
                raise
    
    def _rerank_with_cross_encoder(
        self,
        query: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Rerank candidates using cross-encoder model.
        
        Uses a cross-encoder model to score each query-candidate pair.
        Cross-encoders process query and candidate together, providing
        more accurate relevance scores than bi-encoders.
        
        Args:
            query: Natural language query from the user.
            candidates: List of candidate dictionaries from vector search.
                      Each candidate should have:
                      - "metadata": Dict - Candidate metadata
                      - "similarity": float - Original similarity score
                      - "id": str - Unique identifier
        
        Returns:
            List of candidate dictionaries, reranked by relevance score.
            Each dictionary includes:
            - All original fields
            - "reranker_score": float - Reranker relevance score (0-1, higher is better)
            - "metadata": Updated with reranker_score
        
        Example:
            >>> query = "Show me revenue by region"
            >>> candidates = [
            ...     {"metadata": {"table_name": "metrics"}, "similarity": 0.8},
            ...     {"metadata": {"table_name": "users"}, "similarity": 0.7}
            ... ]
            >>> reranked = reranker._rerank_with_cross_encoder(query, candidates)
            >>> len(reranked) == len(candidates)
            True
            >>> reranked[0]["reranker_score"] > 0
            True
        """
        if not candidates:
            return []
        
        # Ensure model is loaded (lazy loading)
        self._ensure_model_loaded()
        
        # Format candidates into text
        candidate_texts = [self._format_candidate_text(cand) for cand in candidates]
        
        # Create query-candidate pairs for cross-encoder
        pairs = [[query, cand_text] for cand_text in candidate_texts]
        
        # Score all pairs in batch
        scores = self.cross_encoder.predict(pairs)
        
        # Normalize scores to [0, 1] range (cross-encoder outputs may vary)
        # Apply sigmoid if needed, or use min-max normalization
        min_score = float(scores.min())
        max_score = float(scores.max())
        if max_score > min_score:
            normalized_scores = (scores - min_score) / (max_score - min_score)
        else:
            normalized_scores = scores
        
        # Add reranker scores to candidates and sort
        reranked_candidates = []
        for i, candidate in enumerate(candidates):
            reranker_score = float(normalized_scores[i])
            candidate_copy = candidate.copy()
            candidate_copy['reranker_score'] = reranker_score
            
            # Add to metadata as well
            if 'metadata' not in candidate_copy:
                candidate_copy['metadata'] = {}
            candidate_copy['metadata']['reranker_score'] = reranker_score
            
            reranked_candidates.append(candidate_copy)
        
        # Sort by reranker score (descending)
        reranked_candidates.sort(key=lambda x: x['reranker_score'], reverse=True)
        
        return reranked_candidates
    
    def _rerank_with_llm(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        Rerank candidates using LLM (Groq API) as fallback/validation.
        
        Uses Groq API to validate and rerank candidates when cross-encoder
        confidence is low or as a validation layer. This is an optional
        fallback mechanism, not enabled by default.
        
        Args:
            query: Natural language query from the user.
            candidates: List of candidate dictionaries to rerank.
            top_k: Number of top candidates to return.
        
        Returns:
            List of top-K candidate dictionaries, reranked by LLM.
            Each dictionary includes:
            - All original fields
            - "reranker_score": float - LLM-based relevance score
            - "metadata": Updated with reranker_score and llm_validated flag
        
        Raises:
            ValueError: If LLM client is not initialized.
            Exception: If API call fails.
        
        Example:
            >>> query = "Show me revenue"
            >>> candidates = [{"metadata": {"table_name": "metrics"}}]
            >>> reranked = reranker._rerank_with_llm(query, candidates, top_k=5)
            >>> len(reranked) <= top_k
            True
        """
        if self.llm_client is None:
            raise ValueError("LLM client not initialized. Set enable_llm_fallback=True.")
        
        if not candidates:
            return []
        
        # Format candidates for LLM
        candidate_texts = []
        for i, cand in enumerate(candidates):
            cand_text = self._format_candidate_text(cand)
            candidate_texts.append(f"{i+1}. {cand_text}")
        
        candidates_list = "\n".join(candidate_texts)
        
        # Create prompt for LLM reranking
        system_prompt = """You are an expert at ranking database schema elements by relevance to user queries.

Your task is to rank the provided candidates by their relevance to the user query.
Return a JSON object with candidate indices (1-based) as keys and relevance scores (0-1) as values.
Higher scores indicate better relevance."""
        
        user_prompt = f"""# USER QUERY #
{query}

# CANDIDATES #
{candidates_list}

# TASK #
Rank these candidates by relevance to the query. Return JSON with format:
{{"1": 0.95, "2": 0.87, "3": 0.72, ...}}

Return ONLY the JSON object, no additional text."""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            import json
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            scores_dict = json.loads(response_text)
            
            # Map scores back to candidates
            reranked_candidates = []
            for i, candidate in enumerate(candidates):
                score_key = str(i + 1)
                reranker_score = float(scores_dict.get(score_key, 0.5))
                
                candidate_copy = candidate.copy()
                candidate_copy['reranker_score'] = reranker_score
                candidate_copy['llm_validated'] = True
                
                if 'metadata' not in candidate_copy:
                    candidate_copy['metadata'] = {}
                candidate_copy['metadata']['reranker_score'] = reranker_score
                candidate_copy['metadata']['llm_validated'] = True
                
                reranked_candidates.append(candidate_copy)
            
            # Sort by reranker score
            reranked_candidates.sort(key=lambda x: x['reranker_score'], reverse=True)
            
            return reranked_candidates[:top_k]
            
        except Exception as e:
            print(f"⚠ Warning: LLM reranking failed: {str(e)}")
            # Fallback: return original candidates with default scores
            return candidates[:top_k]
    
    def rerank_tables(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        Rerank table candidates based on query relevance.
        
        Takes initial table candidates from vector search and reranks them
        using cross-encoder model. Optionally uses LLM validation if enabled
        and confidence is low.
        
        Args:
            query: Natural language query from the user.
            candidates: List of table candidate dictionaries from vector search.
                       Each should have:
                       - "metadata": Dict with table_name, table_description, element_type="table"
                       - "similarity": float - Original similarity score
                       - "id": str - Unique identifier
            top_k: Number of top tables to return after reranking.
        
        Returns:
            List of top-K table candidate dictionaries, reranked by relevance.
            Each dictionary includes:
            - All original fields
            - "reranker_score": float - Reranker relevance score (0-1)
            - "metadata": Updated with reranker_score
        
        Example:
            >>> query = "Show me revenue by region"
            >>> candidates = [
            ...     {"metadata": {"table_name": "metrics", "element_type": "table"}}
            ... ]
            >>> reranked = reranker.rerank_tables(query, candidates, top_k=10)
            >>> len(reranked) <= top_k
            True
            >>> "reranker_score" in reranked[0]
            True
        """
        if not candidates:
            return []
        
        # Primary: Cross-encoder reranking
        reranked = self._rerank_with_cross_encoder(query, candidates)
        
        # Optional: LLM validation if enabled and confidence is low
        if self.enable_llm_fallback and reranked:
            top_score = reranked[0].get('reranker_score', 0.0)
            if top_score < self.llm_validation_threshold:
                print(f"⚠ Low confidence ({top_score:.2f}), using LLM validation...")
                try:
                    reranked = self._rerank_with_llm(query, candidates, top_k)
                except Exception as e:
                    print(f"⚠ LLM validation failed, using cross-encoder results: {str(e)}")
        
        return reranked[:top_k]
    
    def rerank_columns(
        self,
        query: str,
        table_name: str,
        candidates: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        Rerank column candidates for a specific table based on query relevance.
        
        Takes initial column candidates from vector search and reranks them
        using cross-encoder model. Optionally uses LLM validation if enabled
        and confidence is low.
        
        Args:
            query: Natural language query from the user.
            table_name: Name of the table these columns belong to.
                       Used for context in reranking.
            candidates: List of column candidate dictionaries from vector search.
                       Each should have:
                       - "metadata": Dict with table_name, column_name, type, column_description, element_type="column"
                       - "similarity": float - Original similarity score
                       - "id": str - Unique identifier
            top_k: Number of top columns to return after reranking.
        
        Returns:
            List of top-K column candidate dictionaries, reranked by relevance.
            Each dictionary includes:
            - All original fields
            - "reranker_score": float - Reranker relevance score (0-1)
            - "metadata": Updated with reranker_score
        
        Example:
            >>> query = "Show me revenue amount"
            >>> candidates = [
            ...     {"metadata": {"table_name": "metrics", "column_name": "won_amount", "element_type": "column"}}
            ... ]
            >>> reranked = reranker.rerank_columns(query, "metrics", candidates, top_k=15)
            >>> len(reranked) <= top_k
            True
            >>> "reranker_score" in reranked[0]
            True
        """
        if not candidates:
            return []
        
        # Primary: Cross-encoder reranking
        reranked = self._rerank_with_cross_encoder(query, candidates)
        
        # Optional: LLM validation if enabled and confidence is low
        if self.enable_llm_fallback and reranked:
            top_score = reranked[0].get('reranker_score', 0.0)
            if top_score < self.llm_validation_threshold:
                print(f"⚠ Low confidence ({top_score:.2f}), using LLM validation...")
                try:
                    reranked = self._rerank_with_llm(query, candidates, top_k)
                except Exception as e:
                    print(f"⚠ LLM validation failed, using cross-encoder results: {str(e)}")
        
        return reranked[:top_k]

