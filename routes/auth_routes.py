from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models.auth_models import SystemUser
from datetime import datetime

auth_bp = Blueprint('authbp', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Check if maintenance mode is enabled
    from models.admin_models import SystemSetting
    maintenance_setting = SystemSetting.query.filter_by(key='enable_maintenance_mode').first()
    if maintenance_setting and maintenance_setting.value == 'true':
        return render_template('maintenance.html')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = SystemUser.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role.name
            user.last_login = datetime.utcnow()
            from app import db
            db.session.commit()
            if user.role.name == 'Admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role.name == 'Teacher':
                return redirect(url_for('teacher'))
            elif user.role.name == 'Secretary':
                return redirect(url_for('secretary'))
            elif user.role.name == 'Parent':
                return redirect(url_for('parent'))  # Assuming you add this route
            elif user.role.name == 'Headteacher':
                return redirect(url_for('headteacher'))
            elif user.role.name == 'Bursar':
                return redirect(url_for('bursar'))
            else:
                flash('Role not recognized')
                return redirect(url_for('authbp.login'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('authbp.login'))
    return render_template('index.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('authbp.login'))