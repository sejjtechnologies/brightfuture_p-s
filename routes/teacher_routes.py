from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.auth_models import SystemUser, db
from models.admin_models import SchoolClass, Subject, Stream, TeacherAssignment, Term, AcademicYear, ExamSchedule, ClassStream, SystemSetting, Notification, NotificationRead
from models.secretary_models import Pupil
from models.teacher_models import (
    AssessmentRecord, AssessmentResult, SubjectRemark, ProgressSummary,
    Curriculum, LessonPlan, Homework, HomeworkSubmission,
    LearningNeed, DisciplinaryNote, TeacherNote
)
from datetime import datetime
from sqlalchemy import and_, or_, select

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

def get_teacher_assignments(teacher_id):
    """Get all class/stream/subject assignments for a teacher"""
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher_id).options(
        db.selectinload(TeacherAssignment.class_stream).selectinload(ClassStream.school_class),
        db.selectinload(TeacherAssignment.class_stream).selectinload(ClassStream.stream),
        db.selectinload(TeacherAssignment.subject)
    ).all()
    print(f"DEBUG get_teacher_assignments: teacher_id={teacher_id}, found {len(assignments)} assignments")
    return assignments

def get_teacher_pupils(teacher_id):
    """Get all pupils assigned to a teacher - Ultra Optimized version"""
    # Single optimized query with proper joins and selectinload for best performance
    pupils = Pupil.query.join(
        ClassStream,
        and_(
            Pupil.current_class_id == ClassStream.class_id,
            Pupil.current_stream_id == ClassStream.stream_id
        )
    ).join(
        TeacherAssignment,
        TeacherAssignment.class_stream_id == ClassStream.id
    ).filter(
        TeacherAssignment.teacher_id == teacher_id
    ).options(
        # Use selectinload for optimal loading of related objects
        db.selectinload(Pupil.current_class),
        db.selectinload(Pupil.current_stream)
    ).order_by(
        # Order by class and name for consistent display
        Pupil.current_class_id,
        Pupil.first_name,
        Pupil.last_name
    ).all()

    return pupils

def get_teacher_template_context(user):
    """Get common template context variables for teacher routes"""

    # Get notifications
    notifications = Notification.query.join(SystemUser).filter(
        (Notification.visibility == 'all') |
        (Notification.visibility == 'all_except_parents_admins') |
        (Notification.visibility == user.role.name.lower() + '_only')
    ).order_by(Notification.created_at.desc()).all()

    # Get unread notification count
    read_notification_ids = select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id)
    unread_count = db.session.scalar(
        select(db.func.count()).select_from(Notification).where(
            ((Notification.visibility == 'all') |
             (Notification.visibility == 'all_except_parents_admins') |
             (Notification.visibility == user.role.name.lower() + '_only')) &
            (~Notification.id.in_(read_notification_ids))
        )
    )

    # Get term progress info
    term_progress = get_term_progress_info()

    # Get settings for welcome modal
    school_name_setting = SystemSetting.query.filter_by(key='school_name').first()
    contact_phone_setting = SystemSetting.query.filter_by(key='contact_phone').first()
    contact_email_setting = SystemSetting.query.filter_by(key='contact_email').first()
    school_name = school_name_setting.value if school_name_setting and school_name_setting.value else 'Bright Future P.S'
    contact_phone = contact_phone_setting.value if contact_phone_setting and contact_phone_setting.value else '+256786210221'
    contact_email = contact_email_setting.value if contact_email_setting and contact_email_setting.value else 'sejjtechnologies@gmail.com'

    return {
        'notifications': notifications,
        'term_progress': term_progress,
        'unread_count': unread_count,
        'school_name': school_name,
        'contact_phone': contact_phone,
        'contact_email': contact_email
    }

def get_term_progress_info():
    """Get current term progress information for display in dashboards"""
    try:
        # Get current term and academic year settings
        current_term_setting = SystemSetting.query.filter_by(key='current_term_id').first()
        current_academic_year_setting = SystemSetting.query.filter_by(key='current_academic_year_id').first()

        if not current_term_setting or not current_academic_year_setting:
            return None

        current_term = db.session.get(Term, int(current_term_setting.value))
        current_academic_year = db.session.get(AcademicYear, int(current_academic_year_setting.value))

        if not current_term or not current_academic_year:
            return None

        today = datetime.now().date()
        term_start = current_term.start_date
        term_end = current_term.end_date

        # Calculate days spent and remaining
        if today < term_start:
            days_spent = 0
            days_remaining = (term_end - term_start).days + 1
        elif today > term_end:
            days_spent = (term_end - term_start).days + 1
            days_remaining = 0
        else:
            days_spent = (today - term_start).days + 1
            days_remaining = (term_end - today).days

        # Calculate total term days (approximately 3.5 months = 105 days)
        total_term_days = (term_end - term_start).days + 1

        # Calculate academic year info (3 terms per year)
        academic_year_terms = Term.query.filter_by(academic_year_id=current_academic_year.id).order_by(Term.start_date).all()
        current_term_number = None
        for i, term in enumerate(academic_year_terms, 1):
            if term.id == current_term.id:
                current_term_number = i
                break

        return {
            'term_name': current_term.name,
            'academic_year_name': current_academic_year.name,
            'days_spent': days_spent,
            'days_remaining': days_remaining,
            'total_term_days': total_term_days,
            'current_term_number': current_term_number,
            'total_terms_in_year': len(academic_year_terms),
            'term_start_date': term_start,
            'term_end_date': term_end,
            'today': today
        }
    except Exception as e:
        print(f"Error getting term progress info: {e}")
        return None

