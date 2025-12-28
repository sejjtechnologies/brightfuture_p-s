from app import app, db, Role

with app.app_context():
    roles = ['Admin', 'Teacher', 'Secretary', 'Parent', 'Headteacher', 'Bursar']
    for role_name in roles:
        if not Role.query.filter_by(name=role_name).first():
            role = Role(name=role_name)
            db.session.add(role)
    db.session.commit()
    print("Roles inserted successfully")