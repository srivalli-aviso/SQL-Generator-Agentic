"""
Configuration Module for Query Plan Agent

Contains default configuration settings for the Query Plan Agent.
"""

from dataclasses import dataclass


@dataclass
class QueryPlanConfig:
    """
    Configuration class for Query Plan Agent.
    
    Contains all configurable parameters for query plan generation.
    """
    
    # Groq API Configuration
    model: str = "openai/gpt-oss-120b"  # Groq model to use (120B MoE model, excellent for complex reasoning)
    temperature: float = 0.1  # Temperature for generation (configurable, lower = more deterministic)
    max_tokens: int = 3000  # Maximum tokens in response (higher for detailed plans)
    
    # Input Configuration
    subproblems_dir: str = "../Subproblem_Agent/results"  # Directory containing subproblem JSON files
    schema_path: str = "../Schema_Linking_Agent/cisco_stage_app_modified_m_schema.json"  # Full schema path (optional)
    
    # Output Configuration
    results_dir: str = "./results"  # Directory to save query plan results
    output_format: str = "json"  # Output format (always JSON)