@teacher_bp.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('authbp.login'))

    # Get teacher assignments count
    assignments = TeacherAssignment.query.filter_by(teacher_id=user.id).all()
    assignments_count = len(assignments)
    
    # Get notifications for teacher
    notifications = Notification.query.filter(
        Notification.visibility.in_(['all', 'all_except_parents_admins', 'teachers_only'])
    ).order_by(Notification.created_at.desc()).limit(5).all()

    # Get unread notification count
    read_notification_ids = select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id).subquery()
    unread_count = Notification.query.filter(
        Notification.visibility.in_(['all', 'all_except_parents_admins', 'teachers_only']),
        ~Notification.id.in_(read_notification_ids)
    ).count()

    # Get pupils count
    pupils_count = len(get_teacher_pupils(user.id))

    context = get_teacher_template_context(user)
    context.update({
        'notifications': notifications,
        'unread_count': unread_count,
        'assignments_count': assignments_count,
        'pupils_count': pupils_count
    })

    return render_template('teacher/dashboard.html', **context)

# Assessment Records Routes
@teacher_bp.route('/assessment-records')
def assessment_records():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('authbp.login'))

    assignments = get_teacher_assignments(user.id)
    if not assignments:
        flash('You need to be assigned to classes and streams before accessing assessment records.', 'warning')
        return redirect(url_for('teacher.dashboard'))

    context = get_teacher_template_context(user)
    context.update({'assignments': assignments})
    return render_template('teacher/assessment_records.html', **context)

@teacher_bp.route('/api/assessment-records', methods=['GET', 'POST'])
def api_assessment_records():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'GET':
        # Get current term
        current_term_setting = SystemSetting.query.filter_by(key='current_term_id').first()
        current_term_id = int(current_term_setting.value) if current_term_setting else None

        assessments = AssessmentRecord.query.filter_by(teacher_id=user.id)
        if current_term_id:
            assessments = assessments.filter_by(term_id=current_term_id)

        assessments = assessments.order_by(AssessmentRecord.created_at.desc()).all()

        return jsonify([{
            'id': a.id,
            'title': a.title,
            'assessment_type': a.assessment_type,
            'subject': a.subject.name,
            'class': a.school_class.name,
            'stream': a.stream.name if a.stream else 'All',
            'total_marks': a.total_marks,
            'assessment_date': a.assessment_date.strftime('%Y-%m-%d'),
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M')
        } for a in assessments])

    elif request.method == 'POST':
        data = request.get_json()

        # Get current term
        current_term_setting = SystemSetting.query.filter_by(key='current_term_id').first()
        current_term_id = int(current_term_setting.value) if current_term_setting else None

        if not current_term_id:
            return jsonify({'error': 'No current term set'}), 400

        assessment = AssessmentRecord(
            teacher_id=user.id,
            subject_id=data['subject_id'],
            class_id=data['class_id'],
            stream_id=data.get('stream_id'),
            term_id=current_term_id,
            assessment_type=data['assessment_type'],
            title=data['title'],
            description=data.get('description'),
            total_marks=data['total_marks'],
            assessment_date=datetime.strptime(data['assessment_date'], '%Y-%m-%d').date()
        )

        db.session.add(assessment)
        db.session.commit()

        return jsonify({'success': True, 'id': assessment.id})

