from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.auth_models import SystemUser, db
from models.secretary_models import Pupil
from models.admin_models import SchoolClass, Stream, Notification, NotificationRead
from datetime import datetime
from werkzeug.security import generate_password_hash

secretary_bp = Blueprint('secretary', __name__, url_prefix='/secretary')

@secretary_bp.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Secretary':
        return redirect(url_for('authbp.login'))

    # Get notifications for secretary (notifications that are visible to all or teachers)
    notifications = Notification.query.filter(
        Notification.visibility.in_(['all', 'all_except_parents_admins', 'teachers_only'])
    ).order_by(Notification.created_at.desc()).limit(5).all()

    # Get unread notification count
    from models.admin_models import NotificationRead
    from sqlalchemy import select
    read_notification_ids = select(NotificationRead.notification_id).where(NotificationRead.user_id == user.id).subquery()
    unread_count = Notification.query.filter(
        Notification.visibility.in_(['all', 'all_except_parents_admins', 'teachers_only']),
        ~Notification.id.in_(read_notification_ids)
    ).count()

    # Import the utility function
    from app import get_term_progress_info
    term_progress = get_term_progress_info()

    # Get settings for welcome modal
    from models.admin_models import SystemSetting
    school_name_setting = SystemSetting.query.filter_by(key='school_name').first()
    contact_phone_setting = SystemSetting.query.filter_by(key='contact_phone').first()
    contact_email_setting = SystemSetting.query.filter_by(key='contact_email').first()
    school_name = school_name_setting.value if school_name_setting and school_name_setting.value else 'Bright Future P.S'
    contact_phone = contact_phone_setting.value if contact_phone_setting and contact_phone_setting.value else '+256786210221'
    contact_email = contact_email_setting.value if contact_email_setting and contact_email_setting.value else 'mutaniktechnologies@gmail.com'

    return render_template('secretary/dashboard.html', notifications=notifications, term_progress=term_progress, unread_count=unread_count, school_name=school_name, contact_phone=contact_phone, contact_email=contact_email)

