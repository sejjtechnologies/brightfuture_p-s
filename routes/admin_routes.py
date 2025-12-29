from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.auth_models import SystemUser, Role, db
from models.admin_models import SchoolClass, Subject, Stream, ClassStream, TeacherAssignment, AcademicYear, Term, ExamSchedule, Notification, NotificationRead, SystemSetting
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy import text
import pytz

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/check_duplicate/<type>/<name>')
def check_duplicate(type, name):
    if 'user_id' not in session:
        return {'exists': False}
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return {'exists': False}
    exclude_id = request.args.get('exclude_id')
    exists = False
    if type == 'class':
        query = SchoolClass.query.filter_by(name=name)
        if exclude_id:
            query = query.filter(SchoolClass.id != exclude_id)
        exists = query.first() is not None
    elif type == 'subject':
        query = Subject.query.filter_by(name=name)
        if exclude_id:
            query = query.filter(Subject.id != exclude_id)
        exists = query.first() is not None
    elif type == 'stream':
        query = Stream.query.filter_by(name=name)
        if exclude_id:
            query = query.filter(Stream.id != exclude_id)
        exists = query.first() is not None
    elif type == 'notification':
        query = Notification.query.filter_by(title=name)
        if exclude_id:
            query = query.filter(Notification.id != exclude_id)
        exists = query.first() is not None
    return {'exists': exists}

@admin_bp.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))

    # Check maintenance mode - admins can still access during maintenance
    # maintenance_setting = SystemSetting.query.filter_by(key='enable_maintenance_mode').first()
    # if maintenance_setting and maintenance_setting.value == 'true':
    #     return render_template('maintenance.html')

    # Import the utility function
    from app import get_term_progress_info
    term_progress = get_term_progress_info()

    return render_template('admin/dashboard.html', term_progress=term_progress)

@admin_bp.route('/create_staff', methods=['GET', 'POST'])
def create_staff():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    
    # Get minimum password length from settings
    min_length_setting = SystemSetting.query.filter_by(key='min_password_length').first()
    min_length = int(min_length_setting.value) if min_length_setting else 8
    
    roles = Role.query.filter(Role.name != 'Admin').all()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role_id = request.form['role_id']
        
        if len(password) < min_length:
            flash(f'Password must be at least {min_length} characters long!')
            return redirect(url_for('admin.create_staff'))
        
        role = Role.query.get(role_id)
        if not role:
            flash('Role not found!')
            return redirect(url_for('admin.create_staff'))
        hashed = generate_password_hash(password)
        # Get the next display_id
        max_display_id = db.session.query(db.func.max(SystemUser.display_id)).scalar() or 0
        new_user = SystemUser(display_id=max_display_id + 1, username=username, email=email, password_hash=hashed, role_id=role.id)
        db.session.add(new_user)
        db.session.commit()
        flash('Staff created successfully!')
        return redirect(url_for('admin.dashboard'))
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/create_staff.html', roles=roles, min_password_length=min_length)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    
    # Get minimum password length from settings
    min_length_setting = SystemSetting.query.filter_by(key='min_password_length').first()
    min_length = int(min_length_setting.value) if min_length_setting else 8
    
    if request.method == 'POST':
        # Handle edit
        user_id = request.form.get('user_id')
        username = request.form.get('username')
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        password = request.form.get('password')
        u = SystemUser.query.get(user_id)
        if u:
            if password and len(password) < min_length:
                flash(f'Password must be at least {min_length} characters long!')
                return redirect(url_for('admin.manage_users'))
            u.username = username
            u.email = email
            u.role_id = role_id
            if password:
                u.set_password(password)
            db.session.commit()
            flash('User updated successfully!')
        return redirect(url_for('admin.manage_users'))
    users = SystemUser.query.order_by(SystemUser.id.asc()).all()
    roles = Role.query.all()
    # Convert times to Kampala (UTC+3)
    kampala_offset = timedelta(hours=3)
    for u in users:
        if u.created_at:
            u.created_at_kampala = (u.created_at + kampala_offset).strftime('%d/%m/%Y %I:%M%p').lower()
        else:
            u.created_at_kampala = 'N/A'
        if u.last_login:
            u.last_login_kampala = (u.last_login + kampala_offset).strftime('%d/%m/%Y %I:%M%p').lower()
        else:
            u.last_login_kampala = 'Never'
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/manage_users.html', users=users, roles=roles, min_password_length=min_length)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    u = SystemUser.query.get(user_id)
    if u:
        # Check for dependencies before deleting
        teacher_assignments = TeacherAssignment.query.filter_by(teacher_id=user_id).count()
        notifications_created = Notification.query.filter_by(created_by=user_id).count()
        notifications_read = NotificationRead.query.filter_by(user_id=user_id).count()
        settings_updated = SystemSetting.query.filter_by(updated_by=user_id).count()
        
        if teacher_assignments > 0:
            flash(f'Cannot delete user: {u.username} has {teacher_assignments} teacher assignment(s). Please remove assignments first.')
            return redirect(url_for('admin.manage_users'))
        elif notifications_created > 0:
            flash(f'Cannot delete user: {u.username} has created {notifications_created} notification(s).')
            return redirect(url_for('admin.manage_users'))
        elif notifications_read > 0 or settings_updated > 0:
            # These can be safely deleted
            NotificationRead.query.filter_by(user_id=user_id).delete()
            SystemSetting.query.filter_by(updated_by=user_id).update({'updated_by': None})
            db.session.commit()
        
        db.session.delete(u)
        db.session.commit()
        
        # Renumber display_ids to maintain sequential numbering
        users = SystemUser.query.order_by(SystemUser.id.asc()).all()
        for display_id, usr in enumerate(users, 1):
            usr.display_id = display_id
        db.session.commit()
        
        flash('User deleted successfully!')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/create_class', methods=['GET', 'POST'])
