#!/usr/bin/env python3
"""
Script to seed exam types into the database.
Run this script to populate the exam_types table with default values.
"""

from models.auth_models import db
from models.admin_models import ExamType
import os
import sys

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def seed_exam_types():
    """Seed the database with default exam types"""

    # Default exam types
    default_exam_types = [
        {'name': 'Mid-term', 'description': 'Mid-term examination'},
        {'name': 'End-term', 'description': 'End-term examination'},
        {'name': 'Final', 'description': 'Final examination'},
        {'name': 'Mock', 'description': 'Mock examination'},
        {'name': 'Practice', 'description': 'Practice examination'}
    ]

    try:
        for exam_type_data in default_exam_types:
            # Check if exam type already exists
            existing = ExamType.query.filter_by(name=exam_type_data['name']).first()
            if not existing:
                exam_type = ExamType(
                    name=exam_type_data['name'],
                    description=exam_type_data['description'],
                    is_active=True
                )
                db.session.add(exam_type)
                print(f"Added exam type: {exam_type_data['name']}")
            else:
                print(f"Exam type already exists: {exam_type_data['name']}")

        db.session.commit()
        print("Exam types seeding completed successfully!")

    except Exception as e:
        db.session.rollback()
        print(f"Error seeding exam types: {e}")
        return False

    return True

if __name__ == '__main__':
    from app import app

    with app.app_context():
        success = seed_exam_types()
        if success:
            print("Database seeding completed!")
        else:
            print("Database seeding failed!")
            sys.exit(1)