# Enter Marks Routes
@teacher_bp.route('/enter-marks', methods=['GET', 'POST'])
def enter_marks():
    print(f"DEBUG: enter_marks called - REQUEST METHOD: {request.method}")
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('authbp.login'))

    # Get form data or defaults
    selected_year_id = request.args.get('year_id') or request.form.get('year_id')
    selected_term_id = request.args.get('term_id') or request.form.get('term_id')
    selected_exam_type = request.args.get('exam_type') or request.form.get('exam_type')

    # Get current settings as defaults
    current_term_setting = SystemSetting.query.filter_by(key='current_term_id').first()
    current_year_setting = SystemSetting.query.filter_by(key='current_academic_year_id').first()

    if not selected_year_id and current_year_setting:
        selected_year_id = current_year_setting.value
    if not selected_term_id and current_term_setting:
        selected_term_id = current_term_setting.value
    # Get all available options
    academic_years = AcademicYear.query.order_by(AcademicYear.start_date.desc()).all()
    terms = Term.query.order_by(Term.start_date).all()
    exam_types = [row[0] for row in db.session.query(ExamSchedule.name).distinct().order_by(ExamSchedule.name).all()]

    if not selected_exam_type:
        selected_exam_type = exam_types[0] if exam_types else 'Mid-term'  # default to first available or Mid-term

    # Get pupils and subjects based on selection
    pupils = []
    subjects = []
    existing_results = {}

    print(f"DEBUG: enter_marks - selected_year_id: {selected_year_id}, selected_term_id: {selected_term_id}, selected_exam_type: {selected_exam_type}")

    if selected_year_id and selected_term_id:
        print("DEBUG: Loading pupils and subjects for teacher")
        # Get pupils assigned to this teacher
        teacher_pupils = get_teacher_pupils(user.id)
        print(f"DEBUG: Found {len(teacher_pupils)} teacher pupils")

        # Convert pupils to JSON-serializable format
        pupils = []
        for pupil in teacher_pupils:
            pupils.append({
                'id': pupil.id,
                'admission_number': pupil.admission_number,
                'first_name': pupil.first_name,
                'last_name': pupil.last_name,
                'class_name': pupil.current_class.name if pupil.current_class else '',
                'stream_name': pupil.current_stream.name if pupil.current_stream else ''
            })
        print(f"DEBUG: Converted to {len(pupils)} pupil dictionaries")

        # Get subjects taught by this teacher
        assignments = get_teacher_assignments(user.id)
        teacher_subjects = list(set(assignment.subject for assignment in assignments))
        print(f"DEBUG: Found {len(teacher_subjects)} teacher subjects")
        
        # Convert subjects to JSON-serializable format
        subjects = []
        for subject in teacher_subjects:
            subjects.append({
                'id': subject.id,
                'name': subject.name,
                'can_edit': True  # All subjects in this list can be edited by the teacher
            })
        print(f"DEBUG: Converted to {len(subjects)} subject dictionaries")

        # Get existing assessment results for this year/term/exam_type
        assessments = AssessmentRecord.query.filter_by(
            teacher_id=user.id,
            term_id=selected_term_id
        ).filter(AssessmentRecord.assessment_type == selected_exam_type).all()
        print(f"DEBUG: Found {len(assessments)} existing assessments")

        # Collect all results
        existing_results = {}
        for assessment in assessments:
            for result in assessment.results:
                key = f"{result.pupil_id}_{assessment.subject_id}"
                existing_results[key] = {
                    'marks_obtained': result.marks_obtained,
                    'grade': result.grade,
                    'remarks': result.remarks,
                    'stream_rank': result.stream_rank,
                    'class_rank': result.class_rank
                }
        print(f"DEBUG: Found {len(existing_results)} existing results")
    else:
        print("DEBUG: Not loading pupils - missing year or term")
        pupils = []
        subjects = []
        existing_results = {}

    print(f"DEBUG: Final - pupils: {len(pupils)}, subjects: {len(subjects)}, auto_load_data: {len(pupils) > 0}")

    context = get_teacher_template_context(user)
    context.update({
        'pupils': pupils,
        'subjects': subjects,
        'academic_years': academic_years,
        'terms': terms,
        'exam_types': exam_types,
        'selected_year_id': int(selected_year_id) if selected_year_id else None,
        'selected_term_id': int(selected_term_id) if selected_term_id else None,
        'selected_exam_type': selected_exam_type,
        'existing_results': existing_results,
        'auto_load_data': len(pupils) > 0  # Pass flag to auto-load on frontend
    })

    return render_template('teacher/enter_marks.html', **context)

