#!/usr/bin/env python3
"""
Script to identify foreign keys in M-Schema based on table/column descriptions and examples.
Uses Groq API to analyze the schema and identify relationships.
"""

import os
import json
from groq import Groq


def load_m_schema(json_file_path="./cisco_stage_app_modified_m_schema.json"):
    """
    Read the modified M-Schema JSON file and return it as a dictionary.
    
    Args:
        json_file_path: Path to the JSON file
    
    Returns:
        dict: The M-Schema JSON object as a Python dictionary
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        m_schema = json.load(f)
    return m_schema


# Load the modified M-Schema
m_schema = load_m_schema("./cisco_stage_app_modified_m_schema.json")

system_prompt = f"""
# ROLE #
You are an Expert Database Schema Analyst specializing in identifying referential integrity relationships and foreign key constraints in database schemas.

Your primary responsibility is to analyze database schemas with table and column descriptions, examine column examples/values, and identify foreign key relationships between tables based on:
1. Column names that suggest relationships (e.g., customer_id, order_id, user_id)
2. Column descriptions that indicate references to other tables
3. Example values that match primary key patterns from other tables
4. Business logic and domain knowledge implied by descriptions
5. Naming conventions and data types

You are VERY STRICT in following # ROLE #, # OBJECTIVES #, # RULES #, # OUTPUT FORMAT #, and # IMPORTANT NOTES #.

# OBJECTIVES #
1. Analyze the provided M-Schema JSON structure which contains:
   - Multiple tables with their structure
   - Column definitions with types, primary_key flags, nullable flags, and examples
   - Table descriptions explaining the purpose of each table
   - Column descriptions explaining the meaning and usage of each column

2. Identify foreign key relationships by:
   - Matching column names that reference other tables (e.g., "user_id" → references "users.id")
   - Analyzing column descriptions for mentions of relationships or references
   - Comparing example values to primary key values from other tables
   - Understanding business domain relationships from table/column descriptions
   - Identifying columns that logically reference primary keys in other tables

3. Generate a "foreign_keys" array with identified relationships in the correct format.

# RULES #
1. Only identify relationships where there is STRONG evidence (column name patterns, descriptions, or example value matches)
2. A foreign key column should reference a primary key column in another table
3. Column names ending with "_id", "_code", "_key" often indicate foreign keys
4. Column descriptions mentioning "references", "links to", "foreign key", or similar terms indicate relationships
5. Example values should match or be subsets of primary key example values from the referenced table
6. If no clear foreign key relationships exist, return an empty array []
7. Do NOT create relationships if evidence is weak or ambiguous

# OUTPUT FORMAT #
STRICTLY the output has to be a valid JSON object containing ONLY the "foreign_keys" array.

Output format:
{{
  "foreign_keys": [
    [
      "source_table_name",
      "source_column_name",
      "ref_schema",
      "ref_table_name",
      "ref_column_name"
    ],
    [
      "source_table_name2",
      "source_column_name2",
      "ref_schema",
      "ref_table_name2",
      "ref_column_name2"
    ]
  ]
}}

Each foreign key is an array with 5 elements:
1. source_table_name: Full table name (e.g., "cisco_stage_app.orders")
2. source_column_name: Column name in the source table (e.g., "customer_id")
3. ref_schema: Schema name of referenced table (usually same as source schema, e.g., "cisco_stage_app")
4. ref_table_name: Full table name being referenced (e.g., "cisco_stage_app.customers")
5. ref_column_name: Primary key column name in the referenced table (e.g., "id")

# IMPORTANT NOTES #:
1. Return ONLY the "foreign_keys" array structure, NOT the full schema
2. Use the exact table names and column names as they appear in the input schema
3. Each foreign key entry must be an array of exactly 5 strings
4. The ref_schema should match the schema name from the input (e.g., "cisco_stage_app")
5. Only include relationships you are confident about based on evidence
6. If no foreign keys are found, return: {{"foreign_keys": []}}
7. Ensure valid JSON syntax

Modified M-Schema JSON:
{json.dumps(m_schema, indent=2, ensure_ascii=False)}
"""

# Initialize Groq client - API key must be set in environment variable
if "GROQ_API_KEY" not in os.environ:
    raise ValueError(
        "GROQ_API_KEY environment variable is not set. "
        "Please set it using: export GROQ_API_KEY='your-api-key'"
    )
client = Groq()


def identify_foreign_keys(system_prompt, client, m_schema, model="openai/gpt-oss-120b", temperature=0):
    """
    Identify foreign keys in the M-Schema using Groq API.
    
    Args:
        system_prompt: System prompt with instructions
        client: Groq client instance
        m_schema: Modified M-Schema dictionary
        model: Model name (default: "openai/gpt-oss-120b")
        temperature: Temperature for generation (default: 0)
    
    Returns:
        list: Foreign keys array
    """
    # Get response from Groq API
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt}
        ],
        temperature=temperature
    )
    
    # Extract the response content
    response_content = response.choices[0].message.content.strip()
    
    # Try to extract JSON from the response
    try:
        # Remove markdown code blocks if present
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0].strip()
        elif "```" in response_content:
            response_content = response_content.split("```")[1].split("```")[0].strip()
        
        # Parse the JSON response
        result = json.loads(response_content)
        
        # Extract foreign_keys array
        if 'foreign_keys' in result:
            foreign_keys = result['foreign_keys']
            return foreign_keys
        else:
            print("⚠ Warning: Response does not contain 'foreign_keys' key")
            return []
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response content: {response_content[:500]}...")
        raise ValueError(f"Failed to parse JSON from response: {e}")


def update_foreign_keys_in_schema(m_schema: dict, foreign_keys: list, output_file: str):
    """
    Update the foreign_keys in the schema and save to file.
    
    Args:
        m_schema: The M-Schema dictionary
        foreign_keys: List of foreign key arrays
        output_file: Path to output file
    """
    m_schema['foreign_keys'] = foreign_keys
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(m_schema, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Updated schema saved to: {output_file}")


def main():
    """Main function to execute the script."""
    print("="*80)
    print("Foreign Key Identification")
    print("="*80)
    print("\nAnalyzing schema to identify foreign key relationships...")
    print("This may take a few moments...\n")
    
    try:
        # Identify foreign keys
        foreign_keys = identify_foreign_keys(system_prompt, client, m_schema)
        
        print(f"\n✓ Identified {len(foreign_keys)} foreign key relationship(s)")
        if foreign_keys:
            print("\nForeign Keys:")
            for i, fk in enumerate(foreign_keys, 1):
                print(f"  {i}. {fk[0]}.{fk[1]} → {fk[3]}.{fk[4]}")
        else:
            print("  No foreign keys identified (returning empty array)")
        
        # Update the schema file
        output_file = "./cisco_stage_app_modified_m_schema.json"
        update_foreign_keys_in_schema(m_schema, foreign_keys, output_file)
        
        print("\n" + "="*80)
        print("✓ Successfully identified and updated foreign keys!")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

