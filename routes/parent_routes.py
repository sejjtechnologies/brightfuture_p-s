from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.auth_models import SystemUser, db
from models.secretary_models import Pupil
from models.admin_models import SchoolClass, Stream, Notification, NotificationRead
from datetime import datetime
from sqlalchemy import or_, and_

parent_bp = Blueprint('parent', __name__, url_prefix='/parent')

@parent_bp.route('/')
def dashboard():
    """Parent dashboard with search functionality and term progress"""
    print(f"Dashboard - Session contents: {session}")  # Debug
    print(f"Dashboard - User ID: {session.get('user_id')}, Role: {session.get('role')}")  # Debug

    if 'user_id' not in session:
        print("Dashboard - No user_id in session")  # Debug
        flash('Please log in as a parent to access this page.', 'error')
        return redirect(url_for('auth.login'))

    # For now, allow any logged-in user (remove role check)
    # if session.get('role') != 'parent':
    #     print("Dashboard - Role is not parent")  # Debug
    #     flash('Please log in as a parent to access this page.', 'error')
    #     return redirect(url_for('auth.login'))

    # Get term progress information
    term_progress = get_term_progress_info()

    return render_template('parent/dashboard.html', term_progress=term_progress)

@parent_bp.route('/search_pupils', methods=['POST'])
def search_pupils():
    """API endpoint for searching pupils"""
    print(f"Session contents: {session}")  # Debug
    print(f"User ID: {session.get('user_id')}, Role: {session.get('role')}")  # Debug

    if 'user_id' not in session:
        print("No user_id in session")  # Debug
        return jsonify({'error': 'Unauthorized'}), 403

    # For now, allow any logged-in user to search (remove role check)
    # if session.get('role') != 'parent':
    #     print("Role is not parent")  # Debug
    #     return jsonify({'error': 'Unauthorized'}), 403

    search_term = request.json.get('search_term', '').strip()

    if not search_term:
        return jsonify({'error': 'Search term is required'}), 400

    try:
        # Search pupils by multiple criteria
        pupils = Pupil.query.filter(
            or_(
                Pupil.first_name.ilike(f'%{search_term}%'),
                Pupil.last_name.ilike(f'%{search_term}%'),
                Pupil.admission_number.ilike(f'%{search_term}%'),
                Pupil.address.ilike(f'%{search_term}%'),
                Pupil.nationality.ilike(f'%{search_term}%')
            )
        ).filter(Pupil.status == 'Active').all()

        # Format results
        results = []
        for pupil in pupils:
            results.append({
                'id': pupil.id,
                'admission_number': pupil.admission_number,
                'first_name': pupil.first_name,
                'last_name': pupil.last_name,
                'full_name': pupil.get_full_name(),
                'current_class': pupil.current_class.name if pupil.current_class else 'Not Assigned',
                'current_stream': pupil.current_stream.name if pupil.current_stream else 'Not Assigned',
                'address': pupil.address or 'Not provided',
                'nationality': pupil.nationality or 'Not provided',
                'parent_name': pupil.parent_name or 'Not provided',
                'parent_phone': pupil.parent_phone or 'Not provided'
            })

        return jsonify({
            'success': True,
            'count': len(results),
            'pupils': results
        })

    except Exception as e:
        print(f"Error searching pupils: {e}")
        return jsonify({'error': 'Search failed'}), 500

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

        # Calculate total term days
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
            'term_start_date': term_start.isoformat(),
            'term_end_date': term_end.isoformat(),
            'today': today.isoformat()
        }
    except Exception as e:
        print(f"Error getting term progress info: {e}")
        return None