@teacher_bp.route('/load-marks-data', methods=['GET'])
def load_marks_data():
    print(f"DEBUG: load_marks_data called - REQUEST METHOD: {request.method}")
    print(f"DEBUG: Session contents: {dict(session)}")
    if 'user_id' not in session:
        print("DEBUG: No user_id in session")
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        print(f"DEBUG: User not found or not teacher: user={user}, role={user.role.name if user else 'None'}")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    print(f"DEBUG: Logged in user: ID={user.id}, Username={user.username}, Role={user.role.name}")

    academic_year_id = request.args.get('academic_year_id')
    term_id = request.args.get('term_id')
    exam_type = request.args.get('exam_type')

    print(f"DEBUG: Parameters - year: {academic_year_id}, term: {term_id}, exam: {exam_type}")

    if not all([academic_year_id, term_id, exam_type]):
        return jsonify({'success': False, 'message': 'Missing required parameters'}), 400

    try:
        # Get pupils assigned to this teacher (only from their assigned classes/streams)
        teacher_pupils = get_teacher_pupils(user.id)
        print(f"DEBUG: User ID {user.id} ({user.username}) - Found {len(teacher_pupils)} pupils assigned to teacher")
        for pupil in teacher_pupils:
            print(f"DEBUG: Pupil: {pupil.admission_number} {pupil.first_name} {pupil.last_name} - Class: {pupil.current_class.name if pupil.current_class else 'None'} {pupil.current_stream.name if pupil.current_stream else 'None'}")

        # Get subjects taught by this teacher
        assignments = get_teacher_assignments(user.id)
        teacher_subjects = list(set(assignment.subject for assignment in assignments))
        teacher_subject_ids = [s.id for s in teacher_subjects]
        print(f"DEBUG: Teacher can edit {len(teacher_subjects)} subjects: {[s.name for s in teacher_subjects]}")

        # Get all subjects for display (but mark which ones teacher can edit)
        all_subjects = Subject.query.order_by(Subject.name).all()
        print(f"DEBUG: Found {len(all_subjects)} total subjects")

        # Convert to JSON-serializable format
        pupils_data = []
        for pupil in teacher_pupils:
            pupils_data.append({
                'id': pupil.id,
                'admission_number': pupil.admission_number,
                'first_name': pupil.first_name,
                'last_name': pupil.last_name,
                'class_name': pupil.current_class.name if pupil.current_class else '',
                'stream_name': pupil.current_stream.name if pupil.current_stream else ''
            })

        subjects_data = []
        for subject in all_subjects:
            subjects_data.append({
                'id': subject.id,
                'name': subject.name,
                'can_edit': subject.id in teacher_subject_ids  # Mark if teacher can edit this subject
            })

        # Get existing assessment results for this year/term/exam_type
        existing_marks = {}

        # Get all assessments for this teacher, term, and exam type
        assessments = AssessmentRecord.query.filter_by(
            teacher_id=user.id,
            term_id=term_id,
            assessment_type=exam_type
        ).all()

        print(f"DEBUG: Found {len(assessments)} existing assessments")

        # Collect all existing results
        for assessment in assessments:
            for result in assessment.results:
                key = f"{result.pupil_id}_{assessment.subject_id}"
                existing_marks[key] = {
                    'marks_obtained': result.marks_obtained,
                    'grade': result.grade,
                    'remarks': result.remarks,
                    'stream_rank': result.stream_rank,
                    'class_rank': result.class_rank
                }

        print(f"DEBUG: Found {len(existing_marks)} existing marks")

        # Compute total points and positions for each pupil
        def extract_points_from_remarks(remarks):
            if not remarks or remarks == '--':
                return '--'
            import re
            points_match = re.search(r'Points:\s*(\d+)', remarks)
            return points_match.group(1) if points_match else '--'

        def get_ordinal(n):
            if 10 <= n % 100 <= 20:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            return f"{n}{suffix}"

        pupil_totals = {}
        for pupil in pupils_data:
            total_points = 0
            subject_count = 0
            for subject in subjects_data:
                key = f"{pupil['id']}_{subject['id']}"
                if key in existing_marks:
                    points = extract_points_from_remarks(existing_marks[key]['remarks'])
                    if points != '--':
                        total_points += int(points)
                        subject_count += 1
            pupil_totals[pupil['id']] = {
                'total_points': total_points,
                'subject_count': subject_count,
                'class_name': pupil['class_name'],
                'stream_name': pupil['stream_name']
            }

        # Compute stream positions
        stream_groups = {}
        for pid, data in pupil_totals.items():
            key = f"{data['class_name']}_{data['stream_name']}"
            if key not in stream_groups:
                stream_groups[key] = []
            stream_groups[key].append((pid, data['total_points']))

        for group in stream_groups.values():
            group.sort(key=lambda x: x[1], reverse=True)
            total_in_stream = len(group)
            for rank, (pid, _) in enumerate(group, 1):
                pupil_totals[pid]['stream_position'] = get_ordinal(rank)
                pupil_totals[pid]['stream_total'] = total_in_stream

        # Compute class positions
        class_groups = {}
        for pid, data in pupil_totals.items():
            key = data['class_name']
            if key not in class_groups:
                class_groups[key] = []
            class_groups[key].append((pid, data['total_points']))

        for group in class_groups.values():
            group.sort(key=lambda x: x[1], reverse=True)
            total_in_class = len(group)
            for rank, (pid, _) in enumerate(group, 1):
                pupil_totals[pid]['class_position'] = get_ordinal(rank)
                pupil_totals[pid]['class_total'] = total_in_class

        # Add positions to pupils_data
        for pupil in pupils_data:
            pid = pupil['id']
            pupil['stream_position'] = pupil_totals.get(pid, {}).get('stream_position', '--')
            pupil['stream_total'] = pupil_totals.get(pid, {}).get('stream_total', '--')
            pupil['class_position'] = pupil_totals.get(pid, {}).get('class_position', '--')
            pupil['class_total'] = pupil_totals.get(pid, {}).get('class_total', '--')

        return jsonify({
            'success': True,
            'pupils': pupils_data,
            'subjects': subjects_data,
            'existing_marks': existing_marks,
            'stream_totals': {key: len(group) for key, group in stream_groups.items()},
            'class_totals': {key: len(group) for key, group in class_groups.items()}
        })

    except Exception as e:
        print(f"DEBUG: Error in load_marks_data: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@teacher_bp.route('/save-marks', methods=['POST'])
def save_marks():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    year_id = data.get('academic_year_id')
    term_id = data.get('term_id')
    exam_type = data.get('exam_type')
    marks_data = data.get('marks_data', [])

    print(f"DEBUG save_marks: user_id={user.id}, year={year_id}, term={term_id}, exam={exam_type}")
    print(f"DEBUG save_marks: marks_data length={len(marks_data)}")

    if not all([year_id, term_id, exam_type]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    try:
        # Get teacher's assigned subjects for validation
        assignments = get_teacher_assignments(user.id)
        teacher_subject_ids = [assignment.subject_id for assignment in assignments]
        print(f"DEBUG save_marks: Teacher can save marks for subjects: {teacher_subject_ids}")

        # Process marks for each subject
        saved_count = 0
        for subject_marks in marks_data:
            subject_id = subject_marks['subject_id']

            # Only save marks for subjects the teacher is assigned to
            if subject_id not in teacher_subject_ids:
                print(f"DEBUG save_marks: Skipping subject {subject_id} - not assigned to teacher")
                continue

            pupil_marks = subject_marks['pupil_marks']

            print(f"DEBUG save_marks: processing subject {subject_id}, pupil_marks count={len(pupil_marks)}")

            # Find or create assessment for this subject
            assessment = AssessmentRecord.query.filter_by(
                teacher_id=user.id,
                subject_id=subject_id,
                term_id=term_id,
                assessment_type=exam_type
            ).first()

            if not assessment:
                # Get class/stream from teacher's assignments
                assignment = TeacherAssignment.query.filter_by(
                    teacher_id=user.id,
                    subject_id=subject_id
                ).first()
                if not assignment:
                    print(f"DEBUG save_marks: No assignment found for teacher {user.id}, subject {subject_id}")
                    continue

                assessment = AssessmentRecord(
                    teacher_id=user.id,
                    subject_id=subject_id,
                    class_id=assignment.class_stream.class_id,
                    stream_id=assignment.class_stream.stream_id,
                    term_id=term_id,
                    assessment_type=exam_type,
                    title=f"{exam_type} - {Subject.query.get(subject_id).name}",
                    total_marks=100,  # default
                    assessment_date=datetime.now().date()
                )
                db.session.add(assessment)
                db.session.flush()  # to get the id
                print(f"DEBUG save_marks: Created new assessment {assessment.id}")

            # Save marks for pupils
            for pupil_data in pupil_marks:
                pupil_id = pupil_data['pupil_id']
                marks_obtained = float(pupil_data['marks_obtained']) if pupil_data['marks_obtained'] else None
                remarks = pupil_data.get('remarks', '')

                print(f"DEBUG save_marks: saving pupil {pupil_id}, marks {marks_obtained}")

                if marks_obtained is not None:
                    # Calculate grade and points using UNEB system
                    percentage = marks_obtained  # marks_obtained is already a percentage
                    grade = calculate_grade(percentage)
                    points = calculate_points(percentage)

                    # Check if result exists
                    existing_result = AssessmentResult.query.filter_by(
                        assessment_record_id=assessment.id,
                        pupil_id=pupil_id
                    ).first()

                    if existing_result:
                        existing_result.marks_obtained = marks_obtained
                        existing_result.grade = grade
                        existing_result.remarks = f"Points: {points} | {remarks}"
                        print(f"DEBUG save_marks: Updated existing result")
                    else:
                        new_result = AssessmentResult(
                            assessment_record_id=assessment.id,
                            pupil_id=pupil_id,
                            marks_obtained=marks_obtained,
                            grade=grade,
                            remarks=f"Points: {points} | {remarks}"
                        )
                        db.session.add(new_result)
                        print(f"DEBUG save_marks: Created new result")

                    saved_count += 1

        db.session.commit()
        print(f"DEBUG save_marks: Successfully saved {saved_count} marks")

        # Calculate rankings for all assessments
        assessments = AssessmentRecord.query.filter_by(
            teacher_id=user.id,
            term_id=term_id,
            assessment_type=exam_type
        ).all()

        for assessment in assessments:
            calculate_rankings(assessment.id)

        return jsonify({'success': True, 'message': f'Saved {saved_count} marks successfully'})

    except Exception as e:
        db.session.rollback()
        print(f"DEBUG save_marks: Error - {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@teacher_bp.route('/calculate-grades', methods=['POST'])
def calculate_grades():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json()
    pupil_id = data.get('pupil_id')
    subject_marks = data.get('subject_marks', {})  # {subject_id: marks}

    if not pupil_id:
        return jsonify({'success': False, 'message': 'Missing pupil_id'}), 400

    try:
        # Get teacher's subjects
        assignments = get_teacher_assignments(user.id)
        teacher_subjects = {assignment.subject_id: assignment.subject for assignment in assignments}

        # Calculate grades and points for each subject
        subject_grades = {}
        subject_points = {}
        total_points = 0
        subject_count = 0

        for subject_id, marks in subject_marks.items():
            if subject_id in teacher_subjects:
                percentage = float(marks)
                grade = calculate_grade(percentage)
                points = calculate_points(percentage)
                subject_grades[subject_id] = grade
                subject_points[subject_id] = points
                total_points += points
                subject_count += 1

        # Calculate overall division (simplified - assuming all subjects are considered)
        # In UNEB, it's based on best 4 subjects, but for simplicity, using all
        overall_division = calculate_division(total_points) if subject_count > 0 else '--'

        # For ranking, we need to compare with all pupils
        # This is a simplified version - in real implementation, you'd calculate based on all pupils' aggregates
        rank = "--"  # Placeholder

        # Generate remarks based on performance
        remarks = generate_remarks(total_points, subject_count)

        return jsonify({
            'success': True,
            'subject_grades': subject_grades,
            'subject_points': subject_points,
            'total_aggregate': total_points,
            'overall_division': overall_division,
            'rank': rank,
            'remarks': remarks
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def generate_remarks(total_aggregate, subject_count):
    """Generate remarks based on UNEB aggregate performance"""
    if subject_count == 0:
        return "No subjects to evaluate."
    
    avg_points = total_aggregate / subject_count
    
    if total_aggregate <= 12:
        return "Excellent performance! Outstanding achievement."
    elif total_aggregate <= 23:
        return "Very good work. Continue to excel."
    elif total_aggregate <= 29:
        return "Good performance. Room for improvement in some areas."
    elif total_aggregate <= 34:
        return "Satisfactory performance. Needs to work harder."
    else:
        return "Poor performance. Immediate attention needed."

def calculate_grade(percentage):
    """Calculate UNEB grade based on percentage"""
    if percentage >= 80:
        return '1'
    elif percentage >= 75:
        return '2'
    elif percentage >= 65:
        return '3'
    elif percentage >= 60:
        return '4'
    elif percentage >= 55:
        return '5'
    elif percentage >= 50:
        return '6'
    elif percentage >= 45:
        return '7'
    elif percentage >= 40:
        return '8'
    else:
        return '9'

def calculate_points(percentage):
    """Calculate UNEB points based on percentage"""
    if percentage >= 80:
        return 1
    elif percentage >= 75:
        return 2
    elif percentage >= 65:
        return 3
    elif percentage >= 60:
        return 4
    elif percentage >= 55:
        return 5
    elif percentage >= 50:
        return 6
    elif percentage >= 45:
        return 7
    elif percentage >= 40:
        return 8
    else:
        return 9

def calculate_division(total_aggregate):
    """Calculate final division based on 4-subject aggregate"""
    if total_aggregate <= 12:
        return 'Division 1'
    elif total_aggregate <= 23:
        return 'Division 2'
    elif total_aggregate <= 29:
        return 'Division 3'
    elif total_aggregate <= 34:
        return 'Division 4'
    else:
        return 'Ungraded (Fail)'

def calculate_rankings(assessment_id):
    """Calculate and update rankings for the assessment"""
    # Get all results for this assessment
    results = AssessmentResult.query.filter_by(assessment_record_id=assessment_id).all()

    if not results:
        return

    # Sort by marks obtained (descending)
    sorted_results = sorted(results, key=lambda x: x.marks_obtained, reverse=True)

    # Update rankings
    for rank, result in enumerate(sorted_results, 1):
        result.stream_rank = rank  # For now, treating as stream rank
        result.class_rank = rank   # For now, treating as class rank

    db.session.commit()

# Subject Remarks Routes
@teacher_bp.route('/subject-remarks')
def subject_remarks():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    pupils = get_teacher_pupils(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments, 'pupils': pupils})
    return render_template('teacher/subject_remarks.html', **context)

# Progress Summaries Routes
@teacher_bp.route('/progress-summaries')
def progress_summaries():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    pupils = get_teacher_pupils(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments, 'pupils': pupils})
    return render_template('teacher/progress_summaries.html', **context)

# Curriculum Access Routes
@teacher_bp.route('/curriculum-access')
def curriculum_access():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments})
    return render_template('teacher/curriculum_access.html', **context)

# Lesson Plans Routes
@teacher_bp.route('/lesson-plans')
def lesson_plans():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments})
    return render_template('teacher/lesson_plans.html', **context)