def create_class():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        name = request.form['name']
        if SchoolClass.query.filter_by(name=name).first():
            flash('Class already exists!')
            return redirect(url_for('admin.create_class'))
        new_class = SchoolClass(name=name)
        db.session.add(new_class)
        db.session.commit()
        flash('Class created successfully!')
        return redirect(url_for('admin.create_class'))
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/create_class.html')

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/manage_classes', methods=['GET', 'POST'])
def manage_classes():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        class_id = request.form.get('class_id')
        name = request.form.get('name')
        c = SchoolClass.query.get(class_id)
        if c:
            if SchoolClass.query.filter(SchoolClass.name == name, SchoolClass.id != class_id).first():
                flash('Class name already exists!')
            else:
                c.name = name
                db.session.commit()
                flash('Class updated successfully!')
        return redirect(url_for('admin.manage_classes'))
    classes = SchoolClass.query.order_by(SchoolClass.id.asc()).all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/manage_classes.html', classes=classes)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_class/<int:class_id>', methods=['POST'])
def delete_class(class_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    c = SchoolClass.query.get(class_id)
    if c:
        db.session.delete(c)
        db.session.commit()
        flash('Class deleted successfully!')
    return redirect(url_for('admin.manage_classes'))

@admin_bp.route('/create_subject', methods=['GET', 'POST'])
def create_subject():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        name = request.form['name']
        if Subject.query.filter_by(name=name).first():
            flash('Subject already exists!')
            return redirect(url_for('admin.create_subject'))
        new_subject = Subject(name=name)
        db.session.add(new_subject)
        db.session.commit()
        flash('Subject created successfully!')
        return redirect(url_for('admin.create_subject'))
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/create_subject.html')

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/manage_subjects', methods=['GET', 'POST'])
def manage_subjects():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        name = request.form.get('name')
        s = Subject.query.get(subject_id)
        if s:
            if Subject.query.filter(Subject.name == name, Subject.id != subject_id).first():
                flash('Subject name already exists!')
            else:
                s.name = name
                db.session.commit()
                flash('Subject updated successfully!')
        return redirect(url_for('admin.manage_subjects'))
    subjects = Subject.query.order_by(Subject.id.asc()).all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/manage_subjects.html', subjects=subjects)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    s = Subject.query.get(subject_id)
    if s:
        db.session.delete(s)
        db.session.commit()
        flash('Subject deleted successfully!')
    return redirect(url_for('admin.manage_subjects'))

@admin_bp.route('/create_stream', methods=['GET', 'POST'])
def create_stream():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        name = request.form['name']
        if Stream.query.filter_by(name=name).first():
            flash('Stream already exists!')
            return redirect(url_for('admin.create_stream'))
        new_stream = Stream(name=name)
        db.session.add(new_stream)
        db.session.commit()
        flash('Stream created successfully!')
        return redirect(url_for('admin.create_stream'))
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/create_stream.html')

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/manage_streams', methods=['GET', 'POST'])
def manage_streams():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        stream_id = request.form.get('stream_id')
        name = request.form.get('name')
        s = Stream.query.get(stream_id)
        if s:
            if Stream.query.filter(Stream.name == name, Stream.id != stream_id).first():
                flash('Stream name already exists!')
            else:
                s.name = name
                db.session.commit()
                flash('Stream updated successfully!')
        return redirect(url_for('admin.manage_streams'))
    streams = Stream.query.order_by(Stream.id.asc()).all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/manage_streams.html', streams=streams)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_stream/<int:stream_id>', methods=['POST'])
