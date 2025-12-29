import os
from dotenv import load_dotenv
from app import app, db
from models.auth_models import SystemUser, Role

# Load environment variables
load_dotenv()

def create_teachers():
    """Create teacher users with mixed male and female names following insert_users.py logic"""

    # Authentic Ugandan names - mix of male and female
    male_names = [
        "David", "Daniel", "James", "John", "Joseph", "Michael", "Moses", "Paul", "Peter", "Samuel",
        "Andrew", "Anthony", "Benjamin", "Charles", "Christopher", "Emmanuel", "Francis", "Gabriel", "Isaac", "Jacob",
        "Joshua", "Julius", "Lawrence", "Martin", "Matthew", "Nicholas", "Patrick", "Philip", "Richard", "Simon",
        "Stephen", "Thomas", "Timothy", "Vincent", "William", "Wilson"
    ]

    female_names = [
        "Agnes", "Alice", "Ann", "Beatrice", "Catherine", "Christine", "Dorcas", "Elizabeth", "Esther", "Florence",
        "Grace", "Helen", "Irene", "Janet", "Jennifer", "Joan", "Josephine", "Joyce", "Judith", "Juliet",
        "Lydia", "Margaret", "Maria", "Mary", "Mercy", "Monica", "Naomi", "Norah", "Patience", "Priscilla",
        "Rachel", "Rebecca", "Rose", "Ruth", "Sarah", "Susan", "Tabitha", "Veronica", "Victoria", "Winfred"
    ]

    surnames = [
        "Ssali", "Muwanguzi", "Nakato", "Namugga", "Nankya", "Nalwoga", "Kyambadde", "Ssekitoleko", "Okello", "Ochieng",
        "Adong", "Akello", "Auma", "Nabukeera", "Nakato", "Nabukalu", "Nabatanzi", "Nabwire", "Nakato", "Namubiru",
        "Ssempijja", "Ssebulime", "Mugisha", "Tumushabe", "Rwabwogo", "Mwesigwa", "Muganzi", "Mugabe", "Mugisha", "Muganzi",
        "Kato", "Lubega", "Ssekandi", "Mukiibi", "Nagawa", "Muwanga", "Ssewagaba", "Mugalu", "Ssengendo", "Muwanguzi"
    ]

    with app.app_context():
        # Get the teacher role
        teacher_role = Role.query.filter_by(name='Teacher').first()
        if not teacher_role:
            print("Teacher role not found!")
            return

        teachers_created = 0

        # Create 28 teachers (mixing male and female names)
        for i in range(28):
            if i % 2 == 0:  # Even index - male name
                first_name = male_names[i // 2 % len(male_names)]
            else:  # Odd index - female name
                first_name = female_names[i // 2 % len(female_names)]

            surname = surnames[i % len(surnames)]

            # Create username (first letter of first name + surname) - ensure uniqueness
            base_username = f"{first_name[0].lower()}{surname.lower()}"
            username = base_username
            counter = 1

            # Check for unique username
            while SystemUser.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1

            # Create email
            email = f"{username}@brightfutureps.go.ug"

            # Check if user already exists (double check)
            if not SystemUser.query.filter_by(username=username).first():
                # Get the next display_id (following insert_users.py logic)
                max_display_id = db.session.query(db.func.max(SystemUser.display_id)).scalar() or 0
                user = SystemUser(display_id=max_display_id + 1, username=username, email=email, role_id=teacher_role.id)
                user.set_password('password')  # Following insert_users.py logic
                db.session.add(user)
                teachers_created += 1

                print(f"Created teacher: {first_name} {surname} ({username}) - Display ID: {max_display_id + 1}")

        db.session.commit()
        print(f"\n✅ Successfully created {teachers_created} teachers!")
        print("Default password for all teachers: password")
        print("Please advise teachers to change their passwords upon first login.")

if __name__ == "__main__":
    create_teachers()