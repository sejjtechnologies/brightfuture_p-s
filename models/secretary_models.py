from models.auth_models import db
from datetime import datetime

class Pupil(db.Model):
    __tablename__ = 'pupils'

    id = db.Column(db.Integer, primary_key=True)
    admission_number = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # Male, Female
    address = db.Column(db.Text, nullable=True)
    nationality = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    parent_name = db.Column(db.String(200), nullable=True)
    parent_phone = db.Column(db.String(20), nullable=True)
    parent_email = db.Column(db.String(120), nullable=True)
    emergency_contact_name = db.Column(db.String(200), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)

    # Academic information
    current_class_id = db.Column(db.Integer, db.ForeignKey('school_class.id'), nullable=True)
    current_stream_id = db.Column(db.Integer, db.ForeignKey('stream.id'), nullable=True)
    enrollment_date = db.Column(db.Date, default=datetime.utcnow().date)
    status = db.Column(db.String(20), default='Active')  # Active, Inactive, Graduated, Transferred

    # Relationships
    current_class = db.relationship('SchoolClass', backref='pupils')
    current_stream = db.relationship('Stream', backref='pupils')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Pupil {self.first_name} {self.last_name} - {self.admission_number}>'

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if self.date_of_birth:
            today = datetime.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None