from app import app, db, Role, SystemUser

with app.app_context():
    roles = Role.query.all()
    for role in roles:
        username = role.name.lower()
        email = f"{username}@example.com"
        if not SystemUser.query.filter_by(username=username).first():
            user = SystemUser(username=username, email=email, role_id=role.id)
            user.set_password('password')
            db.session.add(user)
    db.session.commit()
    print("Users inserted successfully")