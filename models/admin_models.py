from models.auth_models import db

class SchoolClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

class Stream(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

class ClassStream(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey('stream.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    __table_args__ = (db.UniqueConstraint('class_id', 'stream_id'),)

class TeacherAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    class_stream_id = db.Column(db.Integer, db.ForeignKey('class_stream.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    __table_args__ = (db.UniqueConstraint('teacher_id', 'class_stream_id', 'subject_id'),)

class AcademicYear(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

class Term(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    academic_year_id = db.Column(db.Integer, db.ForeignKey('academic_year.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    academic_year = db.relationship('AcademicYear', backref=db.backref('terms', lazy=True))

class ExamSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    term = db.relationship('Term', backref=db.backref('exam_schedules', lazy=True))
    subject = db.relationship('Subject', backref=db.backref('exam_schedules', lazy=True))
    school_class = db.relationship('SchoolClass', backref=db.backref('exam_schedules', lazy=True))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    visibility = db.Column(db.String(50), default='all_except_parents_admins')  # Options: 'all', 'teachers_only', etc.
    creator = db.relationship('SystemUser', backref=db.backref('notifications', lazy=True))

class NotificationRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('notification.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=db.func.now())
    notification = db.relationship('Notification', backref=db.backref('reads', lazy=True))
    user = db.relationship('SystemUser', backref=db.backref('read_notifications', lazy=True))

class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # e.g., 'school_info', 'security', 'communication'
    description = db.Column(db.String(255), nullable=True)
    data_type = db.Column(db.String(20), default='string')  # 'string', 'boolean', 'integer', 'json'
    is_public = db.Column(db.Boolean, default=False)  # Can non-admin users see this?
    updated_by = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    updater = db.relationship('SystemUser', backref=db.backref('system_settings', lazy=True))
