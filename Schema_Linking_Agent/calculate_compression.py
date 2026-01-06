"""
Compression Calculation Script

Calculates average table compression and column compression ratios
by comparing original M-Schema with filtered schemas.
"""

import json
import os
from typing import Dict, List, Tuple
from glob import glob


def load_schema(file_path: str) -> Dict:
    """
    Load M-Schema JSON file.
    
    Args:
        file_path: Path to the JSON file.
    
    Returns:
        Dictionary containing the M-Schema structure.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def count_tables_and_columns(schema: Dict) -> Tuple[int, int, Dict[str, int]]:
    """
    Count tables and columns in a schema.
    
    Args:
        schema: M-Schema dictionary.
    
    Returns:
        Tuple of (total_tables, total_columns, table_column_counts)
        where table_column_counts is a dict mapping table_name -> column_count
    """
    tables = schema.get('tables', {})
    total_tables = len(tables)
    total_columns = 0
    table_column_counts = {}
    
    for table_name, table_data in tables.items():
        columns = table_data.get('fields', {})
        column_count = len(columns)
        table_column_counts[table_name] = column_count
        total_columns += column_count
    
    return total_tables, total_columns, table_column_counts


def calculate_compression_stats(
    original_schema: Dict,
    filtered_schemas: List[Dict]
) -> Dict:
    """
    Calculate compression statistics.
    
    Args:
        original_schema: Original M-Schema dictionary.
        filtered_schemas: List of filtered schema dictionaries.
    
    Returns:
        Dictionary containing compression statistics.
    """
    # Get original counts
    orig_tables, orig_columns, orig_table_cols = count_tables_and_columns(original_schema)
    
    # Calculate compression for each filtered schema
    compressions = []
    table_compressions = []
    column_compressions = []
    
    for filtered_schema in filtered_schemas:
        filt_tables, filt_columns, filt_table_cols = count_tables_and_columns(filtered_schema)
        
        # Overall compression
        table_compression = filt_tables / orig_tables if orig_tables > 0 else 0
        column_compression = filt_columns / orig_columns if orig_columns > 0 else 0
        
        compressions.append({
            'tables': filt_tables,
            'columns': filt_columns,
            'table_compression': table_compression,
            'column_compression': column_compression
        })
        
        table_compressions.append(table_compression)
        column_compressions.append(column_compression)
    
    # Calculate averages
    avg_table_compression = sum(table_compressions) / len(table_compressions) if table_compressions else 0
    avg_column_compression = sum(column_compressions) / len(column_compressions) if column_compressions else 0
    
    # Calculate per-table compression
    table_compression_details = {}
    for table_name in orig_table_cols.keys():
        orig_cols = orig_table_cols[table_name]
        filtered_counts = []
        
        for filtered_schema in filtered_schemas:
            filt_tables = filtered_schema.get('tables', {})
            if table_name in filt_tables:
                filt_cols = len(filt_tables[table_name].get('fields', {}))
                filtered_counts.append(filt_cols)
            else:
                filtered_counts.append(0)
        
        # Average columns selected for this table across all queries
        avg_filt_cols = sum(filtered_counts) / len(filtered_counts) if filtered_counts else 0
        table_compression_ratio = avg_filt_cols / orig_cols if orig_cols > 0 else 0
        
        table_compression_details[table_name] = {
            'original_columns': orig_cols,
            'average_filtered_columns': avg_filt_cols,
            'compression_ratio': table_compression_ratio
        }
    
    return {
        'original': {
            'tables': orig_tables,
            'columns': orig_columns,
            'table_column_counts': orig_table_cols
        },
        'compressions': compressions,
        'averages': {
            'table_compression': avg_table_compression,
            'column_compression': avg_column_compression
        },
        'table_details': table_compression_details
    }


def main():
    """
    Main function to calculate compression statistics.
    """
    print("=" * 80)
    print("Schema Compression Calculator")
    print("=" * 80)
    
    # Paths
    original_schema_path = "./cisco_stage_app_modified_m_schema.json"
    results_dir = "./results"
    filtered_schema_pattern = os.path.join(results_dir, "filtered_schema_query_*.json")
    
    # Check if files exist
    if not os.path.exists(original_schema_path):
        print(f"❌ Error: Original schema not found at {original_schema_path}")
        return
    
    filtered_files = sorted(glob(filtered_schema_pattern))
    if not filtered_files:
        print(f"❌ Error: No filtered schemas found matching {filtered_schema_pattern}")
        print("   Run example_usage.py first to generate filtered schemas.")
        return
    
    print(f"\n📊 Loading schemas...")
    print(f"   Original: {original_schema_path}")
    print(f"   Filtered schemas: {len(filtered_files)} files")
    
    # Load original schema
    original_schema = load_schema(original_schema_path)
    
    # Load filtered schemas
    filtered_schemas = []
    for file_path in filtered_files:
        filtered_schemas.append(load_schema(file_path))
    
    # Calculate compression
    print(f"\n📈 Calculating compression statistics...")
    stats = calculate_compression_stats(original_schema, filtered_schemas)
    
    # Display results
    print("\n" + "=" * 80)
    print("COMPRESSION STATISTICS")
    print("=" * 80)
    
    print(f"\n📋 Original Schema:")
    print(f"   Tables: {stats['original']['tables']}")
    print(f"   Columns: {stats['original']['columns']}")
    print(f"\n   Table Column Counts:")
    for table_name, col_count in stats['original']['table_column_counts'].items():
        print(f"     - {table_name}: {col_count} columns")
    
    print(f"\n📊 Average Compression Ratios:")
    print(f"   Table Compression: {stats['averages']['table_compression']:.2%}")
    print(f"   Column Compression: {stats['averages']['column_compression']:.2%}")
    
    print(f"\n📉 Compression by Query:")
    for i, comp in enumerate(stats['compressions'], 1):
        print(f"   Query {i}:")
        print(f"     Tables: {comp['tables']}/{stats['original']['tables']} ({comp['table_compression']:.2%})")
        print(f"     Columns: {comp['columns']}/{stats['original']['columns']} ({comp['column_compression']:.2%})")
    
    print(f"\n🔍 Per-Table Compression Details:")
    for table_name, details in stats['table_details'].items():
        orig_cols = details['original_columns']
        avg_filt_cols = details['average_filtered_columns']
        comp_ratio = details['compression_ratio']
        print(f"   {table_name}:")
        print(f"     Original: {orig_cols} columns")
        print(f"     Average Selected: {avg_filt_cols:.1f} columns")
        print(f"     Compression: {comp_ratio:.2%}")
    
    # Summary
    print(f"\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Original Schema: {stats['original']['tables']} tables, {stats['original']['columns']} columns")
    print(f"Average Filtered: {stats['averages']['table_compression']:.1%} of tables, {stats['averages']['column_compression']:.1%} of columns")
    print(f"Average Reduction: {(1 - stats['averages']['table_compression']):.1%} tables, {(1 - stats['averages']['column_compression']):.1%} columns")
    
    # Save results
    output_file = "./compression_stats.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Statistics saved to: {output_file}")


if __name__ == "__main__":
    main()

