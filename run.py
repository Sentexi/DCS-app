from app import create_app
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

def create_initial_admin():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            # Change credentials as needed!
            username = 'admin'
            email = 'admin@example.com'
            password = 'admin123'
            if not User.query.filter_by(email=email).first():
                admin = User(
                    username=username,
                    email=email,
                    password=generate_password_hash(password),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print(f'Admin user created: {email} / {password}')
            else:
                print('Admin email already exists, skipping admin creation.')
        else:
            print('Admin user already exists.')
            

if __name__ == '__main__':
    create_initial_admin()
    app.run(debug=True)
