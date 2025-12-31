#!/usr/bin/env python3
"""
Script to check if database tables have all necessary columns for storing data from templates.
This script verifies that the database schema matches the application models.
"""
import os
import sys
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import Flask and models
from app import app, db
from models.admin_models import SchoolClass, Subject, Stream, TeacherAssignment, Term, AcademicYear, ExamSchedule, ClassStream, SystemSetting, Notification, NotificationRead
from models.secretary_models import Pupil
from models.teacher_models import AssessmentRecord, AssessmentResult, SubjectRemark, ProgressSummary, Curriculum, LessonPlan, Homework, HomeworkSubmission, LearningNeed, DisciplinaryNote, TeacherNote
from models.auth_models import SystemUser, Role

def check_table_columns(model_class, table_name):
    """Check if the database table has all columns defined in the model"""
    print(f"\n{'='*80}")
    print(f"CHECKING TABLE: {table_name} ({model_class.__name__})")
    print('='*80)
    
    # Get model columns
    model_columns = {}
    for column in model_class.__table__.columns:
        model_columns[column.name] = {
            'type': str(column.type),
            'nullable': column.nullable,
            'default': str(column.default) if column.default else None,
            'primary_key': column.primary_key,
            'unique': column.unique
        }
    
    print(f"Model defines {len(model_columns)} columns:")
    for col_name, info in model_columns.items():
        print(f"  - {col_name}: {info['type']} {'(PK)' if info['primary_key'] else ''} {'(Unique)' if info['unique'] else ''} {'(Nullable)' if info['nullable'] else '(Not Null)'}")
    
    # Check database columns
    try:
        # Use SQLAlchemy inspector
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        db_columns = inspector.get_columns(table_name)
        db_column_names = [col['name'] for col in db_columns]
        
        print(f"\nDatabase table has {len(db_columns)} columns:")
        for col in db_columns:
            print(f"  - {col['name']}: {col['type']} {'(Nullable)' if col['nullable'] else '(Not Null)'}")
        
        # Check for missing columns
        missing_columns = []
        for col_name in model_columns:
            if col_name not in db_column_names:
                missing_columns.append(col_name)
        
        # Check for extra columns (not in model)
        extra_columns = []
        for col_name in db_column_names:
            if col_name not in model_columns:
                extra_columns.append(col_name)
        
        print(f"\n{'='*80}")
        print("VALIDATION RESULTS:")
        print('='*80)
        
        if missing_columns:
            print(f"❌ MISSING COLUMNS ({len(missing_columns)}):")
            for col in missing_columns:
                print(f"  - {col}")
        else:
            print("✅ All model columns exist in database")
        
        if extra_columns:
            print(f"⚠️  EXTRA COLUMNS ({len(extra_columns)}):")
            for col in extra_columns:
                print(f"  - {col}")
        else:
            print("✅ No extra columns in database")
        
        if not missing_columns:
            print("✅ Table structure is complete!")
        else:
            print("❌ Table structure is incomplete. Run migrations.")
        
        return len(missing_columns) == 0
        
    except Exception as e:
        print(f"❌ ERROR checking table {table_name}: {e}")
        return False

def main():
    """Main function to check all relevant tables"""
    print("DATABASE SCHEMA VALIDATION SCRIPT")
    print("==================================")
    
    # Use the app context
    with app.app_context():
        print(f"Connected to database: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # List of models to check - only assessment_results for marks/rankings
        models_to_check = [
            (AssessmentResult, 'assessment_results'),
        ]
        
        total_tables = len(models_to_check)
        passed_tables = 0
        
        for model_class, table_name in models_to_check:
            if check_table_columns(model_class, table_name):
                passed_tables += 1
        
        print(f"\n{'='*80}")
        print("OVERALL SUMMARY:")
        print('='*80)
        print(f"Total tables checked: {total_tables}")
        print(f"Tables with complete structure: {passed_tables}")
        print(f"Tables with issues: {total_tables - passed_tables}")
        
        if passed_tables == total_tables:
            print("🎉 All tables have the correct structure!")
            return 0
        else:
            print("⚠️  Some tables have structural issues. Run migrations if needed.")
            return 1

if __name__ == "__main__":
    exit(main())