def delete_stream(stream_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    s = Stream.query.get(stream_id)
    if s:
        db.session.delete(s)
        db.session.commit()
        flash('Stream deleted successfully!')
    return redirect(url_for('admin.manage_streams'))

@admin_bp.route('/assign_teachers', methods=['GET', 'POST'])
def assign_teachers():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    teachers = SystemUser.query.filter_by(role_id=Role.query.filter_by(name='Teacher').first().id).all()
    classes = SchoolClass.query.all()
    streams = Stream.query.all()
    subjects = Subject.query.all()
    if request.method == 'POST':
        teacher_id = request.form['teacher_id']
        class_id = request.form['class_id']
        stream_id = request.form['stream_id']
        subject_id = request.form['subject_id']
        # Check if class_stream exists, else create
        class_stream = ClassStream.query.filter_by(class_id=class_id, stream_id=stream_id).first()
        if not class_stream:
            class_stream = ClassStream(class_id=class_id, stream_id=stream_id)
            db.session.add(class_stream)
            db.session.commit()
        # Check if assignment exists
        if TeacherAssignment.query.filter_by(teacher_id=teacher_id, class_stream_id=class_stream.id, subject_id=subject_id).first():
            flash('Assignment already exists!')
            return redirect(url_for('admin.assign_teachers'))
        assignment = TeacherAssignment(teacher_id=teacher_id, class_stream_id=class_stream.id, subject_id=subject_id)
        db.session.add(assignment)
        db.session.commit()
        flash('Teacher assigned successfully!')
        return redirect(url_for('admin.assign_teachers'))
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/assign_teachers.html', teachers=teachers, classes=classes, streams=streams, subjects=subjects)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/manage_assignments', methods=['GET', 'POST'])
def manage_assignments():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        assignment_id = request.form.get('assignment_id')
        class_id = request.form.get('class_id')
        stream_id = request.form.get('stream_id')
        subject_id = request.form.get('subject_id')
        # Find or create class_stream
        class_stream = ClassStream.query.filter_by(class_id=class_id, stream_id=stream_id).first()
        if not class_stream:
            class_stream = ClassStream(class_id=class_id, stream_id=stream_id)
            db.session.add(class_stream)
            db.session.commit()
        a = TeacherAssignment.query.get(assignment_id)
        if a:
            # Check if new assignment already exists
            existing = TeacherAssignment.query.filter(
                TeacherAssignment.teacher_id == a.teacher_id,  # Keep same teacher
                TeacherAssignment.class_stream_id == class_stream.id,
                TeacherAssignment.subject_id == subject_id,
                TeacherAssignment.id != assignment_id
            ).first()
            if existing:
                flash('Assignment already exists!')
            else:
                a.class_stream_id = class_stream.id
                a.subject_id = subject_id
                db.session.commit()
                flash('Assignment updated successfully!')
        return redirect(url_for('admin.manage_assignments'))
    assignments = TeacherAssignment.query.join(SystemUser, TeacherAssignment.teacher_id == SystemUser.id)\
        .join(ClassStream, TeacherAssignment.class_stream_id == ClassStream.id)\
        .join(SchoolClass, ClassStream.class_id == SchoolClass.id)\
        .join(Stream, ClassStream.stream_id == Stream.id)\
        .join(Subject, TeacherAssignment.subject_id == Subject.id)\
        .add_columns(SystemUser.username, SchoolClass.id.label('class_id'), SchoolClass.name.label('class_name'), Stream.id.label('stream_id'), Stream.name.label('stream_name'), Subject.id.label('subject_id'), Subject.name.label('subject_name'))\
        .all()
    teachers = SystemUser.query.filter_by(role_id=Role.query.filter_by(name='Teacher').first().id).all()
    classes = SchoolClass.query.all()
    streams = Stream.query.all()
    subjects = Subject.query.all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/manage_assignments.html', assignments=assignments, teachers=teachers, classes=classes, streams=streams, subjects=subjects)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_assignment/<int:assignment_id>', methods=['POST'])
