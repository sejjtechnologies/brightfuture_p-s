from models.auth_models import db
from datetime import datetime

class AssessmentRecord(db.Model):
    """Model for continuous assessment records (tests, quizzes, homework)"""
    __tablename__ = 'assessment_records'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey('stream.id'), nullable=True)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)

    assessment_type = db.Column(db.String(50), nullable=False)  # 'test', 'quiz', 'homework', 'assignment'
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_marks = db.Column(db.Float, nullable=False)
    assessment_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=True)  # For homework/assignments

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = db.relationship('SystemUser', backref='assessment_records')
    subject = db.relationship('Subject', backref='assessment_records')
    school_class = db.relationship('SchoolClass', backref='assessment_records')
    stream = db.relationship('Stream', backref='assessment_records')
    term = db.relationship('Term', backref='assessment_records')

class AssessmentResult(db.Model):
    """Model for pupil assessment results/marks"""
    __tablename__ = 'assessment_results'

    id = db.Column(db.Integer, primary_key=True)
    assessment_record_id = db.Column(db.Integer, db.ForeignKey('assessment_records.id'), nullable=False)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5), nullable=True)  # A, B+, B, etc.
    remarks = db.Column(db.Text, nullable=True)
    stream_rank = db.Column(db.Integer, nullable=True)  # Position in stream
    class_rank = db.Column(db.Integer, nullable=True)  # Position in class
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assessment_record = db.relationship('AssessmentRecord', backref='results')
    pupil = db.relationship('Pupil', backref='assessment_results')

    __table_args__ = (db.UniqueConstraint('assessment_record_id', 'pupil_id'),)

class SubjectRemark(db.Model):
    """Model for subject-wise remarks for pupils"""
    __tablename__ = 'subject_remarks'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)

    remark = db.Column(db.Text, nullable=False)
    remark_type = db.Column(db.String(50), nullable=False)  # 'academic', 'behavior', 'effort', 'general'
    is_positive = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = db.relationship('SystemUser', backref='subject_remarks')
    pupil = db.relationship('Pupil', backref='subject_remarks')
    subject = db.relationship('Subject', backref='subject_remarks')
    term = db.relationship('Term', backref='subject_remarks')

class ProgressSummary(db.Model):
    """Model for pupil progress summaries"""
    __tablename__ = 'progress_summaries'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)

    overall_performance = db.Column(db.String(20), nullable=False)  # 'excellent', 'good', 'satisfactory', 'needs_improvement'
    strengths = db.Column(db.Text, nullable=True)
    areas_for_improvement = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = db.relationship('SystemUser', backref='progress_summaries')
    pupil = db.relationship('Pupil', backref='progress_summaries')
    subject = db.relationship('Subject', backref='progress_summaries')
    term = db.relationship('Term', backref='progress_summaries')

class Curriculum(db.Model):
    """Model for curriculum/syllabus content"""
    __tablename__ = 'curriculums'

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)

    topic = db.Column(db.String(200), nullable=False)
    sub_topic = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    learning_objectives = db.Column(db.Text, nullable=True)
    resources_needed = db.Column(db.Text, nullable=True)
    estimated_duration = db.Column(db.Integer, nullable=True)  # in hours/days

    created_by = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subject = db.relationship('Subject', backref='curriculums')
    school_class = db.relationship('SchoolClass', backref='curriculums')
    term = db.relationship('Term', backref='curriculums')
    creator = db.relationship('SystemUser', backref='curriculums')

class LessonPlan(db.Model):
    """Model for lesson plans"""
    __tablename__ = 'lesson_plans'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey('stream.id'), nullable=True)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)

    lesson_date = db.Column(db.Date, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    topic = db.Column(db.String(200), nullable=False)
    sub_topic = db.Column(db.String(200), nullable=True)
    objectives = db.Column(db.Text, nullable=True)
    materials_needed = db.Column(db.Text, nullable=True)
    methodology = db.Column(db.Text, nullable=True)
    assessment_method = db.Column(db.Text, nullable=True)
    homework = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default='planned')  # 'planned', 'completed', 'cancelled'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = db.relationship('SystemUser', backref='lesson_plans')
    subject = db.relationship('Subject', backref='lesson_plans')
    school_class = db.relationship('SchoolClass', backref='lesson_plans')
    stream = db.relationship('Stream', backref='lesson_plans')
    term = db.relationship('Term', backref='lesson_plans')

class Homework(db.Model):
    """Model for homework assignments"""
    __tablename__ = 'homeworks'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey('stream.id'), nullable=True)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    assigned_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    estimated_duration = db.Column(db.Integer, nullable=True)  # in minutes

    status = db.Column(db.String(20), default='active')  # 'active', 'completed', 'overdue'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = db.relationship('SystemUser', backref='homeworks')
    subject = db.relationship('Subject', backref='homeworks')
    school_class = db.relationship('SchoolClass', backref='homeworks')
    stream = db.relationship('Stream', backref='homeworks')
    term = db.relationship('Term', backref='homeworks')

class HomeworkSubmission(db.Model):
    """Model for homework submissions by pupils"""
    __tablename__ = 'homework_submissions'

    id = db.Column(db.Integer, primary_key=True)
    homework_id = db.Column(db.Integer, db.ForeignKey('homeworks.id'), nullable=False)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='submitted')  # 'submitted', 'graded', 'late'
    grade = db.Column(db.String(5), nullable=True)
    teacher_feedback = db.Column(db.Text, nullable=True)

    # Relationships
    homework = db.relationship('Homework', backref='submissions')
    pupil = db.relationship('Pupil', backref='homework_submissions')

    __table_args__ = (db.UniqueConstraint('homework_id', 'pupil_id'),)

class LearningNeed(db.Model):
    """Model for pupil learning needs/special requirements"""
    __tablename__ = 'learning_needs'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    identified_by = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    need_type = db.Column(db.String(100), nullable=False)  # 'dyslexia', 'ADHD', 'gifted', 'ESL', etc.
    description = db.Column(db.Text, nullable=False)
    support_required = db.Column(db.Text, nullable=True)
    accommodations = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default='active')  # 'active', 'resolved', 'monitored'

    identified_date = db.Column(db.Date, default=datetime.utcnow().date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pupil = db.relationship('Pupil', backref='learning_needs')
    identifier = db.relationship('SystemUser', backref='identified_learning_needs')

class DisciplinaryNote(db.Model):
    """Model for disciplinary notes related to pupils"""
    __tablename__ = 'disciplinary_notes'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    incident_date = db.Column(db.Date, nullable=False)
    incident_type = db.Column(db.String(100), nullable=False)  # 'behavior', 'academic', 'attendance', etc.
    description = db.Column(db.Text, nullable=False)
    action_taken = db.Column(db.Text, nullable=True)
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_notes = db.Column(db.Text, nullable=True)

    severity = db.Column(db.String(20), default='minor')  # 'minor', 'moderate', 'major', 'critical'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pupil = db.relationship('Pupil', backref='disciplinary_notes')
    reporter = db.relationship('SystemUser', backref='disciplinary_notes')

class TeacherNote(db.Model):
    """Model for private teacher notes about pupils"""
    __tablename__ = 'teacher_notes'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('system_users.id'), nullable=False)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    note_type = db.Column(db.String(50), nullable=False)  # 'academic', 'behavioral', 'personal', 'general'
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_confidential = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = db.relationship('SystemUser', backref='teacher_notes')
    pupil = db.relationship('Pupil', backref='teacher_notes')