#!/usr/bin/env python3
"""
Script to check the assessment_results table structure and verify if it has stream_rank and class_rank columns
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Load environment variables from .env file
load_dotenv()

# Get database connection details
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env file")
    exit(1)

print(f"Database URL: {DATABASE_URL[:50]}...") # Print partial URL for security

try:
    # Connect to the database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("CHECKING TABLE STRUCTURE: assessment_results")
    print("="*80)
    
    # Query to get table column information
    query = """
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'assessment_results'
    ORDER BY ordinal_position;
    """
    
    cursor.execute(query)
    columns = cursor.fetchall()
    
    if not columns:
        print("ERROR: Table 'assessment_results' not found!")
    else:
        print(f"\nFound {len(columns)} columns:\n")
        print(f"{'Column Name':<25} {'Data Type':<15} {'Nullable':<10} {'Default'}")
        print("-" * 80)
        
        has_stream_rank = False
        has_class_rank = False
        
        for column_name, data_type, is_nullable, column_default in columns:
            nullable = "YES" if is_nullable else "NO"
            default = column_default if column_default else "None"
            print(f"{column_name:<25} {data_type:<15} {nullable:<10} {default}")
            
            if column_name == "stream_rank":
                has_stream_rank = True
            if column_name == "class_rank":
                has_class_rank = True
        
        print("\n" + "="*80)
        print("VALIDATION RESULTS:")
        print("="*80)
        print(f"✓ stream_rank column: {'EXISTS' if has_stream_rank else 'MISSING ❌'}")
        print(f"✓ class_rank column: {'EXISTS' if has_class_rank else 'MISSING ❌'}")
        
        if has_stream_rank and has_class_rank:
            print("\n✓ All required columns are present!")
        else:
            print("\n✗ Some required columns are missing. Run migrations:")
            print("  flask db migrate -m 'Add stream_rank and class_rank to assessment_results'")
            print("  flask db upgrade")
    
    cursor.close()
    conn.close()
    print("\n" + "="*80)

except psycopg2.OperationalError as e:
    print(f"ERROR: Could not connect to database: {e}")
except Exception as e:
    print(f"ERROR: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