def delete_assignment(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    assignment = TeacherAssignment.query.get(assignment_id)
    if assignment:
        db.session.delete(assignment)
        db.session.commit()
        flash('Assignment deleted successfully!')
    return redirect(url_for('admin.manage_assignments'))

@admin_bp.route('/create_academic_year', methods=['GET', 'POST'])
def create_academic_year():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        name = request.form['name']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        if AcademicYear.query.filter_by(name=name).first():
            flash('Academic year already exists!')
            return redirect(url_for('admin.create_academic_year'))
        new_year = AcademicYear(name=name, start_date=start_date, end_date=end_date)
        db.session.add(new_year)
        db.session.commit()
        flash('Academic year created successfully!')
        return redirect(url_for('admin.create_academic_year'))
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/create_academic_year.html')

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/manage_academic_years', methods=['GET', 'POST'])
def manage_academic_years():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        year_id = request.form.get('year_id')
        name = request.form.get('name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        y = AcademicYear.query.get(year_id)
        if y:
            if AcademicYear.query.filter(AcademicYear.name == name, AcademicYear.id != year_id).first():
                flash('Academic year name already exists!')
            else:
                y.name = name
                y.start_date = start_date
                y.end_date = end_date
                db.session.commit()
                flash('Academic year updated successfully!')
        return redirect(url_for('admin.manage_academic_years'))
    years = AcademicYear.query.order_by(AcademicYear.id.asc()).all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/manage_academic_years.html', years=years)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_academic_year/<int:year_id>', methods=['POST'])
def delete_academic_year(year_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    year = AcademicYear.query.get(year_id)
    if year:
        db.session.delete(year)
        db.session.commit()
        flash('Academic year deleted successfully!')
    return redirect(url_for('admin.manage_academic_years'))

@admin_bp.route('/create_term', methods=['GET', 'POST'])
def create_term():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    academic_years = AcademicYear.query.all()
    if request.method == 'POST':
        name = request.form['name']
        academic_year_id = request.form['academic_year_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        days = request.form['days']
        if Term.query.filter_by(name=name, academic_year_id=academic_year_id).first():
            flash('Term already exists!')
            return redirect(url_for('admin.create_term'))
        new_term = Term(name=name, academic_year_id=academic_year_id, start_date=start_date, end_date=end_date, days=days)
        db.session.add(new_term)
        db.session.commit()
        flash('Term created successfully!')
        return redirect(url_for('admin.create_term'))
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/create_term.html', academic_years=academic_years)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/manage_terms', methods=['GET', 'POST'])
def manage_terms():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        term_id = request.form.get('term_id')
        name = request.form.get('name')
        academic_year_id = request.form.get('academic_year_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        days = request.form.get('days')
        t = Term.query.get(term_id)
        if t:
            if Term.query.filter(Term.name == name, Term.academic_year_id == academic_year_id, Term.id != term_id).first():
                flash('Term already exists!')
            else:
                t.name = name
                t.academic_year_id = academic_year_id
                t.start_date = start_date
                t.end_date = end_date
                t.days = days
                db.session.commit()
                flash('Term updated successfully!')
        return redirect(url_for('admin.manage_terms'))
    terms = Term.query.join(AcademicYear).add_columns(AcademicYear.name.label('year_name')).order_by(Term.id.asc()).all()
    academic_years = AcademicYear.query.all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/manage_terms.html', terms=terms, academic_years=academic_years)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_term/<int:term_id>', methods=['POST'])
def delete_term(term_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    term = Term.query.get(term_id)
    if term:
        db.session.delete(term)
        db.session.commit()
        flash('Term deleted successfully!')
    return redirect(url_for('admin.manage_terms'))

@admin_bp.route('/create_exam_schedule', methods=['GET', 'POST'])
def create_exam_schedule():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    terms = Term.query.all()
    subjects = Subject.query.all()
    classes = SchoolClass.query.all()
    if request.method == 'POST':
        name = request.form['name']
        term_id = request.form['term_id']
        exam_date = request.form['exam_date']
        all_classes_subjects = 'all_classes_subjects' in request.form
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if all_classes_subjects:
            total_possible = len(classes) * len(subjects)
            # Get all existing schedules for this name and term to avoid individual queries
            existing_schedules = ExamSchedule.query.filter_by(name=name, term_id=term_id).all()
            existing_set = {(s.subject_id, s.class_id) for s in existing_schedules}
            schedules_to_add = []
            for cls in classes:
                for subj in subjects:
                    if (subj.id, cls.id) not in existing_set:
                        schedules_to_add.append(ExamSchedule(name=name, term_id=term_id, exam_date=exam_date, subject_id=subj.id, class_id=cls.id))
            db.session.add_all(schedules_to_add)
            db.session.commit()
            created_count = len(schedules_to_add)
            message = f'Exam schedules created for {created_count} class-subject combinations successfully!'
            if created_count == 0:
                message = 'All exam schedules already exist!'
                if is_ajax:
                    return jsonify({'success': False, 'message': message, 'duplicates': ['name']})
                flash(message)
            elif created_count < total_possible:
                message += f' ({total_possible - created_count} duplicates skipped)'
                if is_ajax:
                    return jsonify({'success': True, 'message': message})
                flash(message)
            else:
                if is_ajax:
                    return jsonify({'success': True, 'message': message})
                flash(message)
        else:
            subject_id = request.form['subject_id']
            class_id = request.form['class_id']
            if ExamSchedule.query.filter_by(name=name, term_id=term_id, subject_id=subject_id, class_id=class_id).first():
                message = 'Exam schedule already exists!'
                if is_ajax:
                    return jsonify({'success': False, 'message': message, 'duplicates': ['name', 'term_id', 'subject_id', 'class_id']})
                flash(message)
                return redirect(url_for('admin.create_exam_schedule'))
            new_schedule = ExamSchedule(name=name, term_id=term_id, exam_date=exam_date, subject_id=subject_id, class_id=class_id)
            db.session.add(new_schedule)
            db.session.commit()
            message = 'Exam schedule created successfully!'
            if is_ajax:
                return jsonify({'success': True, 'message': message})
            flash(message)
        return redirect(url_for('admin.create_exam_schedule'))
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/create_exam_schedule.html', terms=terms, subjects=subjects, classes=classes)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/check_exam_duplicate', methods=['POST'])
def check_exam_duplicate():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return jsonify({'error': 'Unauthorized'}), 403
    name = request.form.get('name', '').strip()
    term_id = request.form.get('term_id', '').strip()
    subject_id = request.form.get('subject_id', '')
    class_id = request.form.get('class_id', '')
    all_bulk = request.form.get('all_bulk', 'false') == 'true'
    if not name or not term_id:
        return jsonify({'exists': False})
    if all_bulk:
        exists = ExamSchedule.query.filter_by(name=name, term_id=term_id).first() is not None
    else:
        if not subject_id or not class_id:
            return jsonify({'exists': False})
        exists = ExamSchedule.query.filter_by(name=name, term_id=term_id, subject_id=subject_id, class_id=class_id).first() is not None
    return jsonify({'exists': exists})

@admin_bp.route('/manage_exam_schedules', methods=['GET', 'POST'])
def manage_exam_schedules():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        schedule_id = request.form.get('schedule_id')
        name = request.form.get('name')
        term_id = request.form.get('term_id')
        exam_date = request.form.get('exam_date')
        subject_id = request.form.get('subject_id')
        class_id = request.form.get('class_id')
        s = ExamSchedule.query.get(schedule_id)
        if s:
            if ExamSchedule.query.filter(ExamSchedule.name == name, ExamSchedule.term_id == term_id, ExamSchedule.subject_id == subject_id, ExamSchedule.class_id == class_id, ExamSchedule.id != schedule_id).first():
                flash('Exam schedule already exists!')
            else:
                s.name = name
                s.term_id = term_id
                s.exam_date = exam_date
                s.subject_id = subject_id
                s.class_id = class_id
                db.session.commit()
                flash('Exam schedule updated successfully!')
        return redirect(url_for('admin.manage_exam_schedules'))
    schedules = ExamSchedule.query.join(Term).join(Subject).join(SchoolClass).add_columns(Term.name.label('term_name'), Subject.name.label('subject_name'), SchoolClass.name.label('class_name')).order_by(ExamSchedule.id.asc()).all()
    terms = Term.query.all()
    subjects = Subject.query.all()
    classes = SchoolClass.query.all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('admin/manage_exam_schedules.html', schedules=schedules, terms=terms, subjects=subjects, classes=classes)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_exam_schedule/<int:schedule_id>', methods=['POST'])
def delete_exam_schedule(schedule_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    schedule = ExamSchedule.query.get(schedule_id)
    if schedule:
        db.session.delete(schedule)
        db.session.commit()
        flash('Exam schedule deleted successfully!')
    return redirect(url_for('admin.manage_exam_schedules'))

@admin_bp.route('/create_notification', methods=['GET', 'POST'])
def create_notification():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        visibility = request.form.get('visibility', 'all_except_parents_admins')
        if Notification.query.filter_by(title=title).first():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Notification with this title already exists!'})
            flash('Notification with this title already exists!')
            return redirect(url_for('admin.create_notification'))
        else:
            new_notification = Notification(title=title, message=message, created_by=user.id, visibility=visibility)
            db.session.add(new_notification)
            db.session.commit()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Notification created successfully!'})
            flash('Notification created successfully!')
            return redirect(url_for('admin.dashboard'))
    roles = Role.query.filter(Role.name.notin_(['Admin', 'Parent'])).all()

    # Check if this is an AJAX request (from loadContent)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Check if this is an AJAX request (from loadContent)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

            return render_template('admin/create_notification.html', roles=roles)

        else:

            # Direct access - redirect to dashboard

            return redirect(url_for('admin.dashboard'))
    else:
        # Direct access - redirect to dashboard
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/manage_notifications', methods=['GET', 'POST'])
def manage_notifications():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    if request.method == 'POST':
        notification_id = request.form.get('notification_id')
        title = request.form.get('title')
        message = request.form.get('message')
        visibility = request.form.get('visibility')
        n = Notification.query.get(notification_id)
        if n:
            if Notification.query.filter(Notification.title == title, Notification.id != notification_id).first():
                flash('Notification with this title already exists!')
            else:
                n.title = title
                n.message = message
                n.visibility = visibility
                db.session.commit()
                flash('Notification updated successfully!')
        return redirect(url_for('admin.dashboard'))
    notifications = Notification.query.join(SystemUser).order_by(Notification.created_at.desc()).limit(50).all()
    roles = Role.query.filter(Role.name.notin_(['Admin', 'Parent'])).all()

    # Convert created_at to East Africa Time (Kampala) with AM/PM format
    eat_tz = pytz.timezone('Africa/Nairobi')
    for notification in notifications:
        notification.formatted_created_at = notification.created_at.replace(tzinfo=pytz.utc).astimezone(eat_tz).strftime('%Y-%m-%d %I:%M %p')

    # Check if this is an AJAX request (from loadContent)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/manage_notifications.html', notifications=notifications, roles=roles)
    else:
        # Direct access - redirect to dashboard
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/delete_notification/<int:notification_id>', methods=['POST'])
def delete_notification(notification_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))
    notification = Notification.query.get(notification_id)
    if notification:
        # Delete associated NotificationRead records first
        NotificationRead.query.filter_by(notification_id=notification_id).delete()
        db.session.delete(notification)
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Notification deleted successfully!'})
        else:
            flash('Notification deleted successfully!')
    return redirect(url_for('admin.manage_notifications'))

def populate_default_settings():
    """Populate default system settings if they don't exist"""
    default_settings = [
        # School Information
        {'key': 'school_name', 'value': 'Bright Future Primary School', 'category': 'school_info', 'description': 'The official name of the school', 'data_type': 'string', 'is_public': True},
        {'key': 'school_address', 'value': '', 'category': 'school_info', 'description': 'Complete address of the school', 'data_type': 'text', 'is_public': True},
        {'key': 'school_phone', 'value': '', 'category': 'school_info', 'description': 'Primary contact phone number', 'data_type': 'string', 'is_public': True},
        {'key': 'school_email', 'value': '', 'category': 'school_info', 'description': 'Official email address', 'data_type': 'string', 'is_public': True},

        # Security Settings
        {'key': 'min_password_length', 'value': '8', 'category': 'security', 'description': 'Minimum characters required for passwords', 'data_type': 'integer', 'is_public': False},
        {'key': 'session_timeout', 'value': '30', 'category': 'security', 'description': 'How long before users are automatically logged out (minutes)', 'data_type': 'integer', 'is_public': False},
        {'key': 'max_login_attempts', 'value': '5', 'category': 'security', 'description': 'Number of failed attempts before account lockout', 'data_type': 'integer', 'is_public': False},
        {'key': 'enable_2fa', 'value': 'false', 'category': 'security', 'description': 'Require 2FA for admin accounts', 'data_type': 'boolean', 'is_public': False},

        # Communication Settings
        {'key': 'smtp_server', 'value': '', 'category': 'communication', 'description': 'Email server hostname', 'data_type': 'string', 'is_public': False},
        {'key': 'smtp_port', 'value': '587', 'category': 'communication', 'description': 'Email server port (usually 587 or 465)', 'data_type': 'integer', 'is_public': False},
        {'key': 'smtp_username', 'value': '', 'category': 'communication', 'description': 'Email account username', 'data_type': 'string', 'is_public': False},
        {'key': 'enable_email_notifications', 'value': 'false', 'category': 'communication', 'description': 'Send email notifications to users', 'data_type': 'boolean', 'is_public': False},

        # General Settings
        {'key': 'timezone', 'value': 'Africa/Nairobi', 'category': 'general', 'description': 'System time zone', 'data_type': 'string', 'is_public': True},
        {'key': 'date_format', 'value': 'DD/MM/YYYY', 'category': 'general', 'description': 'How dates are displayed', 'data_type': 'string', 'is_public': True},
        {'key': 'currency', 'value': 'KES', 'category': 'general', 'description': 'Default currency for financial operations', 'data_type': 'string', 'is_public': True},
        {'key': 'language', 'value': 'en', 'category': 'general', 'description': 'Default language for the system', 'data_type': 'string', 'is_public': True},

        # Maintenance Settings
        {'key': 'backup_frequency', 'value': 'weekly', 'category': 'maintenance', 'description': 'How often to automatically backup the database', 'data_type': 'string', 'is_public': False},
        {'key': 'data_retention_months', 'value': '24', 'category': 'maintenance', 'description': 'How long to keep old records (months)', 'data_type': 'integer', 'is_public': False},
        {'key': 'enable_logging', 'value': 'true', 'category': 'maintenance', 'description': 'Keep detailed logs of system activities', 'data_type': 'boolean', 'is_public': False},
        {'key': 'debug_mode', 'value': 'false', 'category': 'maintenance', 'description': 'Enable detailed error messages (disable in production)', 'data_type': 'boolean', 'is_public': False},
        {'key': 'enable_maintenance_mode', 'value': 'false', 'category': 'maintenance', 'description': 'Enable system maintenance mode (blocks all logins)', 'data_type': 'boolean', 'is_public': False},
    ]

    for setting_data in default_settings:
        existing = SystemSetting.query.filter_by(key=setting_data['key']).first()
        if not existing:
            setting = SystemSetting(
                key=setting_data['key'],
                value=setting_data['value'],
                category=setting_data['category'],
                description=setting_data['description'],
                data_type=setting_data['data_type'],
                is_public=setting_data['is_public']
            )
            db.session.add(setting)
    db.session.commit()

@admin_bp.route('/system_settings', methods=['GET', 'POST'])
def system_settings():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))

    # Populate default settings if this is the first access
    populate_default_settings()

    if request.method == 'POST':
        # Handle bulk settings update
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key[8:]  # Remove 'setting_' prefix
                setting = SystemSetting.query.filter_by(key=setting_key).first()
                if setting:
                    setting.value = value
                    setting.updated_by = user.id
                    db.session.commit()
        flash('System settings updated successfully!')
        return redirect(url_for('admin.system_settings'))

    # Get all settings grouped by category
    settings = SystemSetting.query.order_by(SystemSetting.category, SystemSetting.key).all()
    settings_by_category = {}
    for setting in settings:
        if setting.category not in settings_by_category:
            settings_by_category[setting.category] = []
        settings_by_category[setting.category].append(setting)

    # Create a flat dictionary for easy access in template
    settings_dict = {setting.key: setting for setting in settings}

    # Check if this is an AJAX request (from loadContent)


    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':


        return render_template('admin/system_settings.html', settings_by_category=settings_by_category, settings_dict=settings_dict)


    else:


        # Direct access - redirect to dashboard


        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/update_system_setting', methods=['POST'])
