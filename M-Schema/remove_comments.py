#!/usr/bin/env python3
"""
Script to remove all 'comment' fields from columns and tables in M-Schema JSON file.
"""

import json
import sys
from pathlib import Path
from config import MSchemaConfig


def remove_comments_from_json(json_file_path: str, output_file_path: str = None):
    """
    Remove all 'comment' fields from columns and tables in M-Schema JSON.
    
    Args:
        json_file_path: Path to the input JSON file
        output_file_path: Path to save the updated JSON (if None, overwrites input file)
    """
    # Read the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        schema_data = json.load(f)
    
    tables = schema_data.get('tables', {})
    comments_removed = 0
    
    for table_name, table_info in tables.items():
        # Remove table-level comment
        if 'comment' in table_info:
            del table_info['comment']
            comments_removed += 1
            print(f"✓ Removed comment from table: {table_name}")
        
        # Remove column-level comments
        fields = table_info.get('fields', {})
        for field_name, field_info in fields.items():
            if 'comment' in field_info:
                del field_info['comment']
                comments_removed += 1
        
        print(f"  ✓ Removed comments from {len([f for f in fields.values() if 'comment' not in f])} columns in {table_name}")
    
    # Determine output path
    if output_file_path is None:
        output_file_path = json_file_path
    
    # Save the updated JSON
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(schema_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ Removed {comments_removed} comment field(s)")
    print(f"✓ Updated JSON saved to: {output_file_path}")
    return schema_data


def main():
    """Main function to run the script."""
    # Get JSON file path from command line argument or use default from config
    if len(sys.argv) > 1:
        json_file_path = sys.argv[1]
    else:
        json_file_path = MSchemaConfig.get_input_schema_file()
    
    # Check if file exists
    if not Path(json_file_path).exists():
        print(f"✗ Error: File not found: {json_file_path}")
        print(f"Usage: python3 remove_comments.py [json_file_path]")
        sys.exit(1)
    
    # Optional: specify output file
    output_file = None
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    print("="*80)
    print("Removing Comments from M-Schema JSON")
    print("="*80)
    print(f"Input file: {json_file_path}")
    if output_file:
        print(f"Output file: {output_file}")
    else:
        print(f"Output file: {json_file_path} (overwriting)")
    print("="*80)
    print()
    
    # Remove comments
    try:
        remove_comments_from_json(json_file_path, output_file)
        print("\n" + "="*80)
        print("✓ Successfully removed all comments!")
        print("="*80)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

