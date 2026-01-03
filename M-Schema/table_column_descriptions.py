import os
import json
from groq import Groq

def load_m_schema(json_file_path="./cisco_stage_app_clickhouse.json"):
    """
    Read the M-Schema JSON file and return it as a dictionary.
    
    Args:
        json_file_path: Path to the JSON file (default: "./cisco_stage_app_clickhouse.json")
    
    Returns:
        dict: The M-Schema JSON object as a Python dictionary
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        m_schema = json.load(f)
    return m_schema

# Load the M-Schema
m_schema = load_m_schema("./cisco_stage_app_clickhouse.json")

system_prompt = f"""
# ROLE #
You are an Expert Database Schema Documentation Specialist with deep expertise in:
- Database schema analysis and understanding
- Writing clear, concise, and business-focused descriptions for database tables and columns
- Domain Specific Language (DSL) for database documentation
- M-Schema format and structure

Your primary responsibility is to analyze database schemas and generate comprehensive, accurate descriptions that help users understand the purpose, structure, and usage of database tables and columns.

You are VERY STRICT in following # ROLE #, # OBJECTIVES #, # RULES #, # OUTPUT FORMAT #, and # IMPORTANT NOTES #.

# OBJECTIVES #
1. Analyze and understand the provided M-Schema JSON structure, which contains:
   - Database identifier (db_id) and schema name
   - Multiple tables with their complete structure
   - Column definitions including: type, primary_key, nullable, default, autoincrement, examples
   - Table-level metadata
   - Foreign key relationships (if any)

2. Generate comprehensive, business-focused descriptions for:
   - Each table: Add "table_description" field that explains the table's purpose, business context, data granularity, and typical use cases
   - Each column: Add "column_description" field that explains the column's meaning, data format, valid values/ranges, business significance, and usage context
   - Each foreign key: Add "foreign_key_description" field to each foreign key entry that explains the relationship, business logic, and referential integrity between tables

3. Ensure all descriptions are:
   - Clear and concise (1-3 sentences for columns, 2-4 sentences for tables)
   - Business-oriented (focus on what the data represents, not just technical details)
   - Accurate and based on the schema structure, field names, types, and examples
   - Written in plain language that helps users understand the database structure 
MAKE SURE TO STRICTLY FOLLOW THE # OBJECTIVES # while executing the task.

"m-schema":
{m_schema}

# RULES #
1. You will add descriptions to:
   - All tables (table_description field)
   - All columns (column_description field)
   - All foreign keys (foreign_key_description field)
2. You will add descriptions to primary key columns (these are regular columns, so include column_description).
3. You will not add descriptions to the autoincrement keys (this is a metadata field, not a description field).
4. You will not add descriptions to the nullable keys (this is a metadata field, not a description field).
5. You will not add descriptions to the default keys (this is a metadata field, not a description field).

# OUTPUT FORMAT #
STRICTLY the output has to be a valid JSON object matching the exact structure of the input m-schema, but with added descriptions.

Output structure:
{{
  "db_id": "cisco_stage_app",
  "schema": "cisco_stage_app",
  "tables": {{
    "cisco_stage_app.qtd_commit_upside": {{
      "fields": {{
        "year": {{
          "type": "String",
          "primary_key": true,
          "nullable": false,
          "default": "' '",
          "autoincrement": false,
          "column_description": "Your description for the year column here",
          "examples": ["2023", "2021", "2019", "2020", "2022"]
        }},
        "quarter": {{
          "type": "String",
          "primary_key": false,
          "nullable": false,
          "default": "' '",
          "autoincrement": false,
          "column_description": "Your description for the quarter column here",
          "examples": ["Q2", "Q1", "Q3", "Q4"]
        }}
      }},
      "examples": [],
      "table_description": "Your description for the qtd_commit_upside table here"
    }},
    "cisco_stage_app.funnel_metrics": {{
      "fields": {{...}},
      "examples": [],
      "table_description": "Your description for the funnel_metrics table here"
    }},
    "cisco_stage_app.metrics": {{
      "fields": {{...}},
      "examples": [],
      "table_description": "Your description for the metrics table here"
    }},
    "cisco_stage_app.linearity_metrics": {{
      "fields": {{...}},
      "examples": [],
      "table_description": "Your description for the linearity_metrics table here"
    }}
  }},
  "foreign_keys": []
}}

