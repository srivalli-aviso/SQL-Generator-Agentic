"""
Configuration module for M-Schema generation.

This module centralizes all configuration settings used across the M-Schema module,
including database connections, LLM settings, file paths, and schema generation parameters.
"""

import os
from typing import Optional


class MSchemaConfig:
    """Configuration class for M-Schema module."""
    
    # ========== Database Connection ==========
    CH_DB_HOST: Optional[str] = os.getenv('CH_DB_HOST')
    CH_DB_USER: Optional[str] = os.getenv('CH_DB_USER')
    CH_DB_PORT: str = os.getenv('CH_DB_PORT', '8443')
    CH_DB_PASSWORD: Optional[str] = os.getenv('CH_DB_PASSWORD')
    CH_DB_NAME: Optional[str] = os.getenv('CH_DB_NAME')
    DB_NAME: str = os.getenv('DB_NAME', 'lenovo_app')  # For M-Schema generation
    CONNECTION_TIMEOUT: int = 10
    SSL_VERIFY: bool = False
    
    # ========== API/LLM Settings ==========
    GROQ_API_KEY: Optional[str] = os.getenv('GROQ_API_KEY')
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: Optional[int] = None
    
    # ========== File Paths ==========
    SCHEMA_FILE_PREFIX: str = "lenovo_app"  # Change from "cisco_stage_app"
    RESULTS_DIR: str = "./results"  # Directory for M-Schema output files
    DEFAULT_INPUT_SCHEMA_FILE: str = f"{RESULTS_DIR}/{SCHEMA_FILE_PREFIX}_clickhouse.json"
    DEFAULT_OUTPUT_SCHEMA_FILE: str = f"{RESULTS_DIR}/{SCHEMA_FILE_PREFIX}_modified_m_schema.json"
    
    # ========== Schema Generation ==========
    SKIP_EXAMPLES: bool = os.getenv('SKIP_EXAMPLES', 'false').lower() == 'true'
    SAMPLE_ROWS_IN_TABLE_INFO: int = 3
    MAX_STRING_LENGTH: int = 300
    SAMPLE_COEFFICIENT: float = 0.1
    MAX_EXAMPLES_PER_COLUMN: int = 5
    BATCH_FETCH_ENABLED: bool = True
    
    # ========== Table Filtering ==========
    # Set FILTER_TABLES=true to only generate M-Schema for specific tables
    # Set INCLUDE_TABLES to comma-separated list of table names (e.g., "table1,table2,table3")
    # If FILTER_TABLES=false or INCLUDE_TABLES is empty, all tables in the database will be included
    # 
    # Example usage:
    #   export FILTER_TABLES=true
    #   export INCLUDE_TABLES="deals_history,deals_parsed,deals_drilldowns_mapping"
    # 
    # To include all tables, either:
    #   - Set FILTER_TABLES=false (or don't set it)
    #   - Or leave INCLUDE_TABLES empty
    FILTER_TABLES: bool = os.getenv('FILTER_TABLES', 'false').lower() == 'true'
    INCLUDE_TABLES: list = [
        table.strip() 
        for table in os.getenv('INCLUDE_TABLES', '').split(',') 
        if table.strip()
    ] if os.getenv('deals_history, deals_parsed, deals_drilldowns_mapping') else []
    
    # ========== Foreign Key Identification ==========
    FK_IDENTIFICATION_MODEL: str = "openai/gpt-oss-120b"
    FK_IDENTIFICATION_TEMPERATURE: float = 0.0
    
    # ========== Table/Column Descriptions ==========
    DESCRIPTION_MODEL: str = "openai/gpt-oss-120b"
    DESCRIPTION_TEMPERATURE: float = 0.0
    
    # ========== Sampling Settings ==========
    MIN_SAMPLE_ROWS: int = 10000
    MIN_GRANULES_TO_SAMPLE: int = 5
    SAMPLE_COEFFICIENT_DEFAULT: float = 0.1
    
    # ========== Database Dialect Defaults ==========
    POSTGRESQL_DEFAULT_SCHEMA: str = "public"
    CLICKHOUSE_DEFAULT_PROTOCOL: str = "https"
    
    # ========== Internal Thresholds ==========
    MAX_TABLE_ROWS_FOR_EXAMPLES: int = 10_000_000  # Skip examples for tables > 10M rows
    
    @classmethod
    def validate_required(cls) -> None:
        """
        Validate that required environment variables are set.
        
        Raises:
            ValueError: If any required environment variables are missing.
        """
        required_vars = {
            'CH_DB_HOST': cls.CH_DB_HOST,
            'CH_DB_USER': cls.CH_DB_USER,
            'CH_DB_PASSWORD': cls.CH_DB_PASSWORD,
            'CH_DB_NAME': cls.CH_DB_NAME,
        }
        
        missing = [var for var, value in required_vars.items() if not value]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please set them using: export {missing[0]}='your-value'"
            )
    
    @classmethod
    def get_clickhouse_url(cls) -> str:
        """
        Generate ClickHouse connection URL from configuration.
        
        Returns:
            str: ClickHouse connection URL in SQLAlchemy format.
            
        Raises:
            ValueError: If required database credentials are not set.
        """
        from urllib.parse import quote_plus
        
        if not cls.CH_DB_HOST or not cls.CH_DB_USER or not cls.CH_DB_PASSWORD or not cls.CH_DB_NAME:
            raise ValueError(
                "Missing required database credentials. "
                "Please set CH_DB_HOST, CH_DB_USER, CH_DB_PASSWORD, and CH_DB_NAME."
            )
        
        encoded_password = quote_plus(cls.CH_DB_PASSWORD)
        return (
            f'clickhouse+http://{cls.CH_DB_USER}:{encoded_password}@'
            f'{cls.CH_DB_HOST}:{cls.CH_DB_PORT}/{cls.CH_DB_NAME}?'
            f'protocol={cls.CLICKHOUSE_DEFAULT_PROTOCOL}&verify={str(cls.SSL_VERIFY).lower()}'
        )
    
    @classmethod
    def get_input_schema_file(cls, custom_prefix: Optional[str] = None) -> str:
        """
        Get the input schema file path.
        
        Args:
            custom_prefix: Optional custom prefix to use instead of SCHEMA_FILE_PREFIX.
            
        Returns:
            str: Path to the input schema file in the results directory.
        """
        import os
        # Ensure results directory exists
        os.makedirs(cls.RESULTS_DIR, exist_ok=True)
        prefix = custom_prefix or cls.SCHEMA_FILE_PREFIX
        return f"{cls.RESULTS_DIR}/{prefix}_clickhouse.json"
    
    @classmethod
    def get_output_schema_file(cls, custom_prefix: Optional[str] = None) -> str:
        """
        Get the output schema file path.
        
        Args:
            custom_prefix: Optional custom prefix to use instead of SCHEMA_FILE_PREFIX.
            
        Returns:
            str: Path to the output schema file in the results directory.
        """
        import os
        # Ensure results directory exists
        os.makedirs(cls.RESULTS_DIR, exist_ok=True)
        prefix = custom_prefix or cls.SCHEMA_FILE_PREFIX
        return f"{cls.RESULTS_DIR}/{prefix}_modified_m_schema.json"
    
    @classmethod
    def get_include_tables(cls) -> Optional[list]:
        """
        Get the list of tables to include in M-Schema generation.
        
        Returns:
            Optional[list]: List of table names if FILTER_TABLES is True and INCLUDE_TABLES is set,
                          None if all tables should be included.
        """
        if cls.FILTER_TABLES and cls.INCLUDE_TABLES:
            return cls.INCLUDE_TABLES
        return None

