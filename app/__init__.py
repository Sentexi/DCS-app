# app/__init__.py

from flask import Flask, request
from .extensions import db, login_manager, migrate
from flask_login import current_user
from datetime import datetime
from flask_socketio import SocketIO

socketio = SocketIO()  # Create the SocketIO object globally

def create_app(config_file=None):
    app = Flask(__name__)
    
    socketio.init_app(app)
    
    # Enable a 'startswith' test in our Jinja templates
    app.jinja_env.tests['startswith'] = lambda val, prefix: (
        isinstance(val, str) and val.startswith(prefix)
    )

    # Basic config (you can improve this later)
    app.config['SECRET_KEY'] = 'dev'  # change in prod!
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///debate_app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints (to be implemented in the next steps)
    from .auth import auth_bp
    from .main import main_bp
    from .admin import admin_bp
    from .debate import debate_bp
    from .profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(debate_bp)
    app.register_blueprint(profile_bp)
    
    print(app.url_map)
    
    @app.before_request
    def update_last_seen():
        # Only for authenticated users, and not for static/assets
        if current_user.is_authenticated and not request.path.startswith('/static'):
            current_user.last_seen = datetime.utcnow()
            db.session.commit()

    return app