# Homework Tracking Routes
@teacher_bp.route('/homework-tracking')
def homework_tracking():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments})
    return render_template('teacher/homework_tracking.html', **context)

# Exam Schedules Routes
@teacher_bp.route('/exam-schedules')
def exam_schedules():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('authbp.login'))

    assignments = get_teacher_assignments(user.id)

    # Get current term
    current_term_setting = SystemSetting.query.filter_by(key='current_term_id').first()
    current_term_id = int(current_term_setting.value) if current_term_setting else None

    exam_schedules = []
    if current_term_id and assignments:
        # Get all class-subject combinations that the teacher is assigned to
        teacher_class_subjects = []
        for assignment in assignments:
            if assignment.class_stream and assignment.subject:
                teacher_class_subjects.append({
                    'class_id': assignment.class_stream.class_id,
                    'subject_id': assignment.subject_id
                })

        if teacher_class_subjects:
            # Build filter conditions for class-subject combinations
            filter_conditions = []
            for combo in teacher_class_subjects:
                filter_conditions.append(
                    and_(ExamSchedule.class_id == combo['class_id'], 
                         ExamSchedule.subject_id == combo['subject_id'])
                )
            
            # Fetch exam schedules only for subjects and classes the teacher is assigned to
            exam_schedules = ExamSchedule.query.filter(
                ExamSchedule.term_id == current_term_id,
                or_(*filter_conditions)
            ).options(
                db.selectinload(ExamSchedule.subject),
                db.selectinload(ExamSchedule.school_class),
                db.selectinload(ExamSchedule.term)
            ).order_by(ExamSchedule.exam_date).all()

    context = get_teacher_template_context(user)
    context.update({'assignments': assignments, 'exam_schedules': exam_schedules})

    # Check if this is an AJAX request (from loadContent)
    from flask import request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # For AJAX requests, return the full template (loadContent will extract main-content)
        return render_template('teacher/exam_schedules.html', **context)
    else:
        # For direct access, redirect to dashboard
        return redirect(url_for('teacher.dashboard'))

