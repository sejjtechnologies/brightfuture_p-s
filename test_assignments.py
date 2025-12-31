#!/usr/bin/env python3
"""
Test script to debug teacher assignment detection
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.auth_models import SystemUser
from routes.teacher_routes import get_teacher_assignments

def test_teacher_assignments():
    with app.app_context():
        # Test with teacher ID 7 (Mugisha) - should have assignments
        print("Testing teacher ID 7 (Mugisha):")
        assignments_7 = get_teacher_assignments(7)
        assignments_count_7 = len(assignments_7)
        has_assignments_7 = assignments_count_7 > 0
        print(f"  assignments_count: {assignments_count_7}")
        print(f"  has_assignments: {has_assignments_7}")
        print(f"  assignments: {assignments_7}")

        # Test with teacher ID 39 (Teacher) - should have assignments
        print("\nTesting teacher ID 39 (Teacher):")
        assignments_39 = get_teacher_assignments(39)
        assignments_count_39 = len(assignments_39)
        has_assignments_39 = assignments_count_39 > 0
        print(f"  assignments_count: {assignments_count_39}")
        print(f"  has_assignments: {has_assignments_39}")
        print(f"  assignments: {assignments_39}")

        # Test with a teacher who should NOT have assignments (let's find one)
        teachers = SystemUser.query.filter_by(role_id=4).all()  # Assuming role_id 4 is Teacher
        print(f"\nAll teachers: {[(t.id, t.username) for t in teachers]}")

        # Test with teacher ID 1 (assuming they don't have assignments)
        print("\nTesting teacher ID 1 (assuming no assignments):")
        assignments_1 = get_teacher_assignments(1)
        assignments_count_1 = len(assignments_1)
        has_assignments_1 = assignments_count_1 > 0
        print(f"  assignments_count: {assignments_count_1}")
        print(f"  has_assignments: {has_assignments_1}")
        print(f"  assignments: {assignments_1}")

if __name__ == "__main__":
    test_teacher_assignments()