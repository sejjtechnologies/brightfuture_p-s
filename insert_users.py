from app import app, db, Role, SystemUser

with app.app_context():
    roles = Role.query.all()
    for role in roles:
        username = role.name.lower()
        email = f"{username}@example.com"
        if not SystemUser.query.filter_by(username=username).first():
            # Get the next display_id
            max_display_id = db.session.query(db.func.max(SystemUser.display_id)).scalar() or 0
            user = SystemUser(display_id=max_display_id + 1, username=username, email=email, role_id=role.id)
            user.set_password('password')
            db.session.add(user)
    db.session.commit()
    print("Users inserted successfully")