# Pupil Information Routes
@teacher_bp.route('/pupil-profiles')
def pupil_profiles():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('authbp.login'))

    assignments = get_teacher_assignments(user.id)
    if not assignments:
        flash('You need to be assigned to classes and streams before accessing pupil profiles.', 'warning')
        return redirect(url_for('teacher.dashboard'))

    pupils = get_teacher_pupils(user.id)
    context = get_teacher_template_context(user)
    context.update({'pupils': pupils})
    return render_template('teacher/pupil_profiles.html', **context)

@teacher_bp.route('/academic-history')
def academic_history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    pupils = get_teacher_pupils(user.id)
    context = get_teacher_template_context(user)
    context.update({'pupils': pupils})
    return render_template('teacher/academic_history.html', **context)

@teacher_bp.route('/learning-needs')
def learning_needs():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    pupils = get_teacher_pupils(user.id)
    learning_needs = LearningNeed.query.filter(LearningNeed.pupil_id.in_([p.id for p in pupils])).all()
    context = get_teacher_template_context(user)
    context.update({'pupils': pupils, 'learning_needs': learning_needs})
    return render_template('teacher/learning_needs.html', **context)

@teacher_bp.route('/disciplinary-notes')
def disciplinary_notes():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    pupils = get_teacher_pupils(user.id)
    notes = DisciplinaryNote.query.filter(DisciplinaryNote.pupil_id.in_([p.id for p in pupils])).all()
    context = get_teacher_template_context(user)
    context.update({'pupils': pupils, 'notes': notes})
    return render_template('teacher/disciplinary_notes.html', **context)

@teacher_bp.route('/teacher-notes')
def teacher_notes():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    pupils = get_teacher_pupils(user.id)
    notes = TeacherNote.query.filter_by(teacher_id=user.id).all()
    context = get_teacher_template_context(user)
    context.update({'pupils': pupils, 'notes': notes})
    return render_template('teacher/teacher_notes.html', **context)

