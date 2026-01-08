"""
Configuration Module for SQL Agent

Contains default configuration settings for the SQL Agent.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SQLAgentConfig:
    """
    Configuration class for SQL Agent.
    
    Contains all configurable parameters for SQL generation from query plans.
    """
    
    # Groq API Configuration
    model: str = "openai/gpt-oss-120b"  # Same as Query Plan Agent (120B MoE model)
    temperature: float = 0.1  # Low temperature (0-0.2), configurable
    max_tokens: int = 2000  # For SQL generation
    
    # Input Configuration
    query_plans_dir: str = "../Query_Plan_Agent/results"  # Directory with query plan JSON files
    filtered_schema_dir: str = "../Schema_Linking_Agent/results"  # Directory with filtered schema JSON files
    full_schema_path: Optional[str] = "../Schema_Linking_Agent/cisco_stage_app_modified_m_schema.json"  # Full schema path as fallback
    
    # Output Configuration
    results_dir: str = "./results"
    sql_format: str = "pretty"  # "pretty" | "compact" | "none"
    
    # SQL Generation Configuration
    enable_fallback: bool = True  # Enable fallback generation
    enable_validation: bool = False  # Optional SQL validation (configurable)
    enable_execution: bool = True  # Optional database execution (configurable)
    
    # Database Configuration (for execution)
    database_dialect: str = "clickhouse"  # Primary dialect
    db_connection_string: Optional[str] = None  # For execution testing

