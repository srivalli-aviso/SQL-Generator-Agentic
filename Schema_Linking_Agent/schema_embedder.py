"""
Schema Embedding Generator Module

Converts M-Schema JSON into embeddings by extracting text representations
of tables and columns, then generating embeddings for each element.
"""

import json
from typing import Dict, List, Optional
from embedding_service import EmbeddingService


class SchemaEmbedder:
    """
    Generates embeddings for M-Schema elements (tables and columns).
    
    This class processes M-Schema JSON files and creates embeddings
    for tables and columns by extracting relevant text information
    (names, descriptions, types) and generating embeddings using
    the embedding service.
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        """
        Initialize the Schema Embedder.
        
        Args:
            embedding_service: An instance of EmbeddingService to generate embeddings.
        
        Example:
            >>> from embedding_service import EmbeddingService
            >>> emb_service = EmbeddingService()
            >>> embedder = SchemaEmbedder(emb_service)
        """
        self.embedding_service = embedding_service
    
    def load_schema(self, json_path: str) -> Dict:
        """
        Load M-Schema from JSON file.
        
        Reads and parses the M-Schema JSON file into a Python dictionary.
        
        Args:
            json_path: Path to the M-Schema JSON file.
        
        Returns:
            Dictionary containing the M-Schema structure with keys:
            - "db_id": str - Database identifier
            - "schema": str - Schema name
            - "tables": Dict - Dictionary of tables
            - "foreign_keys": List - List of foreign key relationships
        
        Raises:
            FileNotFoundError: If the JSON file doesn't exist.
            json.JSONDecodeError: If the JSON file is invalid.
        
        Example:
            >>> embedder = SchemaEmbedder(embedding_service)
            >>> schema = embedder.load_schema("./schema.json")
            >>> "tables" in schema
            True
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_related_tables_via_fk(self, table_name: str, mschema: Dict) -> List[str]:
        """
        Get list of table names that are related to the given table via foreign keys.
        
        Finds all foreign key relationships where the given table is either
        the source (referencing) or target (referenced) table.
        
        Args:
            table_name: Full name of the table (e.g., "schema.table_name").
            mschema: Dictionary containing the M-Schema structure with:
                    - "foreign_keys": List - List of foreign key relationships
        
        Returns:
            List of related table names (strings). Empty list if no relationships found.
        
        Example:
            >>> schema = {"foreign_keys": [{"source_table": "orders", "target_table": "customers"}]}
            >>> related = embedder.get_related_tables_via_fk("orders", schema)
            >>> "customers" in related
            True
        """
        foreign_keys = mschema.get('foreign_keys', [])
        related_tables = set()
        
        for fk in foreign_keys:
            # Handle different FK formats
            source_table = fk.get('source_table') or fk.get('table') or fk.get('from_table')
            target_table = fk.get('target_table') or fk.get('referenced_table') or fk.get('to_table')
            
            if source_table == table_name and target_table:
                related_tables.add(target_table)
            elif target_table == table_name and source_table:
                related_tables.add(source_table)
        
        return sorted(list(related_tables))
    
    def extract_embeddable_text(
        self, 
        table_name: str,
        table_data: Dict, 
        column_data: Optional[Dict] = None,
        mschema: Optional[Dict] = None
    ) -> str:
        """
        Extract text representation for embedding from table or column data.
        
        Creates a text string that represents a table or column for embedding.
        For tables: includes table name, description, and foreign key relationships.
        For columns: includes table name, column name, type, description, and all examples.
        
        Args:
            table_name: Full name of the table (e.g., "schema.table_name").
            table_data: Dictionary containing table information with keys:
                      - "table_description": str - Description of the table
                      - "fields": Dict - Dictionary of column definitions
            column_data: Optional dictionary containing column information with keys:
                        - "type": str - Column data type
                        - "column_description": str - Description of the column
                        - "examples": List - List of example values
                       If None, extracts table-level text. Default is None.
            mschema: Optional M-Schema dictionary for accessing foreign keys.
                    Required for table-level FK information. Default is None.
        
        Returns:
            String representation suitable for embedding.
            Format for tables: "table_name: table_description. Related to: [table1, table2] via foreign keys"
            Format for columns: "table_name.column_name (type): column_description. Examples: [val1, val2, val3]"
        
        Example:
            >>> table_data = {"table_description": "Revenue data", "fields": {...}}
            >>> text = embedder.extract_embeddable_text("revenue", table_data, mschema=schema)
            >>> "revenue" in text.lower()
            True
        """
        if column_data is None:
            # Table-level text with foreign keys
            table_desc = table_data.get('table_description', '')
            base_text = f"{table_name}: {table_desc}"
            
            # Add foreign key information if available
            if mschema:
                related_tables = self.get_related_tables_via_fk(table_name, mschema)
                if related_tables:
                    fk_text = f" Related to: {', '.join(related_tables)} via foreign keys"
                    return f"{base_text}.{fk_text}"
            
            return base_text
        else:
            # Column-level text with examples
            column_name = list(column_data.keys())[0] if isinstance(column_data, dict) else None
            if column_name:
                col_info = column_data[column_name] if isinstance(column_data, dict) else column_data
                col_type = col_info.get('type', '')
                col_desc = col_info.get('column_description', '')
                base_text = f"{table_name}.{column_name} ({col_type}): {col_desc}"
                
                # Add examples if available
                examples = col_info.get('examples', [])
                if examples:
                    # Include all examples (no restriction)
                    examples_str = ', '.join(str(ex) for ex in examples)
                    return f"{base_text}. Examples: [{examples_str}]"
                
                return base_text
            else:
                # Fallback
                col_type = column_data.get('type', '')
                col_desc = column_data.get('column_description', '')
                base_text = f"{table_name} ({col_type}): {col_desc}"
                
                # Add examples if available
                examples = column_data.get('examples', [])
                if examples:
                    examples_str = ', '.join(str(ex) for ex in examples)
                    return f"{base_text}. Examples: [{examples_str}]"
                
                return base_text
    
    def embed_full_schema(self, mschema: Dict) -> List[Dict]:
        """
        Generate embeddings for all tables and columns in the M-Schema.
        
        Processes the entire M-Schema and creates embeddings for:
        1. Each table (table name + description + foreign key relationships)
        2. Each column in each table (table.column + type + description + all examples)
        
        Args:
            mschema: Dictionary containing the M-Schema structure with:
                    - "tables": Dict - Dictionary of tables
                    - "foreign_keys": List - List of foreign key relationships
                    - Other M-Schema fields
        
        Returns:
            List of dictionaries, each containing:
            - "embedding": List[float] - The embedding vector
            - "element_type": str - "table" or "column"
            - "table_name": str - Full table name
            - "column_name": Optional[str] - Column name (if column)
            - "description": str - Description text
            - "metadata": Dict - Additional metadata
        
        Example:
            >>> schema = embedder.load_schema("./schema.json")
            >>> embeddings = embedder.embed_full_schema(schema)
            >>> len(embeddings) > 0
            True
        """
        all_embeddings = []
        tables = mschema.get('tables', {})
        
        # Process each table
        for table_name, table_data in tables.items():
            # Extract table-level text (with foreign keys) and create embedding
            table_text = self.extract_embeddable_text(table_name, table_data, mschema=mschema)
            table_embedding = self.embedding_service.embed_text(table_text)
            
            all_embeddings.append({
                "embedding": table_embedding,
                "element_type": "table",
                "table_name": table_name,
                "column_name": None,
                "description": table_data.get('table_description', ''),
                "metadata": {
                    "table_name": table_name,
                    "table_description": table_data.get('table_description', '')
                }
            })
            
            # Process each column in the table
            fields = table_data.get('fields', {})
            for column_name, column_info in fields.items():
                # Extract column-level text (with all examples) and create embedding
                column_text = self.extract_embeddable_text(
                    table_name, 
                    table_data, 
                    {column_name: column_info},
                    mschema=mschema
                )
                column_embedding = self.embedding_service.embed_text(column_text)
                
                all_embeddings.append({
                    "embedding": column_embedding,
                    "element_type": "column",
                    "table_name": table_name,
                    "column_name": column_name,
                    "description": column_info.get('column_description', ''),
                    "metadata": {
                        "table_name": table_name,
                        "column_name": column_name,
                        "type": column_info.get('type', ''),
                        "column_description": column_info.get('column_description', ''),
                        "primary_key": column_info.get('primary_key', False)
                    }
                })
        
        return all_embeddings
    
    def save_embeddings(self, embeddings: List[Dict], output_path: str):
        """
        Save embeddings to disk for caching.
        
        Saves embeddings to a JSON file for later use, avoiding
        re-computation of embeddings. The embeddings are saved
        with their associated metadata.
        
        Args:
            embeddings: List of embedding dictionaries to save.
            output_path: Path to the output JSON file.
        
        Example:
            >>> embeddings = embedder.embed_full_schema(schema)
            >>> embedder.save_embeddings(embeddings, "./embeddings_cache.json")
        """
        # Convert embeddings to JSON-serializable format
        serializable_embeddings = []
        for emb in embeddings:
            serializable_emb = {
                "element_type": emb.get("element_type"),
                "table_name": emb.get("table_name"),
                "column_name": emb.get("column_name"),
                "description": emb.get("description"),
                "metadata": emb.get("metadata"),
                "embedding": emb.get("embedding")  # List of floats is JSON-serializable
            }
            serializable_embeddings.append(serializable_emb)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_embeddings, f, indent=2, ensure_ascii=False)