# Reports & Analytics Routes
@teacher_bp.route('/class-performance')
def class_performance():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments})
    return render_template('teacher/class_performance.html', **context)

@teacher_bp.route('/subject-trends')
def subject_trends():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments})
    return render_template('teacher/subject_trends.html', **context)

@teacher_bp.route('/attendance-reports')
def attendance_reports():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments})
    return render_template('teacher/attendance_reports.html', **context)

@teacher_bp.route('/class-reports')
def class_reports():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    assignments = get_teacher_assignments(user.id)
    context = get_teacher_template_context(user)
    context.update({'assignments': assignments})
    return render_template('teacher/class_reports.html', **context)

# API Routes for AJAX functionality

@teacher_bp.route('/api/subject-remarks', methods=['GET', 'POST'])
def api_subject_remarks():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'GET':
        filters = request.args
        query = SubjectRemark.query.join(Pupil).filter(Pupil.id.in_([p.id for p in get_teacher_pupils(user.id)]))

        if filters.get('class_id'):
            query = query.filter(Pupil.current_class_id == filters['class_id'])
        if filters.get('subject_id'):
            query = query.filter(SubjectRemark.subject_id == filters['subject_id'])
        if filters.get('pupil_id'):
            query = query.filter(SubjectRemark.pupil_id == filters['pupil_id'])

        remarks = query.order_by(SubjectRemark.created_at.desc()).all()

        return jsonify([{
            'id': r.id,
            'pupil_name': f"{r.pupil.first_name} {r.pupil.last_name}",
            'class_name': r.pupil.current_class.name,
            'subject_name': r.subject.name,
            'remark': r.remark,
            'remark_type': r.remark_type,
            'remark_date': r.remark_date.strftime('%Y-%m-%d'),
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M')
        } for r in remarks])

    elif request.method == 'POST':
        data = request.get_json()

        remark = SubjectRemark(
            pupil_id=data['pupil_id'],
            subject_id=data['subject_id'],
            teacher_id=user.id,
            remark_type=data['remark_type'],
            remark_date=datetime.strptime(data['remark_date'], '%Y-%m-%d').date(),
            remark=data['remark'],
            additional_notes=data.get('additional_notes')
        )

        db.session.add(remark)
        db.session.commit()

        return jsonify({'success': True, 'id': remark.id})

@teacher_bp.route('/api/progress-summaries', methods=['GET', 'POST'])
def api_progress_summaries():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == 'GET':
        filters = request.args
        query = ProgressSummary.query.join(Pupil).filter(Pupil.id.in_([p.id for p in get_teacher_pupils(user.id)]))

        if filters.get('class_id'):
            query = query.filter(Pupil.current_class_id == filters['class_id'])
        if filters.get('pupil_id'):
            query = query.filter(ProgressSummary.pupil_id == filters['pupil_id'])

        summaries = query.order_by(ProgressSummary.created_at.desc()).all()

        return jsonify([{
            'id': s.id,
            'pupil_name': f"{s.pupil.first_name} {s.pupil.last_name}",
            'class_name': s.pupil.current_class.name,
            'term_name': s.term.name,
            'overall_grade': s.overall_grade,
            'attendance_percentage': s.attendance_percentage,
            'status': s.status,
            'created_at': s.created_at.strftime('%Y-%m-%d')
        } for s in summaries])

    elif request.method == 'POST':
        data = request.get_json()

        summary = ProgressSummary(
            pupil_id=data['pupil_id'],
            teacher_id=user.id,
            term_id=data['term_id'],
            overall_grade=data['overall_grade'],
            attendance_percentage=data['attendance_percentage'],
            status=data['status'],
            academic_performance=data['academic_performance'],
            strengths=data.get('strengths'),
            areas_for_improvement=data.get('areas_for_improvement'),
            recommendations=data.get('recommendations'),
            additional_comments=data.get('additional_comments')
        )

        db.session.add(summary)
        db.session.commit()

        return jsonify({'success': True, 'id': summary.id})

@teacher_bp.route('/api/pupil-profiles', methods=['GET'])
def api_pupil_profiles():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return jsonify({'error': 'Unauthorized'}), 401

    search = request.args.get('search', '')

    # Get teacher pupils with joined relationships - optimized single query
    teacher_pupils = get_teacher_pupils(user.id)

    # Convert to query for filtering
    if teacher_pupils:
        pupil_ids = [p.id for p in teacher_pupils]
        query = Pupil.query.filter(Pupil.id.in_(pupil_ids)).options(
            # Use selectinload for better performance with multiple related objects
            db.selectinload(Pupil.current_class),
            db.selectinload(Pupil.current_stream)
        )
    else:
        # If no pupils, return empty query
        query = Pupil.query.filter(Pupil.id == -1)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Pupil.first_name.ilike(search_filter),
                Pupil.last_name.ilike(search_filter),
                Pupil.admission_number.ilike(search_filter)
            )
        )

    # Load all pupils at once (no pagination)
    pupils = query.all()

    return jsonify({
        'pupils': [{
            'id': p.id,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'admission_number': p.admission_number,
            'current_class': p.current_class.name if p.current_class else 'Not Assigned',
            'current_stream': p.current_stream.name if p.current_stream else None
        } for p in pupils],
        'total_pupils': len(pupils)
    })