@secretary_bp.route('/register-pupil', methods=['GET', 'POST'])
def register_pupil():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Secretary':
        return redirect(url_for('authbp.login'))

    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            date_of_birth_str = request.form.get('date_of_birth')
            gender = request.form.get('gender')
            address = request.form.get('address')
            nationality = request.form.get('nationality')
            phone_number = request.form.get('phone_number')
            email = request.form.get('email')
            parent_name = request.form.get('parent_name')
            parent_phone = request.form.get('parent_phone')
            parent_email = request.form.get('parent_email')
            emergency_contact_name = request.form.get('emergency_contact_name')
            emergency_contact_phone = request.form.get('emergency_contact_phone')
            current_class_id = request.form.get('current_class_id')
            current_stream_id = request.form.get('current_stream_id')

            # Validate required fields
            if not all([first_name, last_name, date_of_birth_str, gender]):
                flash('Please fill in all required fields.', 'danger')
                classes = SchoolClass.query.all()
                streams = Stream.query.all()
                # Check if this is an AJAX request (from loadContent)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                    return render_template('secretary/register_pupil.html', classes=classes, streams=streams)

                else:

                    # Direct access - redirect to dashboard

                    return redirect(url_for('secretary.dashboard'))

            # Generate admission number
            current_year = datetime.now().year
            # Find the last admission number for this year
            last_pupil = Pupil.query.filter(
                Pupil.admission_number.like(f'AD/{current_year}/%')
            ).order_by(Pupil.id.desc()).first()

            if last_pupil:
                # Extract the number from the last admission number
                last_number = int(last_pupil.admission_number.split('/')[-1])
                new_number = last_number + 1
            else:
                new_number = 1

            admission_number = f'AD/{current_year}/{new_number:03d}'

            # Check if admission number already exists (extra safety check)
            existing_pupil = Pupil.query.filter_by(admission_number=admission_number).first()
            if existing_pupil:
                flash('Admission number generation conflict. Please try again.', 'danger')
                classes = SchoolClass.query.all()
                streams = Stream.query.all()
                # Check if this is an AJAX request (from loadContent)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                    return render_template('secretary/register_pupil.html', classes=classes, streams=streams)

                else:

                    # Direct access - redirect to dashboard

                    return redirect(url_for('secretary.dashboard'))

            # Parse date of birth
            try:
                date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'danger')
                classes = SchoolClass.query.all()
                streams = Stream.query.all()
                # Check if this is an AJAX request (from loadContent)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                    return render_template('secretary/register_pupil.html', classes=classes, streams=streams)

                else:

                    # Direct access - redirect to dashboard

                    return redirect(url_for('secretary.dashboard'))

            # Create new pupil
            new_pupil = Pupil(
                admission_number=admission_number,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                address=address,
                nationality=nationality,
                phone_number=phone_number,
                email=email,
                parent_name=parent_name,
                parent_phone=parent_phone,
                parent_email=parent_email,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_phone=emergency_contact_phone,
                current_class_id=current_class_id if current_class_id else None,
                current_stream_id=current_stream_id if current_stream_id else None
            )

            db.session.add(new_pupil)
            db.session.commit()

            flash(f'Pupil {first_name} {last_name} registered successfully with Admission Number: {admission_number}!', 'success')
            # Stay on the same page instead of redirecting
            classes = SchoolClass.query.all()
            streams = Stream.query.all()
            # Check if this is an AJAX request (from loadContent)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                return render_template('secretary/register_pupil.html', classes=classes, streams=streams)

            else:

                # Direct access - redirect to dashboard

                return redirect(url_for('secretary.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            classes = SchoolClass.query.all()
            streams = Stream.query.all()
            # Check if this is an AJAX request (from loadContent)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                return render_template('secretary/register_pupil.html', classes=classes, streams=streams)

            else:

                # Direct access - redirect to dashboard

                return redirect(url_for('secretary.dashboard'))

    # GET request - show registration form
    classes = SchoolClass.query.all()
    streams = Stream.query.all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('secretary/register_pupil.html', classes=classes, streams=streams)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('secretary.dashboard'))

@secretary_bp.route('/manage-pupils')
def manage_pupils():
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Secretary':
        return redirect(url_for('authbp.login'))

    # Get all pupils with their class and stream information
    pupils = Pupil.query.options(
        db.joinedload(Pupil.current_class),
        db.joinedload(Pupil.current_stream)
    ).all()

    classes = SchoolClass.query.all()
    streams = Stream.query.all()

    # Check if this is an AJAX request (from loadContent)


    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':


        return render_template('secretary/manage_pupils.html', pupils=pupils, classes=classes, streams=streams)


    else:


        # Direct access - redirect to dashboard


        return redirect(url_for('secretary.dashboard'))

@secretary_bp.route('/edit-pupil/<int:pupil_id>', methods=['GET', 'POST'])
def edit_pupil(pupil_id):
    if 'user_id' not in session:
        return redirect(url_for('authbp.login'))
    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Secretary':
        return redirect(url_for('authbp.login'))

    pupil = Pupil.query.get_or_404(pupil_id)

    if request.method == 'POST':
        try:
            # Update fields (excluding admission_number)
            pupil.first_name = request.form.get('first_name', pupil.first_name)
            pupil.last_name = request.form.get('last_name', pupil.last_name)

            date_of_birth_str = request.form.get('date_of_birth')
            if date_of_birth_str:
                try:
                    pupil.date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format', 'danger')
                    classes = SchoolClass.query.all()
                    streams = Stream.query.all()
                    # Check if this is an AJAX request (from loadContent)

                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                        return render_template('secretary/edit_pupil.html', pupil=pupil, classes=classes, streams=streams)

                    else:

                        # Direct access - redirect to dashboard

                        return redirect(url_for('secretary.dashboard'))

            pupil.gender = request.form.get('gender', pupil.gender)
            pupil.address = request.form.get('address', pupil.address)
            pupil.nationality = request.form.get('nationality', pupil.nationality)
            pupil.phone_number = request.form.get('phone_number', pupil.phone_number)
            pupil.email = request.form.get('email', pupil.email)
            pupil.parent_name = request.form.get('parent_name', pupil.parent_name)
            pupil.parent_phone = request.form.get('parent_phone', pupil.parent_phone)
            pupil.parent_email = request.form.get('parent_email', pupil.parent_email)
            pupil.emergency_contact_name = request.form.get('emergency_contact_name', pupil.emergency_contact_name)
            pupil.emergency_contact_phone = request.form.get('emergency_contact_phone', pupil.emergency_contact_phone)

            current_class_id = request.form.get('current_class_id')
            pupil.current_class_id = int(current_class_id) if current_class_id else None

            current_stream_id = request.form.get('current_stream_id')
            pupil.current_stream_id = int(current_stream_id) if current_stream_id else None

            pupil.status = request.form.get('status', pupil.status)

            db.session.commit()

            flash(f'Pupil {pupil.first_name} {pupil.last_name} updated successfully!', 'success')
            return redirect(url_for('secretary.manage_pupils'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            classes = SchoolClass.query.all()
            streams = Stream.query.all()
            # Check if this is an AJAX request (from loadContent)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

                return render_template('secretary/edit_pupil.html', pupil=pupil, classes=classes, streams=streams)

            else:

                # Direct access - redirect to dashboard

                return redirect(url_for('secretary.dashboard'))

    # GET request - show edit form
    classes = SchoolClass.query.all()
    streams = Stream.query.all()
    # Check if this is an AJAX request (from loadContent)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        return render_template('secretary/edit_pupil.html', pupil=pupil, classes=classes, streams=streams)

    else:

        # Direct access - redirect to dashboard

        return redirect(url_for('secretary.dashboard'))

@secretary_bp.route('/delete-pupil', methods=['POST'])
def delete_pupil():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    user = SystemUser.query.get(session['user_id'])
    if not user or user.role.name != 'Secretary':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    try:
        data = request.get_json()
        pupil_id = data.get('pupil_id')

        if not pupil_id:
            return jsonify({'success': False, 'message': 'Pupil ID is required'}), 400

        pupil = Pupil.query.get(pupil_id)
        if not pupil:
            return jsonify({'success': False, 'message': 'Pupil not found'}), 404

        pupil_name = f"{pupil.first_name} {pupil.last_name}"

        db.session.delete(pupil)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Pupil {pupil_name} deleted successfully!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500