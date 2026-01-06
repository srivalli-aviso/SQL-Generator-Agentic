"""
Foreign Key Expander Module

Traverses foreign key relationships in M-Schema to include related tables
based on configurable hop limits. Uses graph traversal algorithms (BFS)
to find connected tables.
"""

from typing import List, Set, Dict


class ForeignKeyExpander:
    """
    Expands table selection by including related tables via foreign keys.
    
    This class implements graph traversal to find tables connected through
    foreign key relationships. Supports configurable hop limits (1-hop,
    2-hop, etc.) to control how far to traverse the relationship graph.
    """
    
    def __init__(self, mschema: Dict):
        """
        Initialize the Foreign Key Expander.
        
        Args:
            mschema: Dictionary containing the M-Schema structure with:
                    - "foreign_keys": List - List of foreign key relationships
                    - "tables": Dict - Dictionary of tables
        
        Example:
            >>> schema = load_schema("schema.json")
            >>> expander = ForeignKeyExpander(schema)
        """
        self.mschema = mschema
        self.foreign_keys = mschema.get('foreign_keys', [])
        self.tables = mschema.get('tables', {})
        # Build adjacency list for faster traversal
        self._build_adjacency_list()
    
    def _build_adjacency_list(self):
        """
        Build adjacency list representation of foreign key relationships.
        
        Creates a graph structure where each table points to tables it
        references (via foreign keys) and tables that reference it.
        This enables efficient graph traversal.
        
        Returns:
            None (modifies self.adjacency_list)
        
        Example:
            >>> expander = ForeignKeyExpander(schema)
            >>> "table1" in expander.adjacency_list
            True
        """
        self.adjacency_list = {}
        
        # Initialize adjacency list for all tables
        for table_name in self.tables.keys():
            self.adjacency_list[table_name] = set()
        
        # Add edges based on foreign keys
        for fk in self.foreign_keys:
            # fk format: [source_table, source_column, ref_schema, ref_table, ref_column]
            if len(fk) >= 5:
                source_table = fk[0]
                ref_table = fk[3]
                
                # Add bidirectional edges (table A references B, so B is related to A)
                if source_table in self.adjacency_list:
                    self.adjacency_list[source_table].add(ref_table)
                if ref_table in self.adjacency_list:
                    self.adjacency_list[ref_table].add(source_table)
    
    def get_related_tables(
        self, 
        table_names: List[str], 
        max_hops: int = 1
    ) -> Set[str]:
        """
        Get all tables related to the given tables via foreign keys.
        
        Traverses the foreign key graph starting from the given tables
        and includes all tables within the specified number of hops.
        Uses BFS (Breadth-First Search) for traversal.
        
        Args:
            table_names: List of table names to start traversal from.
            max_hops: Maximum number of hops to traverse. 
                    1 = directly connected tables only
                    2 = tables connected through one intermediate table
                    Default is 1.
        
        Returns:
            Set of table names including the original tables and all
            related tables within the hop limit.
        
        Example:
            >>> expander = ForeignKeyExpander(schema)
            >>> related = expander.get_related_tables(["orders"], max_hops=1)
            >>> "customers" in related  # If orders references customers
            True
        """
        if max_hops < 0:
            return set(table_names)
        
        result_set = set(table_names)
        current_level = set(table_names)
        visited = set(table_names)
        
        # BFS traversal for each hop
        for hop in range(max_hops):
            next_level = set()
            
            for table in current_level:
                # Get neighbors (related tables)
                neighbors = self.adjacency_list.get(table, set())
                
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.add(neighbor)
                        result_set.add(neighbor)
            
            current_level = next_level
            
            # Stop if no more tables to explore
            if not current_level:
                break
        
        return result_set
    
    def traverse_foreign_keys(
        self, 
        table: str, 
        visited: Set[str], 
        current_hop: int, 
        max_hops: int
    ) -> Set[str]:
        """
        Recursively traverse foreign key relationships from a starting table.
        
        Recursive helper function for graph traversal. Explores the foreign
        key graph starting from a table and collects all reachable tables
        within the hop limit.
        
        Args:
            table: Name of the current table being explored.
            visited: Set of already visited table names (to avoid cycles).
            current_hop: Current hop level (0 = starting table).
            max_hops: Maximum number of hops to traverse.
        
        Returns:
            Set of table names reachable from the starting table.
        
        Example:
            >>> expander = ForeignKeyExpander(schema)
            >>> visited = set()
            >>> related = expander.traverse_foreign_keys("orders", visited, 0, 1)
            >>> len(related) > 0
            True
        """
        if current_hop > max_hops or table in visited:
            return set()
        
        visited.add(table)
        result = {table}
        
        # Get neighbors
        neighbors = self.adjacency_list.get(table, set())
        for neighbor in neighbors:
            if neighbor not in visited:
                result.update(
                    self.traverse_foreign_keys(neighbor, visited, current_hop + 1, max_hops)
                )
        
        return result
    
    def expand_with_foreign_keys(
        self, 
        selected_tables: List[str], 
        max_hops: int = 1
    ) -> List[str]:
        """
        Expand a list of selected tables by including related tables via foreign keys.
        
        Takes a list of initially selected tables and expands it to include
        all tables connected through foreign key relationships within the
        specified hop limit. This ensures that related tables are included
        even if they weren't directly selected by the query.
        
        Args:
            selected_tables: List of table names initially selected (e.g., by query).
            max_hops: Maximum number of hops to traverse foreign key relationships.
                     Default is 1 (directly connected tables only).
        
        Returns:
            List of table names including the original selection and all
            related tables within the hop limit. Preserves order where possible.
        
        Example:
            >>> expander = ForeignKeyExpander(schema)
            >>> selected = ["orders"]
            >>> expanded = expander.expand_with_foreign_keys(selected, max_hops=1)
            >>> len(expanded) >= len(selected)
            True
        """
        if max_hops == 0:
            return selected_tables
        
        # Get all related tables
        related_tables = self.get_related_tables(selected_tables, max_hops)
        
        # Convert to list and preserve original order, then add new ones
        result = list(selected_tables)
        for table in related_tables:
            if table not in result:
                result.append(table)
        
        return result