# IMPORTANT NOTES #:
1. Add "column_description" field to EVERY column in EVERY table.
2. Add or update "table_description" field for EVERY table (at the table level, not in fields)
3. Preserve ALL existing fields: type, primary_key, nullable, default, autoincrement, examples
4. Keep the exact same table names and column names as in the input "m-schema".
5. Return the COMPLETE JSON structure with ALL tables and ALL columns, not just examples
6. Ensure valid JSON syntax (proper commas, brackets, quotes)
"""

# Initialize Groq client - API key must be set in environment variable
if "GROQ_API_KEY" not in os.environ:
    raise ValueError(
        "GROQ_API_KEY environment variable is not set. "
        "Please set it using: export GROQ_API_KEY='your-api-key'"
    )
client = Groq()

def get_response(system_prompt, client, m_schema, model="openai/gpt-oss-120b", temperature=0):
    """
    Generate a modified M-Schema using Groq API.
    
    Args:
        system_prompt: System prompt that includes instructions and will receive m_schema
        client: Groq client instance
        m_schema: Original M-Schema dictionary to be modified (will be added to system_prompt)
        model: Model name (default: "openai/gpt-oss-120b")
        temperature: Temperature for generation (default: 0)
    
    Returns:
        dict: Modified M-Schema dictionary
    """
    # Convert m_schema to JSON string
    m_schema_json = json.dumps(m_schema, indent=2, ensure_ascii=False)
    
    # Combine system_prompt with m_schema JSON
    full_system_prompt = f"""{system_prompt}

M-Schema JSON:
{m_schema_json}"""
    
    # Get response from Groq API - using only system message
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": full_system_prompt}
        ],
        temperature=temperature
    )
    
    # Extract the response content
    response_content = response.choices[0].message.content.strip()
    
    # Try to extract JSON from the response (in case there's extra text)
    try:
        # Remove markdown code blocks if present
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0].strip()
        elif "```" in response_content:
            response_content = response_content.split("```")[1].split("```")[0].strip()
        
        # Parse the JSON response
        modified_m_schema = json.loads(response_content)
        
        # Save to JSON file
        output_file = "cisco_stage_app_modified_m_schema.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(modified_m_schema, f, ensure_ascii=False, indent=2)
        print(f"✓ Modified M-Schema saved to: {output_file}")
        
        return modified_m_schema
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response content: {response_content[:500]}...")  # Print first 500 chars for debugging
        raise ValueError(f"Failed to parse JSON from response: {e}")


def validate_modified_schema(modified_schema: dict, original_schema: dict) -> bool:
    """
    Validate that the modified schema has all required fields and descriptions.
    
    Args:
        modified_schema: The generated modified schema
        original_schema: The original schema for comparison
    
    Returns:
        bool: True if validation passes
    """
    print("\n" + "="*80)
    print("Validating Modified Schema")
    print("="*80)
    
    issues = []
    
    # Check structure
    if 'tables' not in modified_schema:
        issues.append("Missing 'tables' key in modified schema")
        return False
    
    original_tables = original_schema.get('tables', {})
    modified_tables = modified_schema.get('tables', {})
    
    # Check all tables exist
    for table_name in original_tables.keys():
        if table_name not in modified_tables:
            issues.append(f"Missing table: {table_name}")
            continue
        
        # Check table description
        if 'table_description' not in modified_tables[table_name]:
            issues.append(f"Missing 'table_description' for table: {table_name}")
        elif not modified_tables[table_name]['table_description']:
            issues.append(f"Empty 'table_description' for table: {table_name}")
        
        # Check all columns exist
        original_fields = original_tables[table_name].get('fields', {})
        modified_fields = modified_tables[table_name].get('fields', {})
        
        for field_name in original_fields.keys():
            if field_name not in modified_fields:
                issues.append(f"Missing field '{field_name}' in table '{table_name}'")
                continue
            
            # Check column description
            if 'column_description' not in modified_fields[field_name]:
                issues.append(f"Missing 'column_description' for field '{field_name}' in table '{table_name}'")
            elif not modified_fields[field_name]['column_description']:
                issues.append(f"Empty 'column_description' for field '{field_name}' in table '{table_name}'")
    
    if issues:
        print("⚠ Validation Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        # Count statistics
        total_tables = len(modified_tables)
        total_columns = sum(len(t.get('fields', {})) for t in modified_tables.values())
        print(f"✓ Validation passed!")
        print(f"  - Tables: {total_tables}")
        print(f"  - Columns: {total_columns}")
        print(f"  - All tables have 'table_description'")
        print(f"  - All columns have 'column_description'")
        return True


def main():
    """Main function to execute the script."""
    print("="*80)
    print("M-Schema Description Generator")
    print("="*80)
    print("\nLoading M-Schema...")
    
    try:
        # Load the original schema
        input_file = "./cisco_stage_app_clickhouse.json"
        m_schema = load_m_schema(input_file)
        print(f"✓ Loaded schema from: {input_file}")
        print(f"  - Tables: {len(m_schema.get('tables', {}))}")
        
        print("\nGenerating descriptions using Groq API...")
        print("This may take a few moments...\n")
        
        # Generate modified schema
        modified_m_schema = get_response(system_prompt, client, m_schema)
        
        # Validate the output
        if validate_modified_schema(modified_m_schema, m_schema):
            print("\n" + "="*80)
            print("✓ Successfully generated and validated modified M-Schema!")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("⚠ Modified schema generated but validation found issues.")
            print("Please review the output file and regenerate if needed.")
            print("="*80)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
