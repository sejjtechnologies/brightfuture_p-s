import os
from flask import Flask, render_template, session, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import timedelta, datetime, timezone
from sqlalchemy import select

from models.auth_models import SystemUser

load_dotenv()

def get_term_progress_info():
    """Get current term progress information for display in dashboards"""
    from models.admin_models import SystemSetting, Term, AcademicYear

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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 300}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Custom Jinja2 filter for East African time formatting
@app.template_filter('eat_time')
def format_eat_time(dt):
    """Format datetime to East African Time (UTC+3) with AM/PM"""
    if dt is None:
        return ""
    # Convert UTC to East African Time (UTC+3)
    eat_time = dt + timedelta(hours=3)
    return eat_time.strftime('%Y-%m-%d %I:%M %p')

db = SQLAlchemy()
from flask_migrate import Migrate

from models.auth_models import db, Role, SystemUser
from models.admin_models import SchoolClass, Subject, Stream, ClassStream, TeacherAssignment, Notification
from models.secretary_models import Pupil

db.init_app(app)
migrate = Migrate(app, db)

# with app.app_context():
#     db.create_all()

# Auth routes
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = SystemUser.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role.name
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            if user.role.name == 'Admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role.name == 'Teacher':
                return redirect(url_for('teacher'))
            elif user.role.name == 'Secretary':
                return redirect(url_for('secretary'))
            elif user.role.name == 'Parent':
                return redirect(url_for('parent'))
            elif user.role.name == 'Headteacher':
                return redirect(url_for('headteacher'))
            elif user.role.name == 'Bursar':
                return redirect(url_for('bursar'))
            else:
                flash('Role not recognized')
                return redirect(url_for('login'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/auth/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.secretary_routes import secretary_bp
from routes.parent_routes import parent_bp
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(secretary_bp)
app.register_blueprint(parent_bp)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/teacher')
def teacher():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(SystemUser, session['user_id'])
    if not user or user.role.name != 'Teacher':
        return redirect(url_for('login'))
    
    # Check maintenance mode
    from models.admin_models import SystemSetting
    maintenance_setting = SystemSetting.query.filter_by(key='enable_maintenance_mode').first()
    if maintenance_setting and maintenance_setting.value == 'true':
        return render_template('maintenance.html')
    
    from models.admin_models import Notification, NotificationRead
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

    term_progress = get_term_progress_info()

    return render_template('teacher/dashboard.html', notifications=notifications, term_progress=term_progress, unread_count=unread_count)

@app.route('/secretary')
def secretary():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    from models.auth_models import SystemUser
    user = db.session.get(SystemUser, session['user_id'])
    if not user or user.role.name != 'Secretary':
        return redirect(url_for('login'))
    
    # Check maintenance mode
    from models.admin_models import SystemSetting
    maintenance_setting = SystemSetting.query.filter_by(key='enable_maintenance_mode').first()
    if maintenance_setting and maintenance_setting.value == 'true':
        return render_template('maintenance.html')
    
    from models.admin_models import Notification, NotificationRead
    from models.auth_models import SystemUser
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

    return render_template('secretary/dashboard.html', notifications=notifications, unread_count=unread_count)

@app.route('/bursar')
def bursar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(SystemUser, session['user_id'])
    if not user or user.role.name != 'Bursar':
        return redirect(url_for('login'))
    
    # Check maintenance mode
    from models.admin_models import SystemSetting, NotificationRead
    maintenance_setting = SystemSetting.query.filter_by(key='enable_maintenance_mode').first()
    if maintenance_setting and maintenance_setting.value == 'true':
        return render_template('maintenance.html')
    
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

    term_progress = get_term_progress_info()

    return render_template('bursar/dashboard.html', notifications=notifications, term_progress=term_progress, unread_count=unread_count)

@app.route('/headteacher')
def headteacher():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(SystemUser, session['user_id'])
    if not user or user.role.name != 'Headteacher':
        return redirect(url_for('login'))
    
    # Check maintenance mode
    from models.admin_models import SystemSetting
    maintenance_setting = SystemSetting.query.filter_by(key='enable_maintenance_mode').first()
    if maintenance_setting and maintenance_setting.value == 'true':
        return render_template('maintenance.html')
    
    from models.admin_models import Notification, NotificationRead
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

    term_progress = get_term_progress_info()

    return render_template('headteacher/dashboard.html', notifications=notifications, term_progress=term_progress, unread_count=unread_count)

@app.route('/parent')
def parent():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = db.session.get(SystemUser, session['user_id'])
    if not user or user.role.name != 'Parent':
        return redirect(url_for('login'))

    # Check maintenance mode
    from models.admin_models import SystemSetting
    maintenance_setting = SystemSetting.query.filter_by(key='enable_maintenance_mode').first()
    if maintenance_setting and maintenance_setting.value == 'true':
        return render_template('maintenance.html')

    # Get notifications for parent (parents should not see any announcements)
    from models.admin_models import Notification, NotificationRead
    notifications = []  # Parents should not see any notifications

    # Get unread notification count (always 0 for parents)
    unread_count = 0

    term_progress = get_term_progress_info()

    return render_template('parent/dashboard.html', notifications=notifications, term_progress=term_progress, unread_count=unread_count)

@app.route('/mark_notifications_read', methods=['POST'])
def mark_notifications_read():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'})

    user = db.session.get(SystemUser, session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})

    try:
        from models.admin_models import Notification, NotificationRead

        # Get all notification IDs that are visible to this user
        visible_notifications = Notification.query.filter(
            (Notification.visibility == 'all') |
            (Notification.visibility == 'all_except_parents_admins') |
            (Notification.visibility == user.role.name.lower() + '_only')
        ).all()

        # Mark all visible notifications as read for this user
        for notification in visible_notifications:
            # Check if already marked as read
            existing_read = NotificationRead.query.filter_by(
                notification_id=notification.id,
                user_id=user.id
            ).first()

            if not existing_read:
                read_record = NotificationRead(
                    notification_id=notification.id,
                    user_id=user.id
                )
                db.session.add(read_record)

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/developer')
def developer():
    return render_template('developer.html')

if __name__ == '__main__':
    app.run(debug=True)