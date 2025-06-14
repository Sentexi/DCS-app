from app import create_app, socketio
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

def create_initial_admin():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(is_admin=True).first():
            # Change credentials as needed!
            first_name = 'Admin'
            last_name = 'User'
            email = 'admin@example.com'
            password = 'admin123'
            if not User.query.filter_by(email=email).first():
                admin = User(
                    first_name=first_name,
                    last_name=last_name,
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

    socketio.run(app, host='0.0.0.0', port=app.config.get('PORT', 5000))
