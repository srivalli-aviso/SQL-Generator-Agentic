"""
Configuration Module for Subproblem Agent

Contains default configuration settings for the Subproblem Agent.
"""

from dataclasses import dataclass


@dataclass
class SubproblemConfig:
    """
    Configuration class for Subproblem Agent.
    
    Contains all configurable parameters for query decomposition.
    """
    
    # Groq API Configuration
    model: str = "llama-3.1-70b-versatile"  # Groq model to use
    temperature: float = 0.1  # Temperature for generation (lower = more deterministic)
    max_tokens: int = 2000  # Maximum tokens in response
    
    # Decomposition Configuration
    enable_fallback: bool = True  # Enable fallback decomposition on failure
    retry_attempts: int = 2  # Number of retry attempts on API failure
    
    # Output Configuration
    include_metadata: bool = True  # Include complexity and flags in output
    strict_json: bool = True  # Require strict JSON format