def update_system_setting():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return jsonify({'success': False, 'message': 'Not authorized'})

    key = request.form.get('key')
    value = request.form.get('value')

    setting = SystemSetting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
        setting.updated_by = user.id
        db.session.commit()
        return jsonify({'success': True, 'message': 'Setting updated successfully'})
    return jsonify({'success': False, 'message': 'Setting not found'})

@admin_bp.route('/set_current_term_year', methods=['GET', 'POST'])
def set_current_term_year():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Admin':
        return redirect(url_for('authbp.login'))

    if request.method == 'POST':
        current_academic_year_id = request.form.get('current_academic_year_id')
        current_term_id = request.form.get('current_term_id')

        try:
            # Update or create current academic year setting
            academic_year_setting = SystemSetting.query.filter_by(key='current_academic_year_id').first()
            if academic_year_setting:
                academic_year_setting.value = current_academic_year_id
                academic_year_setting.updated_by = user.id
            else:
                academic_year_setting = SystemSetting(
                    key='current_academic_year_id',
                    value=current_academic_year_id,
                    category='academic',
                    description='Current academic year ID',
                    data_type='integer',
                    updated_by=user.id
                )
                db.session.add(academic_year_setting)

            # Update or create current term setting
            term_setting = SystemSetting.query.filter_by(key='current_term_id').first()
            if term_setting:
                term_setting.value = current_term_id
                term_setting.updated_by = user.id
            else:
                term_setting = SystemSetting(
                    key='current_term_id',
                    value=current_term_id,
                    category='academic',
                    description='Current term ID',
                    data_type='integer',
                    updated_by=user.id
                )
                db.session.add(term_setting)

            db.session.commit()
            flash('Current academic year and term updated successfully!', 'success')
            return redirect(url_for('admin.set_current_term_year'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

    # GET request - show form
    academic_years = AcademicYear.query.order_by(AcademicYear.start_date.desc()).all()
    terms = Term.query.join(AcademicYear).order_by(AcademicYear.start_date.desc(), Term.start_date).all()

    # Get current settings
    current_academic_year_setting = SystemSetting.query.filter_by(key='current_academic_year_id').first()
    current_term_setting = SystemSetting.query.filter_by(key='current_term_id').first()

    current_academic_year_id = current_academic_year_setting.value if current_academic_year_setting else None
    current_term_id = current_term_setting.value if current_term_setting else None

    # Check if this is an AJAX request (from loadContent)


    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':


        return render_template('admin/set_current_term_year.html',
                         academic_years=academic_years,
                         terms=terms,
                         current_academic_year_id=current_academic_year_id,
                         current_term_id=current_term_id)


    else:


        # Direct access - redirect to dashboard


        return redirect(url_for('admin.dashboard'))