@teacher_bp.route('/api/pupil-details/<int:pupil_id>', methods=['GET'])
def api_pupil_details(pupil_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return jsonify({'error': 'Unauthorized'}), 401

    # Check if pupil is assigned to this teacher
    teacher_pupils = get_teacher_pupils(user.id)
    pupil_ids = [p.id for p in teacher_pupils]

    if pupil_id not in pupil_ids:
        return jsonify({'error': 'Pupil not found or not assigned to you'}), 404

    pupil = Pupil.query.get_or_404(pupil_id)

    return jsonify({
        'id': pupil.id,
        'first_name': pupil.first_name,
        'last_name': pupil.last_name,
        'admission_number': pupil.admission_number,
        'date_of_birth': pupil.date_of_birth.strftime('%Y-%m-%d') if pupil.date_of_birth else None,
        'gender': pupil.gender,
        'nationality': pupil.nationality,
        'religion': pupil.religion,
        'current_class': pupil.current_class.name,
        'current_stream': pupil.current_stream.name if pupil.current_stream else None,
        'admission_date': pupil.admission_date.strftime('%Y-%m-%d') if pupil.admission_date else None,
        'phone': pupil.phone,
        'email': pupil.email,
        'address': pupil.address,
        'father_name': pupil.father_name,
        'mother_name': pupil.mother_name,
        'guardian_phone': pupil.guardian_phone
    })

@teacher_bp.route('/pupil-details/<int:pupil_id>')
def pupil_details(pupil_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('auth.login'))

    # Check if pupil is assigned to this teacher
    teacher_pupils = get_teacher_pupils(user.id)
    pupil_ids = [p.id for p in teacher_pupils]

    if pupil_id not in pupil_ids:
        return "Pupil not found or not assigned to you", 404

    pupil = Pupil.query.get_or_404(pupil_id)
    context = get_teacher_template_context(user)
    context.update({'pupil': pupil})
    return render_template('teacher/pupil_details.html', **context)

@teacher_bp.route('/api/academic-history', methods=['GET'])
def api_academic_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Teacher':
        return jsonify({'error': 'Unauthorized'}), 401

    pupil_id = request.args.get('pupil_id')
    academic_year_id = request.args.get('academic_year_id')
    term_id = request.args.get('term_id')

    if not pupil_id:
        return jsonify({'error': 'Pupil ID required'}), 400

    # Check if pupil is assigned to this teacher
    teacher_pupils = get_teacher_pupils(user.id)
    pupil_ids = [p.id for p in teacher_pupils]

    if int(pupil_id) not in pupil_ids:
        return jsonify({'error': 'Pupil not found or not assigned to you'}), 404

    pupil = Pupil.query.get_or_404(pupil_id)

    # Get assessments
    assessment_query = AssessmentResult.query.filter_by(pupil_id=pupil_id)
    if academic_year_id:
        assessment_query = assessment_query.join(AssessmentRecord).filter(AssessmentRecord.term.has(academic_year_id=academic_year_id))
    if term_id:
        assessment_query = assessment_query.join(AssessmentRecord).filter(AssessmentRecord.term_id == term_id)

    assessments = assessment_query.options(
        db.selectinload(AssessmentResult.assessment_record).selectinload(AssessmentRecord.subject),
        db.selectinload(AssessmentResult.assessment_record).selectinload(AssessmentRecord.term)
    ).all()

    # Get progress summaries
    summary_query = ProgressSummary.query.filter_by(pupil_id=pupil_id)
    if academic_year_id:
        summary_query = summary_query.join(Term).filter(Term.academic_year_id == academic_year_id)
    if term_id:
        summary_query = summary_query.filter(ProgressSummary.term_id == term_id)

    summaries = summary_query.options(
        db.selectinload(ProgressSummary.term).selectinload(Term.academic_year)
    ).all()

    # Calculate stats
    total_assessments = len(assessments)
    average_score = 0
    if assessments:
        total_percentage = sum((a.marks_obtained / a.assessment_record.total_marks) * 100 for a in assessments if a.assessment_record.total_marks > 0)
        average_score = total_percentage / len(assessments)

    latest_summary = max(summaries, key=lambda s: s.created_at) if summaries else None

    return jsonify({
        'pupil': {
            'id': pupil.id,
            'first_name': pupil.first_name,
            'last_name': pupil.last_name,
            'admission_number': pupil.admission_number,
            'current_class': pupil.current_class.name,
            'current_stream': pupil.current_stream.name if pupil.current_stream else None
        },
        'assessments': [{
            'id': a.id,
            'subject': a.assessment_record.subject.name,
            'title': a.assessment_record.title,
            'score': a.marks_obtained,
            'total_marks': a.assessment_record.total_marks,
            'date': a.assessment_record.assessment_date.strftime('%Y-%m-%d')
        } for a in assessments],
        'summaries': [{
            'id': s.id,
            'term': s.term.name,
            'overall_grade': s.overall_grade,
            'attendance_percentage': s.attendance_percentage,
            'status': s.status,
            'academic_performance': s.academic_performance
        } for s in summaries],
        'stats': {
            'total_assessments': total_assessments,
            'average_score': round(average_score, 1) if average_score else None,
            'total_summaries': len(summaries),
            'latest_grade': latest_summary.overall_grade if latest_summary else None
        }
    })

@teacher_bp.route('/api/academic-years', methods=['GET'])
def api_academic_years():
    academic_years = AcademicYear.query.order_by(AcademicYear.start_date.desc()).all()
    return jsonify([{
        'id': ay.id,
        'name': ay.name
    } for ay in academic_years])

@teacher_bp.route('/api/terms', methods=['GET'])
def api_terms():
    terms = Term.query.join(AcademicYear).order_by(AcademicYear.start_date.desc(), Term.start_date).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'academic_year': t.academic_year.name
    } for t in terms])