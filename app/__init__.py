# app/__init__.py

from flask import Flask
from .extensions import db, login_manager, migrate

def create_app(config_file=None):
    app = Flask(__name__)

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(debate_bp)

    return app
