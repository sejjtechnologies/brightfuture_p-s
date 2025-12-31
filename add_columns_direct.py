#!/usr/bin/env python3
"""
Direct SQL script to add missing columns to assessment_results table
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env file")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("Attempting to add stream_rank and class_rank columns...")
    
    # Check if columns exist first
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'assessment_results' AND column_name = 'stream_rank'
        )
    """)
    stream_rank_exists = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'assessment_results' AND column_name = 'class_rank'
        )
    """)
    class_rank_exists = cursor.fetchone()[0]
    
    # Add columns if they don't exist
    if not stream_rank_exists:
        print("Adding stream_rank column...")
        cursor.execute("ALTER TABLE assessment_results ADD COLUMN stream_rank INTEGER NULL;")
        conn.commit()
        print("✓ stream_rank column added")
    else:
        print("✓ stream_rank column already exists")
    
    if not class_rank_exists:
        print("Adding class_rank column...")
        cursor.execute("ALTER TABLE assessment_results ADD COLUMN class_rank INTEGER NULL;")
        conn.commit()
        print("✓ class_rank column added")
    else:
        print("✓ class_rank column already exists")
    
    cursor.close()
    conn.close()
    print("\n✓ All columns verified/added successfully!")
    
except psycopg2.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"Error: {